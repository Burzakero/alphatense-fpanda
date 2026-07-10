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

### Estado final de la suite de tests
**66/66 tests pasando** (`cd backend && pytest -v`).

### Git
Todo el trabajo de esta sesión (frontend, PDF ejecutivo, aging AR/AP)
quedó commiteado en `main` en commits separados por feature. Pendiente:
el usuario hace el primer `git push` manualmente (requiere login
interactivo por navegador con GitHub que no se puede completar desde este
entorno) — después de eso el push queda desbloqueado para el resto de la
sesión.

## Qué falta (backlog, en el orden que fuimos priorizando)

1. **Validar con asesorías reales (5-10 en UK)** — paso de negocio, no de
   código. El frontend actual ya alcanza para hacer estas demos.
2. **Conector Xero** — bloqueado: requiere que el usuario consiga una
   cuenta de developer y registre una app en Xero (credenciales OAuth).
   Alternativa evaluada y no descartada: construirlo primero contra un
   adaptador simulado para no bloquear el avance de código.
3. **Conector QuickBooks** — mismo bloqueo de credenciales OAuth.
4. **Agente de cash flow** — requiere modelar timing proyectado de
   cobros/pagos (no solo montos con fecha de vencimiento, que es lo que ya
   cubre aging). Más trabajo de diseño de datos antes de poder codear.
5. **Pulido del frontend** (diseño, responsive, loading states, etc.,
   incluyendo exponer aging en la UI) — deliberadamente pospuesto hasta el
   final del proyecto.

## Cómo correr todo hoy

```bash
cd backend && uvicorn app.api.main:app --reload   # puerto 8000
cd frontend && npm run dev                         # puerto 5173
```

Nota: en esta máquina Windows, `uvicorn --reload` no siempre recargó limpio
tras editar `app/api/main.py` — si los cambios de backend no se reflejan al
probar, reiniciar el proceso manualmente resolvió el problema.
