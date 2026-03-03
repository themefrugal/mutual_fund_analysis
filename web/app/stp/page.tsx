'use client'

import { useState } from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { useFund } from '@/lib/FundContext'
import { apiSTP, type STPResult } from '@/lib/api'
import { formatCurrency, formatPct } from '@/lib/utils'
import MetricCard from '@/components/MetricCard'

function sample<T>(arr: T[], max: number): T[] {
  if (arr.length <= max) return arr
  const step = Math.ceil(arr.length / max)
  return arr.filter((_, i) => i % step === 0 || i === arr.length - 1)
}

export default function STPPage() {
  const { funds, selectedCode, selectedName } = useFund()

  const [sourceCode, setSourceCode] = useState('')
  const [startDate, setStartDate] = useState('2015-01-01')
  const [endDate, setEndDate] = useState('2024-01-01')
  const [initialInvestment, setInitialInvestment] = useState(1000000)
  const [monthlyTransfer, setMonthlyTransfer] = useState(10000)
  const [result, setResult] = useState<STPResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async () => {
    if (!selectedCode || !sourceCode) return
    if (sourceCode === selectedCode) {
      setError('Source and target funds must be different.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const r = await apiSTP({
        source_scheme_code: sourceCode,
        target_scheme_code: selectedCode,
        start_date: startDate,
        end_date: endDate,
        initial_investment: initialInvestment,
        monthly_transfer: monthlyTransfer,
      })
      setResult(r)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const chartData = result ? sample(result.series, 500) : []
  const sourceName = funds.find((f) => f.schemeCode === sourceCode)?.schemeName ?? sourceCode

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">STP Calculator</h1>
        <p className="mt-1 text-sm text-muted">
          Systematic Transfer Plan — transfers from Source into Target fund each month
        </p>
      </div>

      {/* Inputs */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-text mb-4">Parameters</h2>

        {/* Target fund info */}
        <div className="mb-4 rounded-lg border border-accent/30 bg-accent/5 px-4 py-3">
          <p className="text-[10px] text-muted uppercase tracking-wider font-semibold mb-0.5">
            Target Fund (from sidebar)
          </p>
          <p className="text-sm text-accent font-medium">{selectedName || '—'}</p>
          {selectedCode && (
            <p className="text-xs text-muted font-mono">{selectedCode}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="space-y-1.5 sm:col-span-4">
            <label className="text-xs font-medium text-muted uppercase tracking-wider">
              Source Fund (transfer FROM)
            </label>
            <select
              value={sourceCode}
              onChange={(e) => setSourceCode(e.target.value)}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent"
            >
              <option value="">Select source fund…</option>
              {funds
                .filter((f) => f.schemeCode !== selectedCode)
                .map((f) => (
                  <option key={f.schemeCode} value={f.schemeCode}>
                    {f.schemeName}
                  </option>
                ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted uppercase tracking-wider">
              Initial Investment (₹)
            </label>
            <input
              type="number"
              value={initialInvestment}
              onChange={(e) => setInitialInvestment(+e.target.value)}
              min={1000}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted uppercase tracking-wider">
              Monthly Transfer (₹)
            </label>
            <input
              type="number"
              value={monthlyTransfer}
              onChange={(e) => setMonthlyTransfer(+e.target.value)}
              min={100}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted uppercase tracking-wider">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted uppercase tracking-wider">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent"
            />
          </div>
        </div>

        <div className="mt-4">
          <button
            onClick={run}
            disabled={!selectedCode || !sourceCode || loading}
            className="rounded-lg bg-accent px-5 py-2 text-sm font-semibold text-bg hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {loading ? 'Calculating…' : 'Run STP Analysis'}
          </button>
          {!selectedCode && (
            <span className="ml-3 text-xs text-muted">Select a target fund from the sidebar</span>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-loss/30 bg-loss/10 p-4 text-loss text-sm">
          {error}
        </div>
      )}

      {result && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <MetricCard
              label="XIRR"
              value={formatPct(result.xirr)}
              highlight={result.xirr != null ? (result.xirr >= 0 ? 'gain' : 'loss') : 'neutral'}
            />
            <MetricCard
              label="Source Final Value"
              value={formatCurrency(result.source_final)}
              sub={sourceName.slice(0, 30)}
            />
            <MetricCard
              label="Target Final Value"
              value={formatCurrency(result.target_final)}
              highlight="accent"
              sub={selectedName.slice(0, 30)}
            />
            <MetricCard
              label="Total Portfolio"
              value={formatCurrency(result.total_final)}
              highlight="accent"
            />
          </div>

          {/* Portfolio Value Chart */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-text mb-4">Portfolio Value Over Time</h2>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="gradSrc" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradTgt" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#34d399" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradTotal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  tickLine={false}
                  axisLine={{ stroke: '#1e2232' }}
                  tickFormatter={(v: string) => v.slice(0, 7)}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  tickLine={false}
                  axisLine={{ stroke: '#1e2232' }}
                  tickFormatter={(v: number) =>
                    v >= 1_00_000
                      ? `₹${(v / 1_00_000).toFixed(1)}L`
                      : `₹${(v / 1000).toFixed(0)}K`
                  }
                  width={65}
                />
                <Tooltip
                  contentStyle={{
                    background: '#0f1117',
                    border: '1px solid #1e2232',
                    borderRadius: 8,
                    fontSize: 11,
                    color: '#e2e8f0',
                  }}
                  formatter={(v: number | undefined, name: string | undefined) => [
                    `₹${v?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
                    name,
                  ]}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: '#6b7280' }} />
                <Area
                  type="monotone"
                  dataKey="value_src"
                  name={`Source (${sourceName.slice(0, 25)})`}
                  stroke="#60a5fa"
                  fill="url(#gradSrc)"
                  strokeWidth={1.5}
                  dot={false}
                />
                <Area
                  type="monotone"
                  dataKey="value_tgt"
                  name={`Target (${selectedName.slice(0, 25)})`}
                  stroke="#34d399"
                  fill="url(#gradTgt)"
                  strokeWidth={1.5}
                  dot={false}
                />
                <Area
                  type="monotone"
                  dataKey="total_value"
                  name="Total Portfolio"
                  stroke="#f59e0b"
                  fill="url(#gradTotal)"
                  strokeWidth={2}
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Units tracker */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-text mb-1">Units Tracker (Normalised)</h2>
            <p className="text-xs text-muted mb-4">
              Source units depleting ↓ as target units accumulate ↑ (both scaled 0–1)
            </p>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  tickLine={false}
                  axisLine={{ stroke: '#1e2232' }}
                  tickFormatter={(v: string) => v.slice(0, 7)}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  tickLine={false}
                  axisLine={{ stroke: '#1e2232' }}
                  domain={[0, 1]}
                  tickFormatter={(v: number) => v.toFixed(1)}
                  width={40}
                />
                <Tooltip
                  contentStyle={{
                    background: '#0f1117',
                    border: '1px solid #1e2232',
                    borderRadius: 8,
                    fontSize: 11,
                    color: '#e2e8f0',
                  }}
                  formatter={(v: number | undefined, _n?: unknown) => [v?.toFixed(3), '']}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: '#6b7280' }} />
                <Line
                  type="monotone"
                  dataKey="src_units_norm"
                  name="Source units ↓"
                  stroke="#60a5fa"
                  strokeWidth={1.5}
                  dot={false}
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="tgt_units_norm"
                  name="Target units ↑"
                  stroke="#34d399"
                  strokeWidth={1.5}
                  dot={false}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
