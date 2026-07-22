import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, signup } from '../api/client'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { TextInput } from '../components/ui/TextInput'

export function SignupPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await signup(name, email, password, phone)
      navigate('/home')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create the account.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col items-center justify-center gap-4 px-4">
      <img src="/logo-mark-192.png" alt="Alphatense" className="h-16 w-16" />
      <h1 translate="no" className="notranslate text-lg font-semibold text-slate-900 dark:text-slate-50">
        Create account
      </h1>
      <p className="text-center text-sm text-slate-500 dark:text-slate-400">
        One account per advisory firm — you&apos;ll only see your own client portfolio.
      </p>
      <Card className="w-full p-6">
        <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
          <TextInput
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Advisory firm name"
            required
            autoFocus
          />
          <TextInput
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
          />
          <TextInput
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password (minimum 8 characters)"
            minLength={8}
            required
          />
          <TextInput
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Mobile phone (e.g. +44 7700 900000)"
            required
          />
          <Button type="submit" disabled={loading} className="mt-1">
            {loading ? 'Creating account…' : 'Sign up'}
          </Button>
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        </form>
      </Card>
      <p className="text-center text-xs text-slate-400">
        Starts a 15-day free trial — no credit card required.
      </p>
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Already have an account?{' '}
        <Link to="/login" className="text-brand-600 hover:underline dark:text-brand-400">
          Log in
        </Link>
      </p>
    </div>
  )
}
