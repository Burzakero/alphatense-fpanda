import { Cable, Lock, ShieldCheck } from 'lucide-react'
import { Header } from '../components/landing/Header'
import { Hero } from '../components/landing/Hero'
import { TrustBar } from '../components/landing/TrustBar'
import { FeaturesGrid } from '../components/landing/FeaturesGrid'
import { HowItWorks } from '../components/landing/HowItWorks'
import { UseCases } from '../components/landing/UseCases'
import { CTASection } from '../components/landing/CTASection'
import { Footer } from '../components/landing/Footer'

const TRUST_POINTS = [
  {
    icon: Lock,
    text: 'Bank-level encryption for data in transit and at rest',
  },
  {
    icon: ShieldCheck,
    text: "Each firm's client data is fully isolated — never shared across accounts",
  },
  {
    icon: Cable,
    text: 'Built on the official Xero and QuickBooks APIs',
  },
]

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950">
      <Header />
      <Hero />
      <TrustBar />

      <main>
        <FeaturesGrid />
        <HowItWorks />
        <UseCases />

        <section className="mx-auto max-w-5xl border-y border-slate-200 px-4 py-8 text-center dark:border-slate-800">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            {TRUST_POINTS.map(({ icon: Icon, text }) => (
              <div key={text} className="flex flex-col items-center gap-2 text-center">
                <Icon className="h-5 w-5 text-brand-600 dark:text-brand-400" />
                <p className="text-sm text-slate-600 dark:text-slate-400">{text}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <CTASection />
      <Footer />
    </div>
  )
}
