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
  pages/                     # LandingPage, LoginPage, SignupPage, TrialExpiredPage,
                              # HomePage, UploadPage, PortfolioPage, ClientDetailPage,
                              # ChatPage, AdminLeadsPage
  components/                # KpiCard, VarianceTable, ForecastChart, AgingSection,
                              # CashFlowChart, InvoiceUpload, RequireAuth
                              # components/ui/ y components/landing/ para primitivas
                              # compartidas y las secciones de la landing
  api/client.ts               # cliente HTTP tipado contra la API
```

## Cómo correrlo

```bash
cd backend
pip install -r requirements.txt
pytest -v                              # 195/195 pasando
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

## Estado actual (2026-07-23)

**Deployado en vivo y en uso real**: `alphatense.com` (Vercel, frontend) +
`api.alphatense.com` (Railway, backend con SQLite sobre volumen
persistente). Login real por asesoría (no un secreto compartido), gate de
trial de 15 días con captura de leads (`/admin/leads`, con UI propia en
`/admin/leads`), UI completamente en inglés, landing pública rediseñada,
dashboard/portfolio/cliente reestructurados, PDF ejecutivo con branding +
gráficos + EBITDA bridge + narrativa IA, export a Excel. **195/195 tests
backend** + typecheck/lint de frontend limpio. Detalle sesión a sesión
(2026-07-19 a 2026-07-23) en `PROGRESS.md` — no repetido acá porque decae
rápido.

Lo que queda pendiente:

1. **Validación con asesorías reales (5-10 en UK)** — paso de negocio, no
   de código. Es la prioridad real ahora que el producto está deployado y
   accesible por URL. Ver `Marketing/` (carpeta hermana del repo, no
   versionada acá) para el plan de outreach.
2. **Conector QuickBooks** — mapeo simulado completo (`FakeQuickBooksClient`),
   mismo estado que tenía Xero antes de conectarse de verdad. Falta
   `RealQuickBooksClient` con OAuth real (registro en Intuit developer).
3. **Conector Xero — COMPLETO, verificado en vivo (2026-07-18)**.
   `RealXeroClient` con OAuth2 real funcionando end-to-end. Nota: `GET
   /Journals` resultó inaccesible bajo el modelo de scopes granulares de
   Xero (401 confirmado, no hay scope que lo cubra) — el P&L se construye
   vía `Reports/ProfitAndLoss` en su lugar (ver `PROGRESS.md` para el
   detalle). Pendiente real, no de código: la org trial no tiene
   transacciones cargadas, así que los números del P&L real quedan sin
   verificar hasta validar con un cliente real.
4. **Confirmar `ADMIN_SECRET` seteado en Railway** — sin esa env var en
   producción, `/admin/leads` siempre devuelve 404.
5. ~~Pulido visual del frontend~~ — **hecho**, ya no es un ítem pendiente
   (landing, dashboard, PDF y export todos con trabajo visual real entre
   2026-07-19 y 2026-07-22).

## Qué NO hacer sin confirmar con el usuario

- No arrancar el `RealQuickBooksClient` sin confirmar que las credenciales
  OAuth ya existen.
- No asumir que el deploy, las API keys o las credenciales OAuth ya están
  resueltas — verificar el estado real (¿existe `backend/.env` con la key?
  ¿hay una URL de Railway/Vercel? ¿está `ADMIN_SECRET` seteado en Railway?)
  antes de dar por hecho que se resolvió.

## Preferencias de trabajo confirmadas

- El usuario aprueba planes rápido — usar `EnterPlanMode` antes de
  features multi-archivo y ofrecer una opción "(Recomendado)" en
  `AskUserQuestion` cuando haya una decisión a tomar.
- Verificar siempre contra el servidor real corriendo (no solo tests
  unitarios) antes de dar una feature por terminada.
- Commits por feature, no un commit gigante al final.
