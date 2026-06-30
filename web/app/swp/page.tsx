'use client'

import { useState } from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { useFund } from '@/lib/FundContext'
import { apiSWP, type SWPResult } from '@/lib/api'
import { formatCurrency, formatPct } from '@/lib/utils'
import MetricCard from '@/components/MetricCard'

function sample<T>(arr: T[], max: number): T[] {
  if (arr.length <= max) return arr
  const step = Math.ceil(arr.length / max)
  return arr.filter((_, i) => i % step === 0 || i === arr.length - 1)
}

export default function SWPPage() {
  const { selectedCode, selectedName } = useFund()

  const [startDate, setStartDate] = useState('2015-01-01')
  const [endDate, setEndDate] = useState('2024-01-01')
  const [initialInvestment, setInitialInvestment] = useState(1000000)
  const [monthlyWithdrawal, setMonthlyWithdrawal] = useState(8000)
  const [result, setResult] = useState<SWPResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async () => {
    if (!selectedCode) return
    setLoading(true)
    setError(null)
    try {
      const r = await apiSWP({
        scheme_code: selectedCode,
        start_date: startDate,
        end_date: endDate,
        initial_investment: initialInvestment,
        monthly_withdrawal: monthlyWithdrawal,
      })
      setResult(r)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const chartData = result ? sample(result.series, 500) : []
  const lastPt = result?.series[result.series.length - 1]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">SWP Calculator</h1>
        <p className="mt-1 text-sm text-muted">
          Systematic Withdrawal Plan — {selectedName || 'Select a fund from sidebar'}
        </p>
      </div>

      {/* Inputs */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-text mb-4">Parameters</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
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
              Monthly Withdrawal (₹)
            </label>
            <input
              type="number"
              value={monthlyWithdrawal}
              onChange={(e) => setMonthlyWithdrawal(+e.target.value)}
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
            disabled={!selectedCode || loading}
            className="rounded-lg bg-accent px-5 py-2 text-sm font-semibold text-bg hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {loading ? 'Calculating…' : 'Run SWP Analysis'}
          </button>
          {!selectedCode && (
            <span className="ml-3 text-xs text-muted">Select a fund from the sidebar first</span>
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
            <MetricCard label="Total Withdrawn" value={formatCurrency(lastPt?.cum_amount)} />
            <MetricCard
              label="Remaining Corpus"
              value={formatCurrency(lastPt?.cur_value)}
              highlight="accent"
            />
            <MetricCard label="Total Value" value={formatCurrency(lastPt?.total)} />
          </div>

          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-text mb-4">Corpus Value Over Time</h2>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="gradCor" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradWdr" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
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
                  dataKey="inv_value"
                  name="Initial Value"
                  stroke="#6b7280"
                  fill="none"
                  strokeWidth={1}
                  dot={false}
                  strokeDasharray="4 4"
                />
                <Area
                  type="monotone"
                  dataKey="cur_value"
                  name="Remaining Corpus"
                  stroke="#f59e0b"
                  fill="url(#gradCor)"
                  strokeWidth={2}
                  dot={false}
                />
                <Area
                  type="monotone"
                  dataKey="cum_amount"
                  name="Cumulative Withdrawn"
                  stroke="#60a5fa"
                  fill="url(#gradWdr)"
                  strokeWidth={1.5}
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
