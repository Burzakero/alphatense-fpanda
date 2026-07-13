export type Scenario = 'actual' | 'budget' | 'prior'
export type Severity = 'low' | 'medium' | 'high'
export type ForecastScenario = 'best' | 'base' | 'worst'

export interface KPISet {
  client_id: string
  period: string
  scenario: Scenario

  revenue: number
  cogs: number
  gross_profit: number
  gross_margin_pct: number | null

  opex: number
  ebitda: number
  ebitda_margin_pct: number | null

  other_income: number
  other_expense: number
  tax: number
  net_income: number
  net_margin_pct: number | null
}

export interface VarianceResult {
  client_id: string
  period: string
  kpi_name: string
  comparison_scenario: Scenario

  actual_value: number
  comparison_value: number
  delta: number
  delta_pct: number | null
  severity: Severity
  narrative: string
}

export interface ForecastResult {
  client_id: string
  period: string
  scenario: ForecastScenario

  revenue: number
  cogs: number
  gross_profit: number
  gross_margin_pct: number | null

  opex: number
  ebitda: number
  ebitda_margin_pct: number | null

  other_income: number
  other_expense: number
  tax: number
  net_income: number
  net_margin_pct: number | null

  assumptions: string
}

export interface ClientReport {
  client_id: string
  period: string
  actual_kpis: KPISet
  variances_vs_budget: VarianceResult[]
  variances_vs_prior: VarianceResult[]
}

export interface CreateWorkspaceResponse {
  workspace_id: string
  client_ids: string[]
}

export interface PortfolioForecast {
  [clientId: string]: ForecastResult[]
}

export type InvoiceType = 'ar' | 'ap'
export type AgingBucket = 'current' | '1-30' | '31-60' | '61-90' | '90+'

export interface AgingBucketAmount {
  bucket: AgingBucket
  amount: number
  invoice_count: number
}

export interface AgingReport {
  client_id: string
  type: InvoiceType
  as_of: string
  total_outstanding: number
  buckets: AgingBucketAmount[]
  narrative: string
}

export interface CashFlowWeek {
  week_start: string
  week_end: string
  ar_inflows: number
  ap_outflows: number
  net_change: number
  ending_balance: number
}

export interface CashFlowForecast {
  client_id: string
  as_of: string
  starting_balance: number
  weeks: CashFlowWeek[]
  narrative: string
}
