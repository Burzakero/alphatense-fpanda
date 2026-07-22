import { Link } from 'react-router-dom'
import { Card } from '../components/ui/Card'
import { ButtonLink } from '../components/ui/Button'

const CONTACT_EMAIL = 'juanagustinsinger@gmail.com'

export function TrialExpiredPage() {
  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col items-center justify-center gap-4 px-4 text-center">
      <img src="/logo-mark-192.png" alt="Alphatense" className="h-16 w-16" />
      <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Your trial has ended</h1>
      <Card className="w-full p-6">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Your 15-day free trial of Alphatense has ended. Get in touch and we&apos;ll get you set up to
          keep using your portfolio.
        </p>
        <ButtonLink
          href={`mailto:${CONTACT_EMAIL}?subject=Continue my Alphatense trial`}
          className="mt-4 w-full"
        >
          Contact us
        </ButtonLink>
      </Card>
      <Link to="/login" className="text-sm text-brand-600 hover:underline dark:text-brand-400">
        Back to login
      </Link>
    </div>
  )
}
