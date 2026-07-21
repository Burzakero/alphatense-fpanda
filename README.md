# Alphatense

AI copilot for financial advisory firms (UK & US): a senior financial
analyst available 24/7, on top of every client's accounting system.

Live at **[alphatense.com](https://alphatense.com)** — frontend on Vercel,
backend on Railway, real per-advisor accounts, SQLite persistence.

This repository contains the **FP&A engine** (Phase 1 of the product plan)
and most of Phase 2: Excel/CSV ingestion, KPIs, variance analysis,
forecast, AR/AP aging and cash flow with natural-language narrative, a
conversational agent on Claude, real Xero OAuth2 integration, a React
frontend with real accounts, and executive PDF generation — on a
native multi-client architecture (one advisory firm manages dozens of
clients from a single dashboard).

See `PROGRESS.md` for the session-by-session build log: what was built,
what technical decisions were made and why, and what's still blocked.

## Current status

**Phase 1 — MVP (complete)**
- [x] Multi-client Excel/CSV ingestion and validation
- [x] KPI engine (revenue, gross margin, EBITDA, net income)
- [x] Variance analysis (actual vs budget, actual vs prior period) with
      automatic narrative and detection of the account that drove the
      variance most
- [x] Multi-client orchestrator (`Workspace`) that processes a file with
      many clients/periods in a single call
- [x] One-click executive PDF report
- [x] React frontend consuming the full API, with real accounts and a
      marketing landing page
- [x] Conversational FP&A agent, verified live against a real Anthropic
      API key
- [x] Real per-advisor accounts (email/password) with SQLite persistence
      — each advisory firm only sees its own client portfolio

**Phase 2 — in progress**
- [x] Forecast AI with scenarios (best/base/worst) from each client's
      actuals history, with narrative on the assumed growth rates
- [x] HTTP API (FastAPI) exposing the whole engine
- [x] AR/AP aging agent
- [x] Cash flow agent (13-week projection from AR/AP invoices with due
      dates)
- [x] Real Xero connector — OAuth2 authorization-code + refresh flow,
      `RealXeroClient` verified live against a real trial org
- [ ] QuickBooks connector — **data mapping built and tested against a
      simulated adapter**, `RealQuickBooksClient` still needs Intuit
      developer OAuth credentials
- [x] Public deployment (Railway + Vercel), custom domain
      (`alphatense.com`)

**What's left:** validate with 5-10 real UK advisory firms (business step,
not code), and the QuickBooks OAuth credentials to finish that connector.

## Structure

```
backend/
  app/
    models/domain.py       # Advisor, Client, LineItem, FinancialStatement, KPISet, VarianceResult,
                            # ForecastResult, Invoice, AgingReport, CashFlowForecast
    db/                     # SQLite persistence: database.py (engine/session), models.py (SQLAlchemy
                            # tables: AdvisorAccount, Session, WorkspaceRecord), repository.py (data access)
    ingestion/parser.py     # Excel/CSV -> FinancialStatement (schema validation)
    ingestion/invoices.py   # Excel/CSV -> Invoice (AR/AP invoice schema, separate from the above)
    engine/kpis.py          # FinancialStatement -> KPISet
    engine/variance.py      # KPISet actual vs budget/prior -> VarianceResult (+ narrative)
    engine/forecast.py      # actuals history -> ForecastResult (best/base/worst)
    engine/aging.py         # AR/AP invoices -> AgingReport (buckets by days overdue)
    engine/cash_flow.py     # AR/AP invoices -> CashFlowForecast (week-by-week projected balance)
    engine/workspace.py     # Multi-client orchestrator: one file -> reports + forecasts + aging + cash flow
    agents/fpa_agent.py     # Conversational agent (Claude) over the engine's 5 capabilities
    reporting/pdf_report.py # ClientReport (+ optional forecast/aging/cash flow) -> executive PDF
    integrations/xero/      # Xero connector: client.py (Protocol + Fake/RealXeroClient), mapper.py,
                            # sync.py, oauth.py (OAuth2 authorization-code + refresh flow)
    integrations/quickbooks/ # QuickBooks connector: client.py (Protocol + FakeQuickBooksClient),
                            # mapper.py, sync.py -- simulated, RealQuickBooksClient still pending
    api/main.py              # FastAPI: exposes the whole engine over HTTP, incl. /auth/* routes
    api/auth.py               # Per-advisor bearer-token auth (see "Accounts & persistence" below)
  sample_data/sample_financials.csv  # 2 sample clients, 3 scenarios each
  sample_data/sample_invoices.csv    # sample AR/AP invoices covering all 5 aging buckets
  tests/                  # pytest, coverage for every module above (144 tests)
  run_demo.py             # end-to-end console demo

frontend/                 # React + Vite + TypeScript + Tailwind v4
  src/
    pages/                 # LandingPage, LoginPage, SignupPage, UploadPage, PortfolioPage,
                            # ClientDetailPage, ChatPage
    components/            # KpiCard, VarianceTable, ForecastChart, AgingSection, CashFlowChart,
                            # InvoiceUpload, RequireAuth, layout/TopNav, ui/ (Button, Card, TextInput, ...)
    auth/context.ts         # Current-advisor React context (name, workspace_ids), used by TopNav
    api/client.ts            # Typed HTTP client against the API above
```

## Running it locally

```bash
cd backend
pip install -r requirements.txt

# run the tests
pytest -v

# see the engine in action against the sample data
python run_demo.py

# start the HTTP API on http://127.0.0.1:8000
uvicorn app.api.main:app --reload
```

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, points at the API on 127.0.0.1:8000 by default
```

Copy `backend/.env.example` to `backend/.env` and fill in:
- `ANTHROPIC_API_KEY` — for the conversational agent. Without it, `POST
  /workspaces/{id}/chat` returns `503` in a controlled way instead of
  failing confusingly.
- `DATABASE_PATH` — optional, defaults to `./data/alphatense.db` for local
  dev. In production this points at a Railway persistent volume mount so
  advisor accounts and uploaded data survive restarts.
- `XERO_CLIENT_ID` / `XERO_CLIENT_SECRET` / `XERO_REDIRECT_URI` — for the
  real Xero OAuth connector.

## Accounts & persistence

Each advisory firm has its own account (`POST /auth/signup`, email +
password, bcrypt-hashed) and only sees the workspaces it created — ownership
is enforced on every workspace-scoped route. Sessions are opaque bearer
tokens (SHA-256-hashed in the database, 30-day expiry, no JWT). Workspace
data (P&L statements + invoices) is cached in memory for the life of the
process but persisted to SQLite on every write, so a server restart just
means the next request rehydrates from disk instead of losing data.

## Expected data schema

### Financials (P&L) Excel/CSV

| column      | description                                                          |
|-------------|-----------------------------------------------------------------------|
| client_id   | client identifier (or use `client_name` and it's derived automatically) |
| period      | period label, e.g. `2026-06`                                          |
| scenario    | `actual`, `budget`, or `prior`                                        |
| account     | account name, e.g. `Marketing`                                        |
| category    | `revenue`, `cogs`, `opex`, `other_income`, `other_expense`, `tax`      |
| amount      | numeric amount (expenses as positive)                                 |

See `backend/sample_data/sample_financials.csv` for a full example with two
clients.

### AR/AP invoices Excel/CSV (optional, enables aging and cash flow)

| column        | description                                                    |
|---------------|-------------------------------------------------------------------|
| client_id     | client identifier (or `client_name`, same as above)                |
| invoice_id    | invoice identifier, e.g. `INV-1042`                                |
| type          | `ar` (accounts receivable) or `ap` (accounts payable)              |
| counterparty  | end customer name (AR) or vendor name (AP)                        |
| issue_date    | issue date, ISO (`2026-06-15`)                                     |
| due_date      | due date, ISO                                                      |
| amount        | total invoice amount                                               |
| amount_paid   | optional, default 0 — amount already collected/paid                |

See `backend/sample_data/sample_invoices.csv` for a full example.

## Multi-client design

`Workspace` indexes every line by `(client_id, period, scenario)` and
exposes `build_portfolio_report()`, which computes KPIs and variance
analysis for every client in an advisory firm's portfolio in a single call.
Adding a new client means adding rows to the source file (or connecting a
new Xero org) — the engine itself never changes.

## Forecast AI (Phase 2)

`engine/forecast.py` projects every P&L category (revenue, cogs, opex,
etc.) using the average growth rate from a client's actuals history. The
**base** case uses that average rate; **best** and **worst** add/subtract
one standard deviation of that same rate's historical volatility. A client
with a stable history (like Acme in the sample data) gets a narrow scenario
spread; a client with a volatile history (like Beacon, which had a rough
month) gets a wider one — the spread between scenarios is real information
about risk, not decoration.

Deliberately deterministic (no LLM call): every number can be traced back
to a concrete growth rate an advisor can audit.

## AR/AP aging and cash flow (Phase 2)

`engine/aging.py` buckets a client's open invoices (AR or AP) by days
overdue (current, 1-30, 31-60, 61-90, 90+), with narrative naming the
counterparty with the largest open balance.

`engine/cash_flow.py` projects the cash balance week by week (13 weeks by
default) from those same AR/AP invoices, plus a starting balance the
advisor supplies (there's no bank feed in the system). Deliberately doesn't
mix in an average of historical opex as a recurring outflow, to avoid
double-counting against the AP invoices that already represent part of
those expenses — that scope is explicit in the result's narrative.

Both require uploading an invoices file (`POST /workspaces/{id}/invoices`)
in addition to the financials file.

## Xero connector (real, live)

`app/integrations/xero/` implements a full OAuth2 authorization-code +
refresh flow (`oauth.py`) and a `RealXeroClient` implementing the same
`XeroClient` Protocol as `FakeXeroClient`, so the sync route needs no
changes to swap between them. Verified live against a real Xero trial org:
OAuth consent, and real `Invoices`/`Accounts`/`Contacts` calls. P&L is
built from `Reports/ProfitAndLoss` (not raw `Journals`, which 401s under
Xero's newer granular-scope model with no scope able to unlock it).
`GET /xero/connect` starts the consent flow; `GET /xero/callback` is the
OAuth redirect target. `POST /workspaces/{id}/xero/sync` (body
`{tenant_id, client_id, period}`) uses `RealXeroClient` once a tenant has
connected, otherwise falls back to `FakeXeroClient` (fixtures for
`tenant_id="demo-tenant-xero"`).

## QuickBooks connector (simulated)

`app/integrations/quickbooks/` maps the real QuickBooks Online API
(`Invoice`, `Bill`, `JournalEntry`, `Account` — same call as Xero: the
nested `reports/ProfitAndLoss` report was skipped in favor of
`JournalEntry`+`Account`, much simpler to flatten) to our
`Invoice`/`FinancialStatement`. Unlike Xero, QuickBooks splits AR and AP
into two entities (`Invoice` and `Bill`) and its `Balance` field is the
**outstanding** balance, not the paid amount — the
`amount_paid = TotalAmt - Balance` conversion is documented in
`mapper.py`. `FakeQuickBooksClient` returns fixtures with that same shape
for a demo realm (`demo-realm-quickbooks`) — no real OAuth yet. Same
`client.py`/`mapper.py`/`sync.py` pattern as Xero, so a
`RealQuickBooksClient` swaps in without touching anything else. `POST
/workspaces/{id}/quickbooks/sync` (body `{realm_id, client_id, period}`)
uses the simulation today.

## Conversational agent (Phase 1/2)

`app/agents/fpa_agent.py` exposes the engine's five capabilities (portfolio
summary, client report, forecast, aging, cash flow) as Claude tools
(`claude-opus-4-8`, via the Anthropic SDK) so an advisor can ask in plain
English instead of navigating the API or UI by hand. The agent never
computes anything itself — it only decides which tool to call and narrates
the result, so every number is still exactly what the deterministic engine
returns.

Requires `ANTHROPIC_API_KEY` in `backend/.env` (already configured in
production). Without it, `POST /chat` returns `503` instead of failing
confusingly.

## Executive PDF (Phase 1)

`app/reporting/pdf_report.py` (ReportLab, no system dependencies) generates
a PDF with KPIs, variance analysis, forecast, and — if the `as_of`/
`starting_balance` params are passed — aging and cash flow too. It's the
document an advisor sends their client or uses in the monthly review
meeting.

## HTTP API

`app/api/main.py` exposes the whole engine over HTTP with FastAPI. Every
workspace-scoped route requires a bearer token (see "Accounts &
persistence" above) and enforces that the workspace belongs to the
authenticated advisor.

| method | route | what it does |
|--------|-------|----------|
| GET  | `/health` | health check |
| POST | `/auth/signup` | create an advisor account, get a session token |
| POST | `/auth/login` | log in, get a session token |
| POST | `/auth/logout` | invalidate the current session token |
| GET  | `/auth/me` | current advisor + their workspace_ids |
| POST | `/workspaces` | upload a financials CSV/Excel and create a workspace |
| POST | `/workspaces/{id}/invoices` | upload an AR/AP invoices CSV/Excel into the workspace |
| GET  | `/workspaces/{id}/clients` | list the `client_id`s found |
| GET  | `/workspaces/{id}/portfolio` | KPIs + variance for every client/period |
| GET  | `/workspaces/{id}/clients/{client_id}/report?period=2026-06` | one client/period's report |
| GET  | `/workspaces/{id}/clients/{client_id}/report/pdf?period=...&as_of=...&starting_balance=...` | executive PDF |
| GET  | `/workspaces/{id}/clients/{client_id}/forecast?periods_ahead=3` | best/base/worst forecast |
| GET  | `/workspaces/{id}/portfolio/forecast?periods_ahead=3` | forecast for the whole portfolio |
| GET  | `/workspaces/{id}/clients/{client_id}/aging?type=ar\|ap&as_of=2026-06-30` | AR or AP aging |
| GET  | `/workspaces/{id}/clients/{client_id}/cash-flow?starting_balance=...&as_of=...&weeks_ahead=13` | cash flow projection |
| POST | `/workspaces/{id}/chat` | ask the conversational agent |
| GET  | `/xero/connect` / `/xero/callback` | Xero OAuth2 consent flow |
| POST | `/workspaces/{id}/xero/sync` | sync a client from Xero (real once connected, else simulated) |
| POST | `/workspaces/{id}/quickbooks/sync` | sync a client from QuickBooks (simulated today) |

With the server running, interactive docs (Swagger) are available at
`http://127.0.0.1:8000/docs`.

## Live deployment

- Frontend: Vercel, custom domain `alphatense.com` / `www.alphatense.com`.
- Backend: Railway, `api.alphatense.com`, with a persistent volume for the
  SQLite database.
- Both auto-deploy on push to `main`.

## Next steps

1. Validate pricing and real pain with 5-10 UK advisory firms — business
   step, not code, now that there's a real URL with real accounts to send
   instead of asking prospects to clone the repo.
2. QuickBooks connector — data mapping already built, blocked on Intuit
   developer OAuth credentials.
3. Further visual/UX polish as real advisor feedback comes in (a proper
   post-login dashboard, richer navigation, etc.) — deliberately scoped
   incrementally rather than upfront.
