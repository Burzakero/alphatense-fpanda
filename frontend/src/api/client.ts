import type {
  ClientReport,
  CreateWorkspaceResponse,
  ForecastResult,
  PortfolioForecast,
} from '../types'

export const API_BASE_URL = 'http://127.0.0.1:8000'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, init)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const message = body?.detail ?? `Request failed with status ${res.status}`
    throw new ApiError(res.status, message)
  }
  return res.json() as Promise<T>
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
