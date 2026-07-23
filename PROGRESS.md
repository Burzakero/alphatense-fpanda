# Progreso del proyecto — Alphatense FP&A

Resumen de la sesión de trabajo del 2026-07-10. Complementa el `README.md`
(que describe la arquitectura y cómo correr el proyecto) con el estado real
de avance y lo que falta.

## Qué se hizo en esta sesión

### Entorno
- Se instaló Python 3.12.10 y Node.js 24 (LTS) vía `winget` — no estaban
  presentes en la máquina de desarrollo.
- Dependencias del backend instaladas (`backend/requirements.txt`).
- Suite de tests del backend corrida y verificada en verde antes de tocar
  nada (39/39 en ese momento).

### Frontend (nuevo, desde cero)
Se construyó `frontend/` — React + Vite + TypeScript + Tailwind v4 — como
primer consumidor real de la API del motor FP&A. Antes de esto la API solo
era accesible vía `curl`/Swagger.

- `UploadPage`: sube CSV/Excel, crea un workspace.
- `PortfolioPage`: KPIs + variance de todos los clientes/periodos, con
  badges de severidad.
- `ClientDetailPage`: reporte de un cliente/periodo (KPIs, variance vs
  budget/prior con narrativa) + gráfico de forecast best/base/worst
  (recharts) + botón de descarga del PDF ejecutivo.
- CORS habilitado en el backend (`CORSMiddleware`) para que el frontend
  (puerto 5173) pueda llamar a la API (puerto 8000) en desarrollo.
- Probado end-to-end en navegador: upload real del CSV de ejemplo,
  navegación a detalle de cliente, manejo de errores (archivo no soportado).

**Estado del frontend: funcional pero mínimo/sin pulir.** Es el "flujo
demostrable" mínimo para poder validar con asesorías — no tiene diseño
trabajado, responsive real, ni estados de carga/loading refinados. Se
decidió explícitamente **dejar el pulido de UI/UX para el final del
proyecto**, una vez que el resto de las piezas (conectores, agentes, PDF)
estén más maduras — no tiene sentido invertir tiempo en diseño antes de
validar que el producto en sí resuelve el problema.

### PDF ejecutivo con un clic
- `backend/app/reporting/pdf_report.py`: genera el PDF con **ReportLab**
  (pure-Python, sin dependencias de sistema tipo GTK/Pango — se descartó
  WeasyPrint por eso, dado que instalar el entorno ya costó fricción en
  esta máquina Windows).
- Nuevo endpoint `GET /workspaces/{id}/clients/{client_id}/report/pdf`.
- Contenido: KPIs del periodo, variance vs budget/prior con narrativa, y
  forecast best/base/worst si hay historial suficiente (se omite la
  sección en vez de fallar si no lo hay).
- 5 tests nuevos.

### Agente de Aging AR/AP
Primer "agente especializado" del backlog (backend only, sin frontend —
ver decisión de pulido de UI más abajo). Modelo de datos nuevo en paralelo
al de `FinancialStatement`/`LineItem`, sin tocarlos:

- `Invoice` (`app/models/domain.py`): factura individual con `issue_date`/
  `due_date` reales, `amount`/`amount_paid` → `balance`.
- `app/ingestion/invoices.py`: ingesta separada de `parser.py` (esquema de
  columnas totalmente distinto). `load_invoices()`.
- `app/engine/aging.py`: `calculate_aging()` — bucketing estándar (current,
  1-30, 31-60, 61-90, 90+) por días de vencimiento, con narrativa que
  nombra a la contraparte con mayor saldo abierto (mismo patrón que
  `_driver_phrase` en `engine/variance.py`).
- `Workspace.add_invoices()` / `Workspace.build_aging_report()`: las
  facturas se cargan a un workspace ya existente (no van en el mismo
  archivo que el P&L).
- Endpoints nuevos: `POST /workspaces/{id}/invoices` y `GET
  /workspaces/{id}/clients/{client_id}/aging?type=ar&as_of=YYYY-MM-DD`
  (`as_of` es obligatorio y explícito a propósito — un reporte financiero
  no debe depender silenciosamente de la fecha del reloj del servidor).
- `backend/sample_data/sample_invoices.csv`: facturas AR/AP de ejemplo
  para ambos clientes, cubriendo los 5 buckets y un caso de pago parcial.
- Probado end-to-end contra el servidor real corriendo (no solo tests):
  totales y buckets verificados a mano contra el CSV de ejemplo.

Cash flow (el otro agente especializado del backlog) sigue pendiente —
requiere modelar timing proyectado de cobros/pagos, más complejo que el
modelo de facturas con fecha de vencimiento que ya cubre aging.

### Agente FP&A conversacional — construido, bloqueado por API key
Según el plan de producto real, esto era lo que le faltaba a Fase 1 para
estar realmente completa (no solo el motor determinístico, sino algo con lo
que el asesor pueda conversar):

- `backend/app/agents/fpa_agent.py`: 4 tools (`get_portfolio_summary`,
  `get_client_report`, `get_client_forecast`, `get_client_aging`) que
  envuelven los métodos ya existentes de `Workspace` — el agente nunca
  calcula un número, solo decide qué tool llamar y narra el resultado.
  `claude-opus-4-8`, thinking adaptativo, Tool Runner beta del SDK.
- Endpoint `POST /workspaces/{id}/chat` (stateless — el caller reenvía el
  `history` que devuelve cada respuesta).
- `backend/.env.example` committeado; `.env` real (con la key) queda local,
  ya cubierto por `.gitignore`.
- **RESUELTO (2026-07-18)**: el usuario consiguió la `ANTHROPIC_API_KEY` y
  cargó créditos ($5) en console.anthropic.com. Key guardada en
  `backend/.env` (gitignored). Verificación end-to-end real hecha contra el
  servidor corriendo: se subió `sample_financials.csv`, se preguntó por el
  resumen del portfolio vía `POST /workspaces/{id}/chat`, y la respuesta
  citó cifras reales (2 clientes, revenue por cliente, variance vs. budget,
  tendencia mensual) — el agente conversacional queda confirmado como
  funcional, no solo testeado con mocks.

### Agente de cash flow
Segundo (y último) "agente especializado" del backlog original, después de
aging AR/AP. Forecast de cash flow a 13 semanas (horizonte estándar en
FP&A) a partir de las mismas facturas AR/AP que ya usa aging:

- `CashFlowWeek` / `CashFlowForecast` (`app/models/domain.py`).
- `app/engine/cash_flow.py`: `project_cash_flow()` — bucketing semanal
  hacia adelante (facturas vencidas van a la semana 0, las que vencen
  dentro del horizonte van a su semana correspondiente, más allá del
  horizonte se excluyen) y balance corriente semana a semana.
- **Decisión de scope deliberada**: solo considera facturas AR/AP con
  fecha de vencimiento cargada — no mezcla un promedio de opex histórico
  como salida de caja recurrente, para evitar doble conteo con las
  facturas de AP que ya representan parte de esos mismos gastos. El
  narrative del resultado deja esto explícito (gastos no facturados como
  nómina o alquiler no están incluidos).
- `Workspace.build_cash_flow_forecast(client_id, starting_balance, as_of, weeks_ahead=13)`
  — a diferencia de aging, siempre devuelve un resultado (sin facturas =
  balance plano, es una respuesta válida, no un error).
- Endpoint `GET /workspaces/{id}/clients/{client_id}/cash-flow?starting_balance=...&as_of=...&weeks_ahead=13`.
  `starting_balance` es provisto por el asesor a mano — no hay bank feed
  en el sistema.
- Quinto tool del agente conversacional: `get_client_cash_flow`.
- Verificado contra el servidor real con `sample_invoices.csv`: totales
  semanales y balance corriente calzan exactamente con el cálculo a mano.

### Deploy a Railway (backend) + Vercel (frontend) — código listo, falta que el usuario haga el signup
Para poder mandarle una URL real a un prospecto en vez de pedirle que
corra todo en su máquina. Sin dominio propio todavía — arranca con las
URLs gratuitas de cada plataforma.

- `backend/app/api/auth.py`: gate de acceso compartido (`verify_access_key`)
  aplicado a nivel de app (`FastAPI(dependencies=[...])`). Si
  `DEMO_ACCESS_KEY` no está seteada, no hace nada (cero fricción en dev
  local) — verificado con curl: sin key da 401, con key (por header
  `X-Demo-Key` o query param `?key=`) da 200.
- CORS: `ALLOWED_ORIGINS` (env var, coma-separado) se suma a los orígenes
  locales por defecto, en vez de una lista hardcodeada.
- `backend/Procfile`: comando de arranque para Railway.
- Frontend: `API_BASE_URL` ahora lee `VITE_API_BASE_URL` (con fallback a
  localhost), `AccessGate.tsx` pide el código una vez y lo guarda en
  `localStorage` (se saltea solo en dev local, detectado por la URL del
  backend), el link de descarga del PDF manda el `key` como query param
  porque es un `<a href>` sin headers custom. `frontend/vercel.json` con
  el rewrite de SPA para que las rutas de React Router no den 404 en
  Vercel.
- Verificado: 77/77 tests con el gate desactivado (sin `DEMO_ACCESS_KEY`
  en el entorno de test), typecheck del frontend limpio, dev local sigue
  sin pedir el código de acceso, y el gate real probado con un backend
  temporal (`DEMO_ACCESS_KEY=test-secret-123`) confirmando 401/200 en
  ambos casos.

**Checklist pendiente para el usuario** (no lo puedo hacer yo — requiere
login interactivo por navegador, mismo motivo que el `git push`):
1. **Railway** → New Project → Deploy from GitHub repo → `alphatense-fpanda`,
   Root Directory = `backend`. Variables de entorno: `DEMO_ACCESS_KEY`
   (inventar una), `ALLOWED_ORIGINS` (la URL de Vercel, una vez que
   exista), `ANTHROPIC_API_KEY` (opcional).
2. **Vercel** → New Project → mismo repo, Root Directory = `frontend`,
   preset Vite (auto-detectado). Variable de entorno: `VITE_API_BASE_URL`
   = la URL que dio Railway.
3. Redeploy en Vercel después de setear `VITE_API_BASE_URL` (el build la
   necesita presente al compilar, no solo en runtime).

### PDF ejecutivo enriquecido con aging y cash flow
El PDF (`app/reporting/pdf_report.py`) ahora suma dos secciones opcionales,
reutilizando los mismos resultados que ya calculan aging.py y cash_flow.py
— nada de lógica nueva, solo layout:

- Sección "Aging AR/AP" (una tabla de buckets por tipo AR/AP + narrativa).
- Sección "Cash Flow Proyectado" (tabla semana a semana + narrativa).

`GET /report/pdf` suma parámetros opcionales `as_of` (activa aging, y si
además viene `starting_balance`, activa cash flow) y `weeks_ahead`. Sin
esos parámetros, el PDF sale idéntico a como estaba antes — son aditivos,
no rompen el comportamiento existente. Probado generando un PDF real
contra el servidor con `sample_invoices.csv` y extrayendo el texto con
`pypdf` para confirmar que los números calzan; el símbolo `£` se ve mal en
esa extracción de texto (`�`) pero es un artefacto conocido de
`reportlab`+`pypdf` al extraer, no un defecto del PDF real — reproducido
en un PDF mínimo aislado para confirmar que no es algo introducido hoy.

### Frontend: aging, cash flow, facturas y chat
Con todo lo demás bloqueado esperando al usuario (API key, signups), se
decidió dejar de posponer la parte de "exponer funcionalidad ya construida
en el backend" (distinto de "pulido visual", que sigue pospuesto). El
frontend ahora cubre los 5 endpoints de negocio, no solo 2:

- `components/InvoiceUpload.tsx`: sube facturas AR/AP a un workspace ya
  creado, incrustado en `PortfolioPage`.
- `components/AgingSection.tsx`: formulario de fecha de corte → tablas de
  buckets AR/AP + narrativa, en `ClientDetailPage`.
- `components/CashFlowChart.tsx`: formulario de fecha + balance inicial →
  gráfico de línea del balance proyectado (recharts, mismo patrón que
  `ForecastChart`) + narrativa, en `ClientDetailPage`.
- `pages/ChatPage.tsx` (ruta `/portfolio/:workspaceId/chat`): UI de chat
  con el agente conversacional, `history` opaco reenviado en cada turno.
  Maneja el 503 ("no configurado") de forma prolija en vez de un error
  genérico — es el único camino de este feature que se puede probar hoy,
  ya que la respuesta real del agente sigue bloqueada por la API key.

Probado end-to-end contra el servidor real (no solo typecheck): aging y
cash flow devuelven exactamente los mismos números ya verificados antes
por curl; el chat muestra el mensaje del usuario y el aviso de "no
configurado" correctamente ante el 503 real.

### Conector Xero (simulado)
Con todo lo demás bloqueado esperando al usuario, esta era la única pieza
grande del backlog avanzable sin depender de él. Investigué la forma real
de la API de Xero (`developer.xero.com`) antes de simular nada:

- `Invoices`: `Type` (`ACCREC`=AR/`ACCPAY`=AP), `Contact.Name`,
  `DateString`/`DueDateString`, `Total`/`AmountPaid` — mapea directo a
  nuestro `Invoice`.
- Para el P&L, descarté el reporte `Reports/ProfitAndLoss` (estructura
  Header/Section/Row/Cell muy anidada) a favor de `Journals` (líneas
  planas) + `Accounts` (para clasificar cada cuenta) — mucho más simple de
  mapear a nuestro esquema (account, category, amount).
- Mapeo de `AccountType` de Xero a nuestro `AccountCategory` documentado
  explícitamente en `mapper.py`, incluyendo el heurístico por nombre para
  `tax` (Xero no tiene un tipo de cuenta limpio para eso).

`backend/app/integrations/xero/`: `client.py` (`XeroClient` Protocol +
`FakeXeroClient` con fixtures realistas de un tenant demo),  `mapper.py`
(transforms puros), `sync.py` (orquestación). Nuevo
`Workspace.add_statements()` (mismo patrón que `add_invoices()`) para que
un cliente sincronizado de Xero se sume a un workspace que ya tiene datos
de CSV. Endpoint `POST /workspaces/{id}/xero/sync`.

Cuando lleguen las credenciales OAuth reales, un `RealXeroClient` que
implemente el mismo Protocol reemplaza a `FakeXeroClient` sin tocar
`mapper.py`, `sync.py` ni la ruta de la API. Sin wiring en el frontend
todavía (no tiene sentido un botón "Conectar Xero" sin OAuth real detrás).

Verificado contra el servidor real: el cliente sincronizado desde el
tenant demo aparece en `/portfolio` con KPIs exactos (revenue 62,000, tax
3,100 correctamente clasificado por nombre en vez de caer en opex, net
income 15,380), y sus facturas quedan disponibles para aging (buckets
verificados a mano contra las fechas de la fixture).

### RealXeroClient — OAuth2 real, verificado en vivo (2026-07-18)
Con `XERO_CLIENT_ID`/`XERO_CLIENT_SECRET` ya obtenidos, se construyó el flujo
OAuth2 completo y un `RealXeroClient` que implementa el mismo `XeroClient`
Protocol que `FakeXeroClient` — cero cambios en la ruta de la API por el
swap:

- `backend/app/integrations/xero/oauth.py` (nuevo): `build_authorize_url()` /
  `exchange_code_for_tokens()` / `refresh_access_token()` /
  `get_valid_access_token()`, tokens en memoria (`_TOKENS`, mismo patrón que
  `_WORKSPACES`), refresh automático 60s antes de expirar.
- `GET /xero/connect` y `GET /xero/callback` (este último exceptuado del
  gate de acceso — Xero no puede mandar nuestro header/query param custom).
- `RealXeroClient` en `client.py`: pide un token fresco por llamada, headers
  `Authorization: Bearer` + `Xero-tenant-id`.
- Verificado en vivo contra la organización trial real "Alphatense FP&A" en
  el navegador: login → consentimiento OAuth → callback → `Invoices`,
  `Accounts` y `Contacts` devuelven 200 con datos reales.

**Hallazgo confirmado (no una suposición)**: `GET /Journals` devuelve 401
`AuthorizationUnsuccessful` bajo el modelo de scopes granulares de Xero
(apps registradas después de 2026-03-02) — no existe ningún scope granular
que lo habilite. `accounting.manualjournals.read` es una función distinta
(asientos manuales), confirmado que tampoco lo desbloquea. Se reemplazó la
construcción del P&L: `mapper.map_journal_lines` (JournalLines planas) →
`mapper.map_profit_and_loss` (árbol `Reports/ProfitAndLoss`
Header/Section/Row/SummaryRow, investigado contra docs/ejemplos de Xero ya
que la org trial no tiene transacciones reales para observar la forma
poblada). El filtro de filas reales usa la presencia de un atributo
`Id: "account"` en la celda — así se descartan SummaryRows y las filas
calculadas de Gross/Net Profit sin necesidad de hardcodear títulos de
sección (varían por org/locale). `_SCOPES` en `oauth.py` perdió
`accounting.manualjournals.read` (confirmado inútil).

Verificado en vivo end-to-end tras el fix: reconexión OAuth (un scope menos,
mismo consentimiento) + `POST /workspaces/{id}/xero/sync` contra el tenant
real devuelve `201` (antes: `500` por el 401 de Journals). `line_items_loaded`
e `invoices_loaded` salen en `0` porque la org trial no tiene transacciones
cargadas todavía — eso es esperado, no un bug: prueba que el pipeline es
correcto estructuralmente (OAuth real, llamada real a Reports API, parseo
real), no que los números calcen contra datos conocidos, porque no hay datos
reales en esta org para comparar. 132/132 tests backend pasando.

### Conector QuickBooks (simulado)
Misma lógica que el conector Xero: la otra pieza grande del backlog
avanzable sin depender del usuario. Investigué la forma real de la API de
QuickBooks Online antes de simular nada, y encontré diferencias reales
frente a Xero que había que respetar en el mapeo:

- QuickBooks separa AR y AP en **dos entidades distintas** (`Invoice` y
  `Bill`), a diferencia de Xero que usa un solo `Invoice` con `Type`.
  `CustomerRef`/`VendorRef` son objetos `{value, name}`.
- **Diferencia clave con Xero**: el campo `Balance` de QuickBooks es el
  **saldo pendiente**, no lo pagado (al revés que el `AmountPaid` de
  Xero). `amount_paid` se calcula como `TotalAmt - Balance`, documentado
  explícitamente en el mapper porque es el punto más fácil de romper.
- Fechas (`TxnDate`/`DueDate`) vienen como `"YYYY-MM-DD"` plano, sin el
  sufijo de hora que tiene Xero.
- Para el P&L, mismo criterio que Xero: se descartó el reporte anidado
  `reports/ProfitAndLoss` a favor de `JournalEntry` (líneas planas,
  `JournalEntryLineDetail.AccountRef` + `Amount`) + `Account` (chart of
  accounts, campo `AccountType`) para clasificar. `AccountType` usa
  strings distintos a Xero (`Income`, `Cost of Goods Sold`, `Expense`,
  `Other Income`, `Other Expense`), con el mismo heurístico por nombre
  para `tax` que ya usa el mapper de Xero.

`backend/app/integrations/quickbooks/`: `client.py` (`QuickBooksClient`
Protocol + `FakeQuickBooksClient` con fixtures de un realm demo — 2
invoices, 1 bill, un journal entry de 6 líneas), `mapper.py`
(`map_invoices_and_bills()`, `map_journal_entries()`, transforms puros),
`sync.py` (`sync_client_from_quickbooks()`, misma orquestación que
`xero/sync.py`). Endpoint `POST /workspaces/{id}/quickbooks/sync`, mismo
shape que el de Xero, reutilizando `Workspace.add_statements()` /
`add_invoices()` sin tocar `Workspace`.

Cuando lleguen las credenciales OAuth reales, un `RealQuickBooksClient`
que implemente el mismo Protocol reemplaza a `FakeQuickBooksClient` sin
tocar `mapper.py`, `sync.py` ni la ruta de la API. Sin wiring en el
frontend todavía, mismo motivo que Xero.

11 tests nuevos, con foco específico en la conversión `Balance` →
`amount_paid` (`test_quickbooks_mapper.py`,
`test_quickbooks_sync.py`, casos en `test_api.py`). Verificado contra el
servidor real: el cliente sincronizado desde el realm demo aparece en
`/portfolio` con los mismos KPIs que la fixture de Xero (revenue 62,000,
opex 22,700, tax 3,100 correctamente clasificado, net income 15,380 —
mismos números por diseño, misma fixture base), y en `/aging` el saldo
pendiente de la factura parcialmente pagada (Cool Cars Ltd: `TotalAmt`
3,400, `Balance` 1,000) aparece correctamente como 1,000 de saldo abierto
(no 2,400), confirmando que la conversión no quedó invertida.

### Estado final de la suite de tests
**132/132 tests backend pasando** (`cd backend && pytest -v`, actualizado
2026-07-18 tras el fix de Xero) + typecheck del frontend limpio
(`npx tsc -b`).

### Git
Todo el trabajo de esta sesión vive en `main` en commits separados por
feature. El usuario sigue teniendo pendiente el primer `git push` manual
(requiere login interactivo por navegador con GitHub que no se puede
completar desde este entorno) — después de eso el push queda desbloqueado
para el resto de la sesión.

## Actualización 2026-07-19 a 2026-07-23: deploy en vivo, cuentas reales,
## rediseño completo y trial gate

Todo lo que sigue está en `main`, deployado y verificado en vivo en
`alphatense.com` (Vercel + Railway), no solo probado localmente. Resumen
denso porque abarca varias sesiones — el detalle línea a línea de cada
feature vive en los mensajes de commit (`git log --oneline`), no repetido
acá:

- **2026-07-19**: deploy real (Vercel + Railway), dominio propio
  `alphatense.com` conectado vía Cloudflare, `RealXeroClient` con OAuth2
  verificado en vivo contra la org trial de Xero, rebrand con el logo real.
- **2026-07-20**: login real por asesoría (antes era una sola
  `DEMO_ACCESS_KEY` compartida) + persistencia en SQLite sobre un volumen
  persistente de Railway (antes los workspaces vivían en un dict en
  memoria y se perdían en cada restart — bug de pérdida de datos cerrado y
  verificado con un restart real de producción), landing page de marketing
  (antes la app caía directo al formulario de upload), traducción completa
  de la UI a inglés (mercado objetivo es UK/US, se había construido todo
  en español por default).
- **2026-07-21**: dashboard autenticado `/home` (antes login llevaba
  directo a un upload en blanco), fix de UX del botón de upload (drag-and-
  drop con confirmación visual de archivo seleccionado), secciones de
  confianza/cómo-funciona/CTA de demo en la landing.
- **2026-07-22**: rediseño completo de la landing pública ("enterprise
  financial-SaaS feel"), reestructuración de portfolio/cliente (agrupado
  por cliente, hub con tabs en vez de una tabla plana), PDF ejecutivo con
  branding + gráficos reales + EBITDA bridge + tendencia de 12 meses +
  working capital + narrativa ejecutiva generada por IA (antes era texto
  plano sin charts), export a Excel multi-hoja para Power BI, pulido de
  logo/badges, **gate de trial de 15 días + captura de leads** (nombre,
  email, teléfono al signup, con pantalla de "trial expirado" que deriva a
  contacto por email).
- **2026-07-23**: página de admin (`/admin/leads`, ver
  `frontend/src/pages/AdminLeadsPage.tsx`) para ver los leads capturados
  sin tener que pegar la URL del endpoint JSON a mano.

**195/195 tests backend pasando**, typecheck/lint de frontend limpio.

## Qué falta (backlog, en el orden que fuimos priorizando)

1. **Validar con asesorías reales (5-10 en UK)** — paso de negocio, no de
   código; es el ítem que más importa ahora que todo lo demás está
   deployado y accesible por URL. Ver `Marketing/` (fuera de este repo)
   para el plan de outreach.
2. **Conector QuickBooks** — el mapeo de datos ya está construido y
   probado contra un adaptador simulado (`FakeQuickBooksClient`), mismo
   estado que tenía Xero antes de conectarse de verdad. Solo falta el
   `RealQuickBooksClient` con el OAuth real, bloqueado por que el usuario
   registre una app de developer en Intuit.
3. **Confirmar `ADMIN_SECRET` seteado en Railway** — la página de admin de
   leads (arriba) solo funciona si esa env var existe en producción; si no
   está seteada, el endpoint devuelve 404 siempre.
4. **Conector Xero** — completo y verificado en vivo (ver detalle arriba,
   sección 2026-07-18/19). Pendiente real, no de código: la org trial
   conectada no tiene transacciones cargadas, así que la correctitud
   numérica del P&L real queda sin verificar hasta que haya un cliente
   real con datos.
5. ~~Pulido visual del frontend~~ — **hecho** (ver actualización
   2026-07-19 a 2026-07-23 arriba). Ya no es un ítem pendiente.

## Cómo correr todo hoy

```bash
cd backend && uvicorn app.api.main:app --reload   # puerto 8000
cd frontend && npm run dev                         # puerto 5173
```

Nota: en esta máquina Windows, `uvicorn --reload` no siempre recargó limpio
tras editar `app/api/main.py` — si los cambios de backend no se reflejan al
probar, reiniciar el proceso manualmente resolvió el problema.
