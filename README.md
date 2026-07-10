# Finance Alphatense AI

Copiloto de IA para asesorías financieras (UK & US): un analista financiero
senior disponible 24/7, encima del ERP de cada cliente.

Este repositorio contiene el **motor FP&A** (Fase 1 del plan de producto):
ingesta de Excel/CSV, cálculo de KPIs y variance analysis con narrativa en
lenguaje natural, sobre una arquitectura multi-cliente nativa (una asesoría
gestiona decenas de clientes desde un panel único).

## Estado actual

**Fase 1 -- MVP (completo)**
- [x] Ingesta y validación de Excel/CSV multi-cliente
- [x] Motor de cálculo de KPIs (revenue, gross margin, EBITDA, net income)
- [x] Variance analysis (actual vs budget, actual vs periodo anterior) con
      narrativa automática y detección de la cuenta que más contribuyó al
      desvío
- [x] Orquestador multi-cliente (`Workspace`) que procesa un archivo con
      varios clientes/periodos en una sola llamada

**Fase 2 -- en progreso**
- [x] Forecast AI con escenarios (best/base/worst) a partir del historial
      de actuals de cada cliente, con narrativa de las tasas de crecimiento
      asumidas
- [x] API HTTP (FastAPI) que expone todo el motor (ingesta, KPIs, variance,
      forecast) por HTTP, lista para que la consuma un frontend
- [ ] Conector QuickBooks (requiere credenciales OAuth reales -- pendiente
      de decidir si se construye como adaptador simulado mientras tanto)
- [ ] Agentes especializados adicionales (cash flow, aging AR/AP)
- [ ] Conector Xero (Fase 1, aún no construido)
- [ ] Generación del informe ejecutivo en PDF con un clic
- [ ] Frontend

## Estructura

```
backend/
  app/
    models/domain.py     # Advisor, Client, LineItem, FinancialStatement, KPISet, VarianceResult
    ingestion/parser.py  # Excel/CSV -> FinancialStatement (validación de esquema)
    engine/kpis.py        # FinancialStatement -> KPISet
    engine/variance.py    # KPISet actual vs budget/prior -> VarianceResult (+ narrativa)
    engine/forecast.py    # historial de actuals -> ForecastResult (best/base/worst)
    engine/workspace.py   # Orquestador multi-cliente: un archivo -> reportes + forecasts de todo el portfolio
    api/main.py           # FastAPI: expone el motor completo por HTTP
  sample_data/sample_financials.csv  # 2 clientes de ejemplo, 3 escenarios cada uno
  tests/                # pytest, cobertura de ingesta, KPIs, variance, workspace y API
  run_demo.py           # demo end-to-end por consola
```

## Cómo correrlo

```bash
cd backend
pip install -r requirements.txt

# correr los tests (incluye los de la API)
pytest -v

# ver el motor en acción con los datos de ejemplo
python run_demo.py

# levantar la API HTTP en http://127.0.0.1:8000
uvicorn app.api.main:app --reload
```

## Esquema de datos esperado (Excel/CSV)

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
auditar. Una mejora de redacción de la narrativa vía LLM se puede agregar
después envolviendo la salida de este módulo, sin tocar cómo se lo llama.

```bash
python run_demo.py   # ahora también imprime el forecast a 3 periodos por cliente
```

`Workspace.build_forecast(client_id, periods_ahead=3)` y
`Workspace.build_portfolio_forecast(periods_ahead=3)` exponen esto a nivel
de un cliente o de todo el portfolio, respectivamente. Requiere al menos 2
periodos de actuals cargados para ese cliente.

## API HTTP (Fase 2)

`app/api/main.py` expone el motor completo (ingesta, KPIs, variance,
forecast) por HTTP con FastAPI, para que un frontend (o cualquier cliente
HTTP) pueda usarlo sin importar el paquete Python directamente.

No hay base de datos todavía: cada archivo subido se procesa en memoria y
queda guardado bajo un `workspace_id` (UUID) generado en el momento, válido
mientras el proceso siga corriendo. Es la primera pieza de infraestructura
de la Fase 2 -- una capa de persistencia real puede reemplazar el
diccionario en memoria más adelante sin cambiar ninguna ruta.

| método | ruta | qué hace |
|--------|------|----------|
| GET  | `/health` | chequeo de salud |
| POST | `/workspaces` | sube un CSV/Excel (`multipart/form-data`, campo `file`) y crea un workspace |
| GET  | `/workspaces/{workspace_id}/clients` | lista los `client_id` encontrados en el archivo |
| GET  | `/workspaces/{workspace_id}/portfolio` | KPIs + variance analysis de todos los clientes/periodos |
| GET  | `/workspaces/{workspace_id}/clients/{client_id}/report?period=2026-06` | reporte de un cliente/periodo puntual |
| GET  | `/workspaces/{workspace_id}/clients/{client_id}/forecast?periods_ahead=3` | forecast best/base/worst de un cliente |
| GET  | `/workspaces/{workspace_id}/portfolio/forecast?periods_ahead=3` | forecast de todos los clientes con suficiente historial |

Ejemplo rápido con `curl`:

```bash
uvicorn app.api.main:app --reload &

WS=$(curl -s -X POST http://127.0.0.1:8000/workspaces \
  -F "file=@sample_data/sample_financials.csv" | python -c "import sys,json;print(json.load(sys.stdin)['workspace_id'])")

curl -s "http://127.0.0.1:8000/workspaces/$WS/portfolio" | python -m json.tool
```

Con el servidor corriendo, la documentación interactiva (Swagger) queda
disponible en `http://127.0.0.1:8000/docs`.

## Próximos pasos (según el plan de producto)

1. Validar tarifas y dolor real con 5-10 asesorías UK antes de seguir
   construyendo
2. Conector Xero + agente FP&A conversacional (Fase 1, pendiente)
3. Conector QuickBooks + más agentes especializados (resto de Fase 2)
4. Generación del PDF ejecutivo con un clic
5. Frontend (ya puede empezar a consumir la API)
