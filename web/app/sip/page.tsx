'use client'

import { useState } from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts'
import { useFund } from '@/lib/FundContext'
import { apiSIP, apiRollingXIRR, type SIPResult, type RollingXIRRPoint } from '@/lib/api'
import { formatCurrency, formatPct } from '@/lib/utils'
import MetricCard from '@/components/MetricCard'

function sample<T>(arr: T[], max: number): T[] {
  if (arr.length <= max) return arr
  const step = Math.ceil(arr.length / max)
  return arr.filter((_, i) => i % step === 0 || i === arr.length - 1)
}

function buildHistogram(points: RollingXIRRPoint[], bins = 40) {
  const vals = points.map((p) => p.xirr).filter((v): v is number => v != null)
  if (vals.length === 0) return { data: [], mean: null, median: null }
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const width = (max - min) / bins || 1
  const counts = new Array(bins).fill(0)
  for (const v of vals) counts[Math.min(Math.floor((v - min) / width), bins - 1)]++
  const sorted = [...vals].sort((a, b) => a - b)
  const mean = vals.reduce((s, v) => s + v, 0) / vals.length
  const mid = Math.floor(sorted.length / 2)
  const median = sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid]
  return {
    data: counts.map((count, i) => ({ bucket: +(min + i * width).toFixed(1), count })),
    mean: +mean.toFixed(2),
    median: +median.toFixed(2),
  }
}

export default function SIPPage() {
  const { selectedCode, selectedName } = useFund()

  const [startDate, setStartDate] = useState('2015-01-01')
  const [endDate, setEndDate] = useState('2024-01-01')
  const [monthlyAmount, setMonthlyAmount] = useState(5000)
  const [stepUp, setStepUp] = useState(0)
  const [result, setResult] = useState<SIPResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [rollWindowYears, setRollWindowYears] = useState(7)
  const [rollAmount, setRollAmount] = useState(1000)
  const [rollStepUp, setRollStepUp] = useState(0)
  const [rollResult, setRollResult] = useState<RollingXIRRPoint[] | null>(null)
  const [rollLoading, setRollLoading] = useState(false)
  const [rollError, setRollError] = useState<string | null>(null)

  const run = async () => {
    if (!selectedCode) return
    setLoading(true)
    setError(null)
    try {
      const r = await apiSIP({
        scheme_code: selectedCode,
        start_date: startDate,
        end_date: endDate,
        monthly_amount: monthlyAmount,
        step_up_pct: stepUp,
      })
      setResult(r)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const runRolling = async () => {
    if (!selectedCode) return
    setRollLoading(true)
    setRollError(null)
    try {
      const r = await apiRollingXIRR({
        scheme_code: selectedCode,
        window_years: rollWindowYears,
        monthly_amount: rollAmount,
        step_up_pct: rollStepUp,
      })
      setRollResult(r)
    } catch (e: unknown) {
      setRollError(e instanceof Error ? e.message : String(e))
    } finally {
      setRollLoading(false)
    }
  }

  const chartData = result ? sample(result.series, 500) : []
  const lastPt = result?.series[result.series.length - 1]

  // Normalise unit accumulation: express each series as % of its final value
  const unitAccData = (() => {
    if (!result) return []
    const pts = sample(result.series.filter((p) => p.invested_amount != null && p.cum_units != null), 400)
    const maxInv = Math.max(...pts.map((p) => p.invested_amount!))
    const maxUnits = Math.max(...pts.map((p) => p.cum_units!))
    if (maxInv === 0 || maxUnits === 0) return []
    return pts.map((p) => ({
      date: p.date,
      invested_pct: +((p.invested_amount! / maxInv) * 100).toFixed(2),
      units_pct: +((p.cum_units! / maxUnits) * 100).toFixed(2),
    }))
  })()

  const rollPoints = (rollResult ?? []).filter((p) => p.xirr != null)
  const hist = buildHistogram(rollPoints)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">SIP Calculator</h1>
        <p className="mt-1 text-sm text-muted">
          Systematic Investment Plan — {selectedName || 'Select a fund from sidebar'}
        </p>
      </div>

      {/* Inputs */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-text mb-4">Parameters</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted uppercase tracking-wider">Monthly Amount (₹)</label>
            <input type="number" value={monthlyAmount} onChange={(e) => setMonthlyAmount(+e.target.value)} min={100}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent" />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted uppercase tracking-wider">Annual Step-Up (%)</label>
            <input type="number" value={stepUp} onChange={(e) => setStepUp(+e.target.value)} min={0} max={50} step={1}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent" />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted uppercase tracking-wider">Start Date</label>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent" />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted uppercase tracking-wider">End Date</label>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent" />
          </div>
        </div>
        <div className="mt-4">
          <button onClick={run} disabled={!selectedCode || loading}
            className="rounded-lg bg-accent px-5 py-2 text-sm font-semibold text-bg hover:bg-accent-hover disabled:opacity-50 transition-colors">
            {loading ? 'Calculating…' : 'Run SIP Analysis'}
          </button>
          {!selectedCode && <span className="ml-3 text-xs text-muted">Select a fund from the sidebar first</span>}
        </div>
      </div>

      {error && <div className="rounded-xl border border-loss/30 bg-loss/10 p-4 text-loss text-sm">{error}</div>}

      {result && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <MetricCard label="XIRR" value={formatPct(result.xirr)}
              highlight={result.xirr != null ? (result.xirr >= 0 ? 'gain' : 'loss') : 'neutral'} />
            <MetricCard label="Total Invested" value={formatCurrency(lastPt?.invested_amount)} />
            <MetricCard label="Current Value" value={formatCurrency(lastPt?.current_value)} highlight="accent" />
            <MetricCard label="Gain / Loss"
              value={lastPt?.current_value != null && lastPt?.invested_amount != null
                ? formatCurrency(lastPt.current_value - lastPt.invested_amount) : '—'}
              highlight={lastPt?.current_value != null && lastPt?.invested_amount != null
                ? lastPt.current_value >= lastPt.invested_amount ? 'gain' : 'loss' : 'neutral'} />
          </div>

          {/* Portfolio value chart */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-text mb-4">Portfolio Value Over Time</h2>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="gradInvested" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6b7280" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6b7280" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false}
                  axisLine={{ stroke: '#1e2232' }} tickFormatter={(v: string) => v.slice(0, 7)} interval="preserveStartEnd" />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#1e2232' }}
                  tickFormatter={(v: number) => v >= 1_00_000 ? `₹${(v / 1_00_000).toFixed(1)}L` : `₹${(v / 1000).toFixed(0)}K`} width={65} />
                <Tooltip contentStyle={{ background: '#0f1117', border: '1px solid #1e2232', borderRadius: 8, fontSize: 11, color: '#e2e8f0' }}
                  formatter={(v: number) => [`₹${v?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`, undefined]} />
                <Legend wrapperStyle={{ fontSize: 11, color: '#6b7280' }} />
                <Area type="monotone" dataKey="invested_amount" name="Amount Invested" stroke="#6b7280"
                  fill="url(#gradInvested)" strokeWidth={1.5} dot={false} />
                <Area type="monotone" dataKey="current_value" name="Current Value" stroke="#f59e0b"
                  fill="url(#gradValue)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Unit accumulation chart */}
          {unitAccData.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-sm font-semibold text-text mb-1">Unit Accumulation — Normalised</h2>
              <p className="text-xs text-muted mb-4">Both series rescaled to 0–100% of their final value</p>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={unitAccData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                  <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false}
                    axisLine={{ stroke: '#1e2232' }} tickFormatter={(v: string) => v.slice(0, 7)} interval="preserveStartEnd" />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#1e2232' }}
                    tickFormatter={(v: number) => `${v.toFixed(0)}%`} width={48} />
                  <Tooltip contentStyle={{ background: '#0f1117', border: '1px solid #1e2232', borderRadius: 8, fontSize: 11, color: '#e2e8f0' }}
                    formatter={(v: number, name: string) => [`${v?.toFixed(1)}%`, name]} />
                  <Legend wrapperStyle={{ fontSize: 11, color: '#6b7280' }} />
                  <Line type="monotone" dataKey="invested_pct" name="Amount Invested %" stroke="#6b7280" strokeWidth={1.5} dot={false} />
                  <Line type="monotone" dataKey="units_pct" name="Units Accumulated %" stroke="#f59e0b" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {/* Rolling SIP XIRR */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-text mb-1">Rolling SIP XIRR Distribution</h2>
        <p className="text-xs text-muted mb-4">
          Slide a fixed-duration SIP window across the full NAV history and see how XIRR varies by start date.
        </p>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted uppercase tracking-wider">SIP Duration (years)</label>
            <input type="number" value={rollWindowYears} onChange={(e) => setRollWindowYears(+e.target.value)} min={1} max={20} step={1}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent" />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted uppercase tracking-wider">Monthly Amount (₹)</label>
            <input type="number" value={rollAmount} onChange={(e) => setRollAmount(+e.target.value)} min={100} step={100}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent" />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted uppercase tracking-wider">Annual Step-Up (%)</label>
            <input type="number" value={rollStepUp} onChange={(e) => setRollStepUp(+e.target.value)} min={0} max={50} step={1}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent" />
          </div>
        </div>
        <button onClick={runRolling} disabled={!selectedCode || rollLoading}
          className="rounded-lg bg-accent px-5 py-2 text-sm font-semibold text-bg hover:bg-accent-hover disabled:opacity-50 transition-colors">
          {rollLoading ? 'Computing…' : 'Compute Rolling XIRR'}
        </button>

        {rollError && <div className="mt-3 text-loss text-sm">{rollError}</div>}

        {rollResult && rollPoints.length === 0 && (
          <p className="mt-3 text-sm text-muted">No valid windows found — try a shorter duration.</p>
        )}

        {rollPoints.length > 0 && (
          <div className="mt-6 space-y-6">
            {/* Stats row */}
            <div className="flex flex-wrap gap-5 text-xs">
              {hist.mean != null && (
                <div className="flex flex-col gap-0.5">
                  <span className="text-muted uppercase tracking-wider">Mean</span>
                  <span className="font-semibold font-mono text-accent">{hist.mean.toFixed(2)}%</span>
                </div>
              )}
              {hist.median != null && (
                <div className="flex flex-col gap-0.5">
                  <span className="text-muted uppercase tracking-wider">Median</span>
                  <span className="font-semibold font-mono text-gain">{hist.median.toFixed(2)}%</span>
                </div>
              )}
              <div className="flex flex-col gap-0.5">
                <span className="text-muted uppercase tracking-wider">Min</span>
                <span className="font-semibold font-mono text-loss">
                  {Math.min(...rollPoints.map((p) => p.xirr!)).toFixed(2)}%
                </span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-muted uppercase tracking-wider">Max</span>
                <span className="font-semibold font-mono text-gain">
                  {Math.max(...rollPoints.map((p) => p.xirr!)).toFixed(2)}%
                </span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-muted uppercase tracking-wider">Windows</span>
                <span className="font-semibold font-mono text-text">{rollPoints.length}</span>
              </div>
            </div>

            {/* Histogram */}
            <div>
              <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
                XIRR Distribution
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={hist.data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                  <XAxis dataKey="bucket" tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false}
                    axisLine={{ stroke: '#1e2232' }} tickFormatter={(v: number) => `${v}%`} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false}
                    axisLine={{ stroke: '#1e2232' }} width={36} />
                  <Tooltip contentStyle={{ background: '#0f1117', border: '1px solid #1e2232', borderRadius: 8, fontSize: 11, color: '#e2e8f0' }}
                    formatter={(v: number) => [v, 'Windows']} labelFormatter={(l) => `XIRR ~${l}%`} />
                  {hist.mean != null && (
                    <ReferenceLine x={hist.mean} stroke="#f59e0b" strokeDasharray="4 4"
                      label={{ value: 'Mean', fill: '#f59e0b', fontSize: 9 }} />
                  )}
                  {hist.median != null && (
                    <ReferenceLine x={hist.median} stroke="#34d399" strokeDasharray="4 4"
                      label={{ value: 'Median', fill: '#34d399', fontSize: 9 }} />
                  )}
                  <Bar dataKey="count" fill="#f59e0b" fillOpacity={0.7} radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* XIRR by start date */}
            <div>
              <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
                XIRR by SIP Start Date
              </h3>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={sample(rollPoints, 500)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                  <XAxis dataKey="start_date" tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false}
                    axisLine={{ stroke: '#1e2232' }} tickFormatter={(v: string) => v.slice(0, 7)} interval="preserveStartEnd" />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false}
                    axisLine={{ stroke: '#1e2232' }} tickFormatter={(v: number) => `${v.toFixed(0)}%`} width={48} />
                  <Tooltip contentStyle={{ background: '#0f1117', border: '1px solid #1e2232', borderRadius: 8, fontSize: 11, color: '#e2e8f0' }}
                    formatter={(v: number) => [`${v?.toFixed(2)}%`, 'XIRR']} />
                  <ReferenceLine y={0} stroke="#1e2232" strokeDasharray="4 4" />
                  <Line type="monotone" dataKey="xirr" name="XIRR" stroke="#f59e0b" strokeWidth={1.5} dot={false} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
