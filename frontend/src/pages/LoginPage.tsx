import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, login } from '../api/client'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { TextInput } from '../components/ui/TextInput'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      navigate('/home')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not log in.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col items-center justify-center gap-4 px-4">
      <img src="/logo-mark-192.png" alt="Alphatense" className="h-16 w-16" />
      <h1 translate="no" className="notranslate text-lg font-semibold text-slate-900 dark:text-slate-50">
        Log in
      </h1>
      <Card className="w-full p-6">
        <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
          <TextInput
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            autoFocus
            required
          />
          <TextInput
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            required
          />
          <Button type="submit" disabled={loading} className="mt-1">
            {loading ? 'Logging in…' : 'Log in'}
          </Button>
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        </form>
      </Card>
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Don&apos;t have an account yet?{' '}
        <Link to="/signup" className="text-brand-600 hover:underline dark:text-brand-400">
          Sign up
        </Link>
      </p>
    </div>
  )
}
