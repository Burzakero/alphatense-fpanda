# CLAUDE.md — Alphatense FP&A

Contexto de proyecto para Claude Code. Para el detalle sesión a sesión ver
`PROGRESS.md`; para la documentación orientada a producto/API ver
`README.md`. Este archivo es el resumen operativo para retomar el trabajo
sin perder contexto.

## Qué es esto

Alphatense es un copiloto de IA para asesorías financieras (UK & US): un
analista financiero senior disponible 24/7, encima del ERP de cada
cliente. El repo contiene el motor FP&A (ingestión, KPIs, variance,
forecast, aging AR/AP, cash flow), un agente conversacional sobre Claude,
conectores Xero/QuickBooks (simulados), un frontend React, y generación de
PDF ejecutivo — todo sobre una arquitectura multi-cliente nativa (una
asesoría gestiona decenas de clientes desde un panel único).

Plan de producto real: 3 fases (Fase 1 MVP UK beachhead, Fase 2
Consolidación con QuickBooks + más agentes, Fase 3 Escala con
SAP/Oracle/Dynamics). Este repo cubre Fase 1 completa y gran parte de
Fase 2.

## Arquitectura y convenciones

- **Backend**: Python 3.12, FastAPI, Pydantic v2, pandas, pytest,
  ReportLab (PDF — se eligió sobre WeasyPrint para evitar dependencias de
  sistema tipo GTK/Pango), Anthropic SDK (`claude-opus-4-8`, Tool Runner).
- **Frontend**: React + Vite + TypeScript + Tailwind v4 (usa el plugin
  `@tailwindcss/vite`, no PostCSS), `react-router-dom`, `recharts`.
- **Filosofía de capas** (seguida en todo el proyecto, no romper el
  patrón): funciones de motor puras/determinísticas sin I/O
  (`engine/kpis.py`, `engine/variance.py`, `engine/aging.py`,
  `engine/cash_flow.py`, `engine/forecast.py`) → `models` → `ingestion` →
  `engine` → `api`. Cada feature nueva del motor tiene su propio archivo,
  sus propios tests, y su narrativa/supuestos documentados explícitamente
  en el código (nunca escondidos).
- **Multi-tenant**: `Workspace` (`engine/workspace.py`) indexa todo por
  `(client_id, period, scenario)`. Es el orquestador central: agregar un
  cliente nuevo es agregar filas al archivo fuente o sincronizar un
  conector, el motor no cambia.
- **Patrón de conector** (Xero, QuickBooks): `client.py` (Protocol +
  implementación Fake con fixtures realistas) / `mapper.py` (transforms
  puros raw JSON → domain objects) / `sync.py` (orquestación). Diseñado
  para que un `Real*Client` que implemente el mismo Protocol se
  intercambie después sin tocar `mapper.py`, `sync.py` ni la ruta de la
  API. **Antes de simular una API externa, investigar la forma real** (vía
  un subagente de research) — una simulación que no calza con el esquema
  real no sirve el día que llegue la key.
- **Decisiones de scope deliberadas, documentadas en código**: el cash
  flow forecast excluye a propósito el promedio de opex histórico (evita
  doble conteo contra las facturas de AP) — scope limitado a facturas
  AR/AP, con narrativa explícita de la limitación.
- Comentarios en el código: solo cuando el *por qué* no es obvio (un
  supuesto, una conversión que rompe fácil, un caso límite). No comentar
  el *qué* — los nombres ya lo dicen.

## Estructura

```
backend/app/
  models/domain.py         # Advisor, Client, LineItem, FinancialStatement, KPISet,
                            # VarianceResult, ForecastResult, Invoice, AgingReport, CashFlowForecast
  ingestion/parser.py       # Excel/CSV -> FinancialStatement
  ingestion/invoices.py      # Excel/CSV -> Invoice (esquema separado)
  engine/kpis.py             # FinancialStatement -> KPISet
  engine/variance.py         # KPISet actual vs budget/prior -> VarianceResult + narrativa
  engine/forecast.py         # historial -> ForecastResult (best/base/worst)
  engine/aging.py            # facturas -> AgingReport (buckets por días de vencimiento)
  engine/cash_flow.py        # facturas -> CashFlowForecast (balance semanal proyectado)
  engine/workspace.py        # Orquestador multi-cliente
  agents/fpa_agent.py        # Agente conversacional (Claude), 5 tools sobre Workspace
  reporting/pdf_report.py    # ClientReport (+forecast/aging/cash flow opcionales) -> PDF
  integrations/xero/         # client.py, mapper.py, sync.py (simulado, ver abajo)
  integrations/quickbooks/   # ídem, para QuickBooks (simulado, ver abajo)
  api/main.py                 # FastAPI: expone todo por HTTP
  api/auth.py                  # Gate de acceso compartido (no-op sin DEMO_ACCESS_KEY)
backend/sample_data/          # sample_financials.csv, sample_invoices.csv
backend/tests/                 # pytest, un archivo por módulo de arriba
frontend/src/
  pages/                     # UploadPage, PortfolioPage, ClientDetailPage, ChatPage
  components/                # KpiCard, VarianceTable, ForecastChart, AgingSection,
                              # CashFlowChart, InvoiceUpload, AccessGate
  api/client.ts               # cliente HTTP tipado contra la API
```

## Cómo correrlo

```bash
cd backend
pip install -r requirements.txt
pytest -v                              # 120/120 pasando
python run_demo.py                     # motor por consola con datos de ejemplo
uvicorn app.api.main:app --reload      # API en http://127.0.0.1:8000 (Swagger en /docs)
```

```bash
cd frontend
npm install
npm run dev                            # http://localhost:5173
```

Agente conversacional: copiar `backend/.env.example` a `backend/.env` y
completar `ANTHROPIC_API_KEY`. Sin esa variable, `POST /chat` responde
`503` de forma controlada.

Nota Windows: `uvicorn --reload` no siempre recarga limpio tras editar
`app/api/main.py` — si los cambios no se reflejan, reiniciar el proceso
manualmente.

## Estado actual (2026-07-14)

**Todo lo avanzable sin acción del usuario está construido y probado.**
120/120 tests backend + typecheck de frontend limpio. Lo que queda
pendiente depende enteramente de acciones externas del usuario:

1. **Deploy (Railway + Vercel)** — código 100% listo (`auth.py`, CORS
   configurable, `Procfile`, `vercel.json`, `AccessGate.tsx`). Falta que
   el usuario haga el signup manual en ambas plataformas (requiere login
   interactivo por navegador, no completable desde este entorno). Checklist
   completo en `PROGRESS.md`.
2. **Agente conversacional** — construido y testeado (`fpa_agent.py`,
   `POST /chat`, UI de chat), bloqueado por `ANTHROPIC_API_KEY` real.
3. **Conector Xero — COMPLETO, verificado en vivo (2026-07-18)**.
   `RealXeroClient` con OAuth2 real funcionando end-to-end contra la org
   trial "Alphatense FP&A" (login, consentimiento, Invoices/Accounts/
   Contacts/P&L Report todos reales). Nota: `GET /Journals` resultó
   inaccesible bajo el modelo de scopes granulares de Xero (401 confirmado,
   no hay scope que lo cubra) — el P&L se construye vía
   `Reports/ProfitAndLoss` en su lugar (ver `PROGRESS.md` para el detalle).
   Pendiente real, no de código: la org trial no tiene transacciones
   cargadas, así que los números del P&L real quedan sin verificar hasta
   validar con un cliente real.
4. **Conector QuickBooks** — mismo estado que Xero (`FakeQuickBooksClient`,
   completo y verificado). Falta `RealQuickBooksClient` con OAuth real
   (registro en Intuit developer).
5. **Validación con asesorías reales (5-10 en UK)** — paso de negocio, no
   de código, una vez deployado.
6. **Pulido visual del frontend** (diseño, responsive, loading states) —
   deliberadamente pospuesto para el final del proyecto; toda la
   funcionalidad de negocio ya está expuesta en la UI, solo falta el
   trabajo visual.

`git push` también quedó pendiente del usuario en su momento (requiere
login interactivo por navegador con GitHub, no completable desde este
entorno) — verificar `git log origin/main..HEAD` para ver si ya está al día.

## Qué NO hacer sin confirmar con el usuario

- No arrancar el `RealXeroClient`/`RealQuickBooksClient` sin confirmar que
  las credenciales OAuth ya existen.
- No invertir tiempo en pulido visual del frontend sin que lo pida
  explícitamente — es una decisión de scope ya tomada.
- No asumir que el deploy o la API key ya están resueltos — verificar el
  estado real (¿existe `backend/.env` con la key? ¿hay una URL de Railway/
  Vercel?) antes de dar por hecho que se resolvió.

## Preferencias de trabajo confirmadas

- El usuario aprueba planes rápido — usar `EnterPlanMode` antes de
  features multi-archivo y ofrecer una opción "(Recomendado)" en
  `AskUserQuestion` cuando haya una decisión a tomar.
- Verificar siempre contra el servidor real corriendo (no solo tests
  unitarios) antes de dar una feature por terminada.
- Commits por feature, no un commit gigante al final.
