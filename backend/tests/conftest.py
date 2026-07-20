"""
Points the app at a throwaway SQLite file for the whole test session, before
any test module imports app.api.main (which imports app.db.database, whose
engine is created from DATABASE_PATH at import time -- must be set first).
"""

import os
import tempfile
from pathlib import Path

_tmp_dir = tempfile.mkdtemp(prefix="alphatense-test-db-")
os.environ["DATABASE_PATH"] = str(Path(_tmp_dir) / "test.db")

from app.db.database import init_db  # noqa: E402

init_db()
