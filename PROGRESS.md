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

### Estado final de la suite de tests
**44/44 tests pasando** (`cd backend && pytest -v`).

## Qué falta (backlog, en el orden que fuimos priorizando)

1. **Validar con asesorías reales (5-10 en UK)** — paso de negocio, no de
   código. El frontend actual ya alcanza para hacer estas demos.
2. **Conector Xero** — bloqueado: requiere que el usuario consiga una
   cuenta de developer y registre una app en Xero (credenciales OAuth).
   Alternativa evaluada y no descartada: construirlo primero contra un
   adaptador simulado para no bloquear el avance de código.
3. **Conector QuickBooks** — mismo bloqueo de credenciales OAuth.
4. **Agentes especializados** (cash flow, aging AR/AP) — requieren modelar
   datos que el esquema actual (líneas agregadas por cuenta/periodo/
   escenario) no soporta todavía (facturas individuales con fechas de
   vencimiento, timing de cobros/pagos). Más trabajo de diseño de datos
   antes de poder codear.
5. **Pulido del frontend** (diseño, responsive, loading states, etc.) —
   deliberadamente pospuesto hasta el final del proyecto.

## Cómo correr todo hoy

```bash
cd backend && uvicorn app.api.main:app --reload   # puerto 8000
cd frontend && npm run dev                         # puerto 5173
```

Nota: en esta máquina Windows, `uvicorn --reload` no siempre recargó limpio
tras editar `app/api/main.py` — si los cambios de backend no se reflejan al
probar, reiniciar el proceso manualmente resolvió el problema.
