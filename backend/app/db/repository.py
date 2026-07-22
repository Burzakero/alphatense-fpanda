"""
Thin persistence functions used by app/api/main.py.

Keeps SQLAlchemy usage out of the route handlers -- each function takes an
open `Session` and does one job. `save_workspace`/`load_workspace` are the
only functions that touch the engine's `Workspace` class, serializing its
`statements`/`invoices` (see app/engine/workspace.py) to/from the JSON
column on `WorkspaceRecord`.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import timedelta

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.db.models import AdvisorAccount, Session as SessionRecord, WorkspaceRecord, utcnow
from app.engine.workspace import Workspace
from app.models.domain import FinancialStatement, Invoice

SESSION_TTL = timedelta(days=30)
TRIAL_PERIOD = timedelta(days=15)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_advisor(db: DbSession, *, name: str, email: str, password: str, phone: str) -> AdvisorAccount:
    advisor = AdvisorAccount(
        advisor_id=str(uuid.uuid4()),
        name=name,
        email=email.strip().lower(),
        password_hash=hash_password(password),
        phone=phone.strip(),
        trial_expires_at=utcnow() + TRIAL_PERIOD,
    )
    db.add(advisor)
    db.commit()
    db.refresh(advisor)
    return advisor


def is_trial_expired(advisor: AdvisorAccount) -> bool:
    """Accounts created before the trial system shipped have trial_expires_at=None
    (grandfathered in, never nullable-added rows aren't retroactively locked out)."""
    return advisor.trial_expires_at is not None and advisor.trial_expires_at < utcnow()


def get_advisor_by_email(db: DbSession, email: str) -> AdvisorAccount | None:
    return db.scalar(select(AdvisorAccount).where(AdvisorAccount.email == email.strip().lower()))


def get_advisor_by_id(db: DbSession, advisor_id: str) -> AdvisorAccount | None:
    return db.get(AdvisorAccount, advisor_id)


def create_session(db: DbSession, advisor_id: str) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        SessionRecord(
            token_hash=_hash_token(token),
            advisor_id=advisor_id,
            expires_at=utcnow() + SESSION_TTL,
        )
    )
    db.commit()
    return token


def get_advisor_by_token(db: DbSession, token: str) -> AdvisorAccount | None:
    session_record = db.get(SessionRecord, _hash_token(token))
    if session_record is None:
        return None
    if session_record.expires_at < utcnow():
        return None
    return get_advisor_by_id(db, session_record.advisor_id)


def delete_session(db: DbSession, token: str) -> None:
    session_record = db.get(SessionRecord, _hash_token(token))
    if session_record is not None:
        db.delete(session_record)
        db.commit()


def save_workspace(db: DbSession, workspace_id: str, advisor_id: str, workspace: Workspace) -> None:
    data = {
        "statements": [s.model_dump(mode="json") for s in workspace.statements],
        "invoices": [i.model_dump(mode="json") for i in workspace.invoices],
    }
    record = db.get(WorkspaceRecord, workspace_id)
    if record is None:
        db.add(WorkspaceRecord(workspace_id=workspace_id, advisor_id=advisor_id, data=data))
    else:
        record.data = data
    db.commit()


def get_workspace_owner_id(db: DbSession, workspace_id: str) -> str | None:
    """Cheap ownership lookup that doesn't deserialize the (potentially large) data blob.

    Used to re-verify ownership on every request even when the Workspace
    itself is already cached in memory (app/api/main.py's `_WORKSPACES`) --
    the cache has no notion of who owns what, so this check must not be
    skipped just because the data was already loaded once.
    """
    return db.scalar(select(WorkspaceRecord.advisor_id).where(WorkspaceRecord.workspace_id == workspace_id))


def load_workspace(db: DbSession, workspace_id: str) -> tuple[Workspace, str] | None:
    """Returns (workspace, owning advisor_id), or None if no such workspace exists."""
    record = db.get(WorkspaceRecord, workspace_id)
    if record is None:
        return None
    statements = [FinancialStatement(**s) for s in record.data.get("statements", [])]
    invoices = [Invoice(**i) for i in record.data.get("invoices", [])]
    return Workspace(statements=statements, invoices=invoices), record.advisor_id


def list_advisor_workspace_ids(db: DbSession, advisor_id: str) -> list[str]:
    rows = db.scalars(
        select(WorkspaceRecord)
        .where(WorkspaceRecord.advisor_id == advisor_id)
        .order_by(WorkspaceRecord.created_at.desc())
    )
    return [r.workspace_id for r in rows]
