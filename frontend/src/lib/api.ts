const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? ''
const API_PREFIX = `${API_BASE}/api/v1`
const API_KEY = (import.meta.env.VITE_API_KEY as string | undefined) ?? ''

function authHeaders(init?: HeadersInit): Headers {
  const headers = new Headers(init)
  if (API_KEY) {
    headers.set('X-API-Key', API_KEY)
  }
  return headers
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    headers: authHeaders(),
  })
  if (!response.ok) {
    throw new Error(`Request failed ${path} (${response.status})`)
  }
  return response.json()
}

export type EtfMeta = {
  symbol: string
  bucket: 'conservative' | 'moderate' | 'aggressive'
  max_allocation_pct: number
}

export type PublicConfig = {
  app_name: string
  base_currency: string
  risk_profile: string
  allocation_targets: {
    conservative_pct: number
    moderate_pct: number
    aggressive_pct: number
  }
  available_capital_usd: number
  etf_universe: EtfMeta[]
  notifications: string[]
}

export type Recommendation = {
  id: number
  run_id: number
  symbol: string
  action: string
  size_pct: string | number | null
  size_amount_usd: string | number | null
  confidence: string | number | null
  status: string
  compliance_status: string
  created_at: string
  explanation?: {
    locale: string
    thesis: string
    risks: string
    invalidation?: string | null
    evidence_refs: string[]
  } | null
}

export type MarketOverview = {
  usdcop: { pair: string; ts: string; rate: string | number; source: string } | null
  dxy: { pair: string; ts: string; rate: string | number; source: string } | null
  etf_latest_features: Array<{
    entity: string
    feature_set_version: string
    ts: string
    payload: {
      close?: number
      return_1d?: number | null
      return_20d?: number | null
      volatility_20d_ann?: number | null
    }
  }>
  macro_latest: Array<{ series_id: string; ts: string; value: string | number }>
  warnings: string[]
}

export type AdvisoryRunSummary = {
  run_id: number
  status: string
  recommendations_count: number
  actionable_count: number
  warnings: string[]
  email_status?: string | null
  notification_id?: number | null
}

export type NotificationItem = {
  id: number
  channel: string
  status: string
  subject?: string | null
  body: string
  error_message?: string | null
  created_at: string
  sent_at?: string | null
}

export type Portfolio = {
  id: number
  name: string
  base_currency: string
  cash_usd: string | number
  is_primary: boolean
  holdings: Array<{
    id: number
    symbol: string
    quantity: string | number
    avg_cost_usd: string | number
  }>
}

export const fetchPublicConfig = () => getJson<PublicConfig>('/meta/config')
export const fetchLiveHealth = () => getJson<{ status: string }>('/health/live')
export const fetchRecommendations = (actionableOnly = false) =>
  getJson<Recommendation[]>(
    `/recommendations?limit=50${actionableOnly ? '&actionable_only=true' : ''}`,
  )
export const fetchMarketOverview = () => getJson<MarketOverview>('/market/overview')
export const fetchPortfolio = () => getJson<Portfolio>('/portfolios/primary')
export const fetchNotifications = () => getJson<NotificationItem[]>('/notifications?limit=10')

export async function triggerAdvisoryRun(notifyEmail = true): Promise<AdvisoryRunSummary> {
  const response = await fetch(`${API_PREFIX}/advisory/runs`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ trigger: 'on_demand', notify_email: notifyEmail }),
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Advisory run failed (${response.status})`)
  }
  return response.json()
}
