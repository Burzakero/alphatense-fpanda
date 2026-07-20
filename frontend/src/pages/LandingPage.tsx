import { Link } from 'react-router-dom'
import { BarChart3, Bot, Cable, LineChart, ReceiptText } from 'lucide-react'
import { ButtonLink } from '../components/ui/Button'
import { Card } from '../components/ui/Card'

const FEATURES = [
  {
    icon: BarChart3,
    title: 'KPIs y variance automáticos',
    description: 'Revenue, EBITDA, márgenes y desvíos vs. budget o periodo anterior, por cliente y por período.',
  },
  {
    icon: LineChart,
    title: 'Forecast a 3 escenarios',
    description: 'Proyección best / base / worst para cada cliente, generada a partir de su propio historial.',
  },
  {
    icon: ReceiptText,
    title: 'Aging AR/AP + cash flow',
    description: 'Facturas vencidas por antigüedad y proyección semanal de caja, sin planillas manuales.',
  },
  {
    icon: Cable,
    title: 'Conectado a Xero y QuickBooks',
    description: 'Sincronizá P&L y facturas directo desde el ERP de cada cliente.',
  },
  {
    icon: Bot,
    title: 'Asistente conversacional con IA',
    description: 'Preguntale en lenguaje natural por cualquier cliente de tu cartera y respondé rápido.',
  },
]

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-4 py-6">
        <div className="flex items-center gap-2">
          <img src="/logo-mark-192.png" alt="" className="h-8 w-8" />
          <span translate="no" className="notranslate text-lg font-semibold text-brand-700 dark:text-brand-300">
            Alphatense
          </span>
        </div>
        <div className="flex items-center gap-4">
          <Link
            to="/login"
            className="text-sm font-medium text-slate-600 hover:text-brand-600 dark:text-slate-300 dark:hover:text-brand-400"
          >
            Iniciar sesión
          </Link>
          <ButtonLink href="/signup" size="sm">
            Registrarse
          </ButtonLink>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 pb-24 pt-12 text-center">
        <h1 className="mx-auto max-w-3xl text-4xl font-bold tracking-tight text-slate-900 dark:text-slate-50 sm:text-5xl">
          El copiloto de FP&amp;A para asesorías financieras
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-600 dark:text-slate-400">
          Un analista financiero senior disponible 24/7, encima del ERP de cada cliente — así tu asesoría gestiona
          decenas de clientes desde un panel único, sin planillas armadas a mano.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <ButtonLink href="/signup" size="md">
            Empezar gratis
          </ButtonLink>
          <Link
            to="/login"
            className="inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50 dark:text-brand-300 dark:hover:bg-slate-900"
          >
            Ya tengo cuenta
          </Link>
        </div>

        <div className="mt-20 grid grid-cols-1 gap-4 text-left sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <Card key={title} className="p-5">
              <Icon className="h-6 w-6 text-brand-600 dark:text-brand-400" />
              <h3 className="mt-3 text-sm font-semibold text-slate-900 dark:text-slate-50">{title}</h3>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
            </Card>
          ))}
        </div>
      </main>
    </div>
  )
}
