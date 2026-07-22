import type {
  AgingReport,
  CashFlowForecast,
  ClientReport,
  CreateWorkspaceResponse,
  ForecastResult,
  InvoiceType,
  PortfolioForecast,
} from '../types'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

const TOKEN_STORAGE = 'alphatense_token'

export interface Advisor {
  advisor_id: string
  name: string
  email: string
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_STORAGE)
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const headers = new Headers(init?.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  if (!res.ok) {
    if (res.status === 401) clearToken()
    const body = await res.json().catch(() => null)
    const message = body?.detail ?? `Request failed with status ${res.status}`
    throw new ApiError(res.status, message)
  }
  return res.json() as Promise<T>
}

export async function signup(name: string, email: string, password: string, phone: string): Promise<Advisor> {
  const result = await request<{ token: string; advisor: Advisor }>('/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password, phone }),
  })
  setToken(result.token)
  return result.advisor
}

export async function login(email: string, password: string): Promise<Advisor> {
  const result = await request<{ token: string; advisor: Advisor }>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  setToken(result.token)
  return result.advisor
}

export async function logout(): Promise<void> {
  try {
    await request('/auth/logout', { method: 'POST' })
  } finally {
    clearToken()
  }
}

export function getMe(): Promise<{ advisor: Advisor; workspace_ids: string[] }> {
  return request('/auth/me')
}

export function createWorkspace(file: File): Promise<CreateWorkspaceResponse> {
  const formData = new FormData()
  formData.append('file', file)
  return request<CreateWorkspaceResponse>('/workspaces', {
    method: 'POST',
    body: formData,
  })
}

export function listClients(workspaceId: string): Promise<{ client_ids: string[] }> {
  return request(`/workspaces/${workspaceId}/clients`)
}

export function getPortfolioReport(workspaceId: string): Promise<ClientReport[]> {
  return request(`/workspaces/${workspaceId}/portfolio`)
}

export function getClientReport(
  workspaceId: string,
  clientId: string,
  period: string,
): Promise<ClientReport> {
  const params = new URLSearchParams({ period })
  return request(`/workspaces/${workspaceId}/clients/${clientId}/report?${params}`)
}

export function getClientForecast(
  workspaceId: string,
  clientId: string,
  periodsAhead = 3,
): Promise<ForecastResult[]> {
  const params = new URLSearchParams({ periods_ahead: String(periodsAhead) })
  return request(`/workspaces/${workspaceId}/clients/${clientId}/forecast?${params}`)
}

export function getPortfolioForecast(
  workspaceId: string,
  periodsAhead = 3,
): Promise<PortfolioForecast> {
  const params = new URLSearchParams({ periods_ahead: String(periodsAhead) })
  return request(`/workspaces/${workspaceId}/portfolio/forecast?${params}`)
}

export function uploadInvoices(workspaceId: string, file: File): Promise<{ invoices_loaded: number }> {
  const formData = new FormData()
  formData.append('file', file)
  return request(`/workspaces/${workspaceId}/invoices`, {
    method: 'POST',
    body: formData,
  })
}

export function getClientAging(
  workspaceId: string,
  clientId: string,
  type: InvoiceType,
  asOf: string,
): Promise<AgingReport> {
  const params = new URLSearchParams({ type, as_of: asOf })
  return request(`/workspaces/${workspaceId}/clients/${clientId}/aging?${params}`)
}

export function getClientCashFlow(
  workspaceId: string,
  clientId: string,
  startingBalance: number,
  asOf: string,
  weeksAhead = 13,
): Promise<CashFlowForecast> {
  const params = new URLSearchParams({
    starting_balance: String(startingBalance),
    as_of: asOf,
    weeks_ahead: String(weeksAhead),
  })
  return request(`/workspaces/${workspaceId}/clients/${clientId}/cash-flow?${params}`)
}

export function chat(
  workspaceId: string,
  message: string,
  history: unknown[],
): Promise<{ reply: string; history: unknown[] }> {
  return request(`/workspaces/${workspaceId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  })
}
