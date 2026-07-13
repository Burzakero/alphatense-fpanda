# Finance Alphatense AI

Copiloto de IA para asesorías financieras (UK & US): un analista financiero
senior disponible 24/7, encima del ERP de cada cliente.

Este repositorio contiene el **motor FP&A** (Fase 1 del plan de producto) y
gran parte de Fase 2: ingesta de Excel/CSV, KPIs, variance analysis,
forecast, aging AR/AP y cash flow con narrativa en lenguaje natural, un
agente conversacional sobre Claude, un frontend React que consume todo
eso, y generación de PDF ejecutivo — sobre una arquitectura multi-cliente
nativa (una asesoría gestiona decenas de clientes desde un panel único).

Ver `PROGRESS.md` para el detalle sesión a sesión de qué se construyó, qué
decisiones técnicas se tomaron y por qué, y qué sigue bloqueado.

## Estado actual

**Fase 1 -- MVP (completo)**
- [x] Ingesta y validación de Excel/CSV multi-cliente
- [x] Motor de cálculo de KPIs (revenue, gross margin, EBITDA, net income)
- [x] Variance analysis (actual vs budget, actual vs periodo anterior) con
      narrativa automática y detección de la cuenta que más contribuyó al
      desvío
- [x] Orquestador multi-cliente (`Workspace`) que procesa un archivo con
      varios clientes/periodos en una sola llamada
- [x] Generación del informe ejecutivo en PDF con un clic
- [x] Frontend (React) que consume la API completa
- [ ] Conector Xero -- **mapeo de datos construido y probado contra un
      adaptador simulado**, falta el `RealXeroClient` (credenciales OAuth
      reales)
- [ ] Agente FP&A conversacional -- **construido**, pendiente de
      `ANTHROPIC_API_KEY` para probarlo en vivo

**Fase 2 -- en progreso**
- [x] Forecast AI con escenarios (best/base/worst) a partir del historial
      de actuals de cada cliente, con narrativa de las tasas de crecimiento
      asumidas
- [x] API HTTP (FastAPI) que expone todo el motor por HTTP
- [x] Agente de aging AR/AP (antigüedad de cuentas por cobrar/pagar)
- [x] Agente de cash flow (proyección de 13 semanas a partir de facturas
      AR/AP con fecha de vencimiento)
- [ ] Conector QuickBooks (requiere credenciales OAuth reales)
- [ ] Deploy público (Railway + Vercel) -- código listo, falta el signup
      del usuario

## Estructura

```
backend/
  app/
    models/domain.py      # Advisor, Client, LineItem, FinancialStatement, KPISet, VarianceResult,
                           # ForecastResult, Invoice, AgingReport, CashFlowForecast
    ingestion/parser.py    # Excel/CSV -> FinancialStatement (validación de esquema)
    ingestion/invoices.py  # Excel/CSV -> Invoice (esquema de facturas AR/AP, separado del anterior)
    engine/kpis.py         # FinancialStatement -> KPISet
    engine/variance.py     # KPISet actual vs budget/prior -> VarianceResult (+ narrativa)
    engine/forecast.py     # historial de actuals -> ForecastResult (best/base/worst)
    engine/aging.py        # facturas AR/AP -> AgingReport (buckets por días de vencimiento)
    engine/cash_flow.py    # facturas AR/AP -> CashFlowForecast (balance proyectado semana a semana)
    engine/workspace.py    # Orquestador multi-cliente: un archivo -> reportes + forecasts + aging + cash flow
    agents/fpa_agent.py    # Agente conversacional (Claude) sobre las 5 capacidades del motor
    reporting/pdf_report.py # ClientReport (+ forecast/aging/cash flow opcionales) -> PDF ejecutivo
    integrations/xero/     # Conector Xero: client.py (Protocol + FakeXeroClient), mapper.py, sync.py
    api/main.py            # FastAPI: expone el motor completo por HTTP
    api/auth.py             # Gate de acceso compartido para el deploy público (no-op en dev local)
  sample_data/sample_financials.csv  # 2 clientes de ejemplo, 3 escenarios cada uno
  sample_data/sample_invoices.csv    # facturas AR/AP de ejemplo, cubriendo los 5 buckets de aging
  tests/                 # pytest, cobertura de cada módulo de arriba
  run_demo.py            # demo end-to-end por consola

frontend/                # React + Vite + TypeScript + Tailwind
  src/
    pages/                # UploadPage, PortfolioPage, ClientDetailPage, ChatPage
    components/           # KpiCard, VarianceTable, ForecastChart, AgingSection, CashFlowChart,
                          # InvoiceUpload, AccessGate
    api/client.ts         # cliente HTTP tipado contra la API de arriba
```

## Cómo correrlo

```bash
cd backend
pip install -r requirements.txt

# correr los tests
pytest -v

# ver el motor en acción con los datos de ejemplo
python run_demo.py

# levantar la API HTTP en http://127.0.0.1:8000
uvicorn app.api.main:app --reload
```

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, apunta a la API en 127.0.0.1:8000 por defecto
```

Para el agente conversacional, copiar `backend/.env.example` a `backend/.env`
y completar `ANTHROPIC_API_KEY`. Sin esa variable, `POST /chat` responde
`503` de forma controlada (no rompe el resto de la API).

## Esquema de datos esperado

### Excel/CSV de financials (P&L)

| columna     | descripción                                                          |
|-------------|-----------------------------------------------------------------------|
| client_id   | identificador del cliente (o usar `client_name` y se deriva solo)     |
| period      | etiqueta de periodo, ej. `2026-06`                                     |
| scenario    | `actual`, `budget`, o `prior`                                          |
| account     | nombre de la cuenta contable, ej. `Marketing`                          |
| category    | `revenue`, `cogs`, `opex`, `other_income`, `other_expense`, `tax`      |
| amount      | monto numérico (gastos como positivos)                                |

Ver `backend/sample_data/sample_financials.csv` para un ejemplo completo con
dos clientes.

### Excel/CSV de facturas AR/AP (opcional, habilita aging y cash flow)

| columna       | descripción                                                    |
|---------------|-------------------------------------------------------------------|
| client_id     | identificador del cliente (o `client_name`, igual que arriba)     |
| invoice_id    | identificador de la factura, ej. `INV-1042`                       |
| type          | `ar` (cuenta por cobrar) o `ap` (cuenta por pagar)                 |
| counterparty  | nombre del cliente final (AR) o proveedor (AP)                    |
| issue_date    | fecha de emisión, ISO (`2026-06-15`)                               |
| due_date      | fecha de vencimiento, ISO                                          |
| amount        | monto total de la factura                                          |
| amount_paid   | opcional, default 0 -- monto ya cobrado/pagado                     |

Ver `backend/sample_data/sample_invoices.csv` para un ejemplo completo.

## Diseño multi-cliente

`Workspace` indexa todas las líneas por `(client_id, period, scenario)` y
expone `build_portfolio_report()`, que calcula KPIs y variance analysis para
todos los clientes de una asesoría en una sola llamada. Agregar un cliente
nuevo es agregar filas al archivo fuente (o, en fases futuras, conectar un
nuevo org de Xero) — el motor no cambia.

## Forecast AI (Fase 2)

`engine/forecast.py` proyecta cada categoría del P&L (revenue, cogs, opex,
etc.) tomando la tasa de crecimiento promedio del historial de actuals de
un cliente. El caso **base** usa esa tasa promedio; **best** y **worst**
suman/restan un desvío estándar de la volatilidad histórica de esa misma
tasa. Es decir: un cliente con historial estable (como Acme en los datos de
ejemplo) obtiene un abanico de escenarios angosto, y un cliente con
historial volátil (como Beacon, que tuvo un mes flojo) obtiene un abanico
más amplio — el spread entre escenarios es información real sobre el
riesgo, no un adorno.

Es deliberadamente determinístico (sin llamada a un LLM): cada número se
puede rastrear hasta una tasa de crecimiento concreta que el asesor puede
auditar.

## Aging AR/AP y cash flow (Fase 2)

`engine/aging.py` bucketea las facturas abiertas de un cliente (AR o AP)
por días de vencimiento (current, 1-30, 31-60, 61-90, 90+), con narrativa
que nombra a la contraparte con mayor saldo abierto.

`engine/cash_flow.py` proyecta el balance de caja semana a semana (13
semanas por defecto) a partir de esas mismas facturas AR/AP, más un balance
inicial que provee el asesor (no hay bank feed en el sistema). Deliberadamente
no mezcla un promedio de opex histórico como salida recurrente, para evitar
doble conteo contra las facturas de AP que ya representan parte de esos
gastos -- el scope queda explícito en la narrativa del resultado.

Ambos requieren subir un archivo de facturas (`POST /workspaces/{id}/invoices`)
además del archivo de financials.

## Conector Xero (simulado)

`app/integrations/xero/` mapea la API real de Xero (`Invoices`, `Journals`,
`Accounts` -- se descartó el reporte anidado `Reports/ProfitAndLoss` a favor
de `Journals`+`Accounts`, mucho más simple de aplanar) a nuestros
`Invoice`/`FinancialStatement`. `FakeXeroClient` devuelve fixtures con esa
misma forma para un tenant demo (`demo-tenant-xero`) -- no hay OAuth real
todavía. `client.py`/`mapper.py`/`sync.py` están separados justo para que
un `RealXeroClient` (cuando haya credenciales) se intercambie sin tocar el
resto. `POST /workspaces/{id}/xero/sync` (body `{tenant_id, client_id,
period}`) usa la simulación hoy.

## Agente conversacional (Fase 1/2)

`app/agents/fpa_agent.py` expone las cinco capacidades del motor (resumen de
portfolio, reporte de cliente, forecast, aging, cash flow) como tools de
Claude (`claude-opus-4-8`, vía el SDK de Anthropic) para que un asesor
pregunte en lenguaje natural en vez de navegar la API o la UI a mano. El
agente nunca calcula nada por su cuenta -- solo decide qué tool llamar y
narra el resultado, así que cada número sigue siendo el mismo que devuelve
el motor determinístico.

Requiere `ANTHROPIC_API_KEY` en `backend/.env`. Sin ella, `POST /chat`
responde `503` en vez de fallar de forma confusa.

## PDF ejecutivo (Fase 1)

`app/reporting/pdf_report.py` (ReportLab, sin dependencias de sistema)
genera un PDF con KPIs, variance analysis, forecast, y -- si se pasan los
parámetros `as_of`/`starting_balance` -- también aging y cash flow. Es el
documento que un asesor le manda a su cliente o usa en la reunión mensual.

## API HTTP

`app/api/main.py` expone el motor completo por HTTP con FastAPI. No hay
base de datos: cada archivo subido se procesa en memoria bajo un
`workspace_id` (UUID), válido mientras el proceso siga corriendo.

| método | ruta | qué hace |
|--------|------|----------|
| GET  | `/health` | chequeo de salud |
| POST | `/workspaces` | sube un CSV/Excel de financials y crea un workspace |
| POST | `/workspaces/{id}/invoices` | sube un CSV/Excel de facturas AR/AP al workspace |
| GET  | `/workspaces/{id}/clients` | lista los `client_id` encontrados |
| GET  | `/workspaces/{id}/portfolio` | KPIs + variance de todos los clientes/periodos |
| GET  | `/workspaces/{id}/clients/{client_id}/report?period=2026-06` | reporte de un cliente/periodo |
| GET  | `/workspaces/{id}/clients/{client_id}/report/pdf?period=...&as_of=...&starting_balance=...` | PDF ejecutivo |
| GET  | `/workspaces/{id}/clients/{client_id}/forecast?periods_ahead=3` | forecast best/base/worst |
| GET  | `/workspaces/{id}/portfolio/forecast?periods_ahead=3` | forecast de todo el portfolio |
| GET  | `/workspaces/{id}/clients/{client_id}/aging?type=ar\|ap&as_of=2026-06-30` | aging AR o AP |
| GET  | `/workspaces/{id}/clients/{client_id}/cash-flow?starting_balance=...&as_of=...&weeks_ahead=13` | proyección de cash flow |
| POST | `/workspaces/{id}/chat` | pregunta al agente conversacional |
| POST | `/workspaces/{id}/xero/sync` | sincroniza un cliente desde Xero (simulado hoy, `FakeXeroClient`) |

Con el servidor corriendo, la documentación interactiva (Swagger) queda
disponible en `http://127.0.0.1:8000/docs`.

## Próximos pasos

1. El usuario consigue `ANTHROPIC_API_KEY` y hace el signup en Railway +
   Vercel (código listo para ambos, ver `PROGRESS.md`).
2. Validar tarifas y dolor real con 5-10 asesorías UK, mandando la URL
   deployada en vez de pedir clonar el repo.
3. Conector Xero (bloqueado por credenciales OAuth reales).
4. Conector QuickBooks (mismo bloqueo).
5. Pulido visual del frontend (diseño, responsive, loading states) --
   deliberadamente pospuesto hasta el final del proyecto.
