import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ApiError, getLeads, type Lead } from '../api/client'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { PageHeading } from '../components/ui/PageHeading'
import { TextInput } from '../components/ui/TextInput'
import { tableShell, tableHead, tableHeadCell, tableBody, tableCell, tableCellStrong } from '../components/ui/table'

function trialStatus(trialExpiresAt: string | null): string {
  if (!trialExpiresAt) return '—'
  const daysLeft = Math.ceil((new Date(trialExpiresAt).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
  return daysLeft >= 0 ? `Active (${daysLeft}d left)` : 'Expired'
}

export function AdminLeadsPage() {
  const [searchParams] = useSearchParams()
  const [secretInput, setSecretInput] = useState(searchParams.get('secret') ?? '')
  const [leads, setLeads] = useState<Lead[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  function load(secret: string) {
    if (!secret) return
    setLoading(true)
    setError(null)
    getLeads(secret)
      .then(setLeads)
      .catch((err) => setError(err instanceof ApiError ? 'Invalid secret or not found.' : 'Could not load leads.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    const secret = searchParams.get('secret')
    if (secret) load(secret)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <PageHeading title="Leads" subtitle="Signups captured from the trial gate." />

      <Card className="mt-4 p-4">
        <form
          className="flex items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            load(secretInput)
          }}
        >
          <div className="flex-1">
            <label htmlFor="admin-secret" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Admin secret
            </label>
            <TextInput
              id="admin-secret"
              type="password"
              value={secretInput}
              onChange={(e) => setSecretInput(e.target.value)}
              className="w-full"
              placeholder="ADMIN_SECRET"
            />
          </div>
          <Button type="submit" disabled={!secretInput || loading}>
            {loading ? 'Loading…' : 'Load leads'}
          </Button>
        </form>
      </Card>

      {error && <p className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}

      {leads && (
        <div className="mt-6">
          {leads.length === 0 ? (
            <p className="text-sm text-slate-400">No leads yet.</p>
          ) : (
            <div className={tableShell}>
              <table className="w-full text-left text-sm">
                <thead className={tableHead}>
                  <tr>
                    <th className={tableHeadCell}>Name</th>
                    <th className={tableHeadCell}>Email</th>
                    <th className={tableHeadCell}>Phone</th>
                    <th className={tableHeadCell}>Signed up</th>
                    <th className={tableHeadCell}>Trial status</th>
                  </tr>
                </thead>
                <tbody className={tableBody}>
                  {leads.map((lead) => (
                    <tr key={lead.email}>
                      <td className={tableCellStrong}>{lead.name}</td>
                      <td className={tableCell}>{lead.email}</td>
                      <td className={tableCell}>{lead.phone ?? '—'}</td>
                      <td className={tableCell}>{new Date(lead.created_at).toLocaleDateString()}</td>
                      <td className={tableCell}>{trialStatus(lead.trial_expires_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
