const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FundItem {
  schemeCode: string
  schemeName: string
  schemeISIN: string
}

export interface NAVPoint {
  date: string
  nav: number | null
}

export interface CAGRPoint {
  date: string
  years: number
  cagr: number | null
}

export interface CAGRStatPoint {
  years: number
  min: number | null
  p25: number | null
  median: number | null
  mean: number | null
  p75: number | null
  max: number | null
}

export interface SIPRequest {
  scheme_code: string
  start_date: string
  end_date: string
  monthly_amount: number
  step_up_pct: number
}

export interface SIPSeriesPoint {
  date: string
  invested_amount: number | null
  current_value: number | null
  cum_units: number | null
}

export interface SIPResult {
  xirr: number | null
  series: SIPSeriesPoint[]
}

export interface SWPRequest {
  scheme_code: string
  start_date: string
  end_date: string
  initial_investment: number
  monthly_withdrawal: number
}

export interface SWPSeriesPoint {
  date: string
  inv_value: number | null
  cur_value: number | null
  cum_amount: number | null
  total: number | null
}

export interface SWPResult {
  xirr: number | null
  series: SWPSeriesPoint[]
}

export interface STPRequest {
  source_scheme_code: string
  target_scheme_code: string
  start_date: string
  end_date: string
  initial_investment: number
  monthly_transfer: number
}

export interface STPSeriesPoint {
  date: string
  value_src: number | null
  value_tgt: number | null
  total_value: number | null
  src_units_norm: number | null
  tgt_units_norm: number | null
}

export interface STPResult {
  xirr: number | null
  source_final: number | null
  target_final: number | null
  total_final: number | null
  series: STPSeriesPoint[]
}

export interface CompareRequest {
  scheme_codes: string[]
  from_date: string
  // Weights for comparison funds only: scheme_codes[1:].
  combo_weights?: number[]
}

export interface FundSeries {
  name: string
  series: { date: string; rebased_nav: number | null }[]
}

export interface DrawdownPoint {
  date: string
  mf: string
  draw_down: number | null
}

export interface RollingCAGRPoint {
  date: string
  years: number
  mf: string
  cagr: number | null
}

export interface DrawdownRecoveryPoint {
  name: string
  latest_date: string
  latest_nav: number | null
  last_seen_date: string | null
  last_seen_nav: number | null
}

export interface GrowthPoint {
  date: string
  mf: string        // "{fund name}|{N}Y"
  end_value: number | null
}

export interface RollingXIRRPoint {
  start_date: string
  end_date: string
  xirr: number | null
}

export interface CompareResult {
  funds: FundSeries[]
  drawdown: DrawdownPoint[]
  rolling_cagr: RollingCAGRPoint[]
  drawdown_recovery: DrawdownRecoveryPoint[]
  growth_series: GrowthPoint[]
}

export interface RollingXIRRRequest {
  scheme_code: string
  window_years: number
  monthly_amount: number
  step_up_pct: number
}

export interface PastForwardRequest {
  scheme_code: string
  backward_years: number
  forward_years: number
  frequency: 'Daily' | 'Weekly' | 'Monthly'
  non_overlapping: boolean
  hurdle_rate: number
  start_date?: string
  end_date?: string
  target_return?: number
}

export interface PastForwardObservation {
  as_of_date: string
  backward_start_date: string
  forward_end_date: string
  backward_start_nav: number
  as_of_nav: number
  forward_end_nav: number
  trailing_cagr: number
  forward_cagr: number
  data_quality: string
  zone?: 'Low' | 'Middle' | 'High'
}

export interface MatrixData {
  index: string[]
  columns: string[]
  data: Array<Array<string | number>>
}

export interface PastForwardResult {
  observations: PastForwardObservation[]
  summary: Record<string, string | number | null>
  current_trailing: number | null
  target_return: number
  conditional: Record<string, number | null>
  matched_observations: PastForwardObservation[]
  zones: PastForwardObservation[]
  zone_summary: Array<Record<string, string | number | null>>
  narrative: Record<string, string[]>
  matrices: Record<string, MatrixData>
}

// ─── Fetch helpers ────────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: 'no-store' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err as { detail: string }).detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    cache: 'no-store',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err as { detail: string }).detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

// ─── API functions ────────────────────────────────────────────────────────────

export const apiFunds = () => get<FundItem[]>('/api/funds')
export const apiNAV = (code: string) => get<NAVPoint[]>(`/api/nav/${code}`)
export const apiCAGR = (code: string) => get<CAGRPoint[]>(`/api/cagr/${code}`)
export const apiCAGRStats = (code: string) => get<CAGRStatPoint[]>(`/api/cagr/${code}/stats`)
export const apiSIP = (req: SIPRequest) => post<SIPResult>('/api/sip', req)
export const apiSWP = (req: SWPRequest) => post<SWPResult>('/api/swp', req)
export const apiSTP = (req: STPRequest) => post<STPResult>('/api/stp', req)
export const apiCompare = (req: CompareRequest) => post<CompareResult>('/api/compare', req)
export const apiRollingXIRR = (req: RollingXIRRRequest) => post<RollingXIRRPoint[]>('/api/sip/rolling-xirr', req)
export const apiPastForward = (req: PastForwardRequest) => post<PastForwardResult>('/api/past-forward', req)
