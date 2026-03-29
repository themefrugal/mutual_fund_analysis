'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import { useFund } from '@/lib/FundContext'
import { apiNAV, type NAVPoint } from '@/lib/api'

function sample<T>(arr: T[], max: number): T[] {
  if (arr.length <= max) return arr
  const step = Math.ceil(arr.length / max)
  return arr.filter((_, i) => i % step === 0 || i === arr.length - 1)
}

export default function NAVPage() {
  const { selectedCode, selectedName } = useFund()
  const [nav, setNav] = useState<NAVPoint[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showTable, setShowTable] = useState(false)
  const [logY, setLogY] = useState(false)

  useEffect(() => {
    if (!selectedCode) return
    setLoading(true)
    setError(null)
    apiNAV(selectedCode)
      .then(setNav)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [selectedCode])

  const chartData = useMemo(() => sample(nav, 1500), [nav])
  const latest = nav.length > 0 ? nav[nav.length - 1] : null
  const oldest = nav.length > 0 ? nav[0] : null
  const allTimeHigh = nav.reduce<number>(
    (m, p) => (p.nav != null && p.nav > m ? p.nav : m),
    0
  )

  const totalReturn =
    latest?.nav != null && oldest?.nav != null && oldest.nav > 0
      ? ((latest.nav - oldest.nav) / oldest.nav) * 100
      : null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">NAV History</h1>
        <p className="mt-1 text-sm text-muted line-clamp-1">{selectedName}</p>
      </div>

      {/* Metric row */}
      {!loading && nav.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">Latest NAV</p>
            <p className="mt-1 text-2xl font-bold text-accent">
              ₹{latest?.nav?.toFixed(4) ?? '—'}
            </p>
            <p className="text-xs text-muted">{latest?.date}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">
              All-Time High
            </p>
            <p className="mt-1 text-2xl font-bold text-text">₹{allTimeHigh.toFixed(4)}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">
              Since Inception
            </p>
            <p
              className={`mt-1 text-2xl font-bold ${
                totalReturn != null && totalReturn >= 0 ? 'text-gain' : 'text-loss'
              }`}
            >
              {totalReturn != null ? `${totalReturn.toFixed(1)}%` : '—'}
            </p>
            <p className="text-xs text-muted">From {oldest?.date}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">Data Points</p>
            <p className="mt-1 text-2xl font-bold text-text">{nav.length.toLocaleString()}</p>
            <p className="text-xs text-muted">trading days</p>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-text">NAV Over Time</h2>
          <label className="flex items-center gap-1.5 cursor-pointer text-xs text-muted">
            <input
              type="checkbox"
              checked={logY}
              onChange={(e) => setLogY(e.target.checked)}
              className="accent-amber-400"
            />
            Log Y-axis
          </label>
        </div>

        {loading ? (
          <div className="flex h-72 items-center justify-center text-muted text-sm animate-pulse">
            Loading NAV data…
          </div>
        ) : error ? (
          <div className="flex h-72 items-center justify-center text-loss text-sm">{error}</div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: '#1e2232' }}
                tickFormatter={(v: string) => v.slice(0, 7)}
                interval="preserveStartEnd"
              />
              <YAxis
                scale={logY ? 'log' : 'auto'}
                domain={['auto', 'auto']}
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: '#1e2232' }}
                tickFormatter={(v: number) =>
                  `₹${v >= 100 ? v.toFixed(0) : v.toFixed(2)}`
                }
                width={72}
              />
              <Tooltip
                contentStyle={{
                  background: '#0f1117',
                  border: '1px solid #1e2232',
                  borderRadius: 8,
                  color: '#e2e8f0',
                  fontSize: 12,
                }}
                labelFormatter={(l) => `Date: ${l}`}
                formatter={(v: number | undefined, _n?: unknown) => [`₹${v?.toFixed(4)}`, 'NAV']}
              />
              <Line
                type="monotone"
                dataKey="nav"
                stroke="#f59e0b"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Table toggle */}
      {!loading && nav.length > 0 && (
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <button
            onClick={() => setShowTable((v) => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-sm font-semibold text-text hover:bg-bg transition-colors"
          >
            <span>NAV Data Table ({nav.length.toLocaleString()} rows)</span>
            <span className="text-muted text-xs">{showTable ? '▲ Hide' : '▼ Show'}</span>
          </button>
          {showTable && (
            <div className="overflow-x-auto max-h-96 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-bg border-b border-border">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-muted">
                      Date
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-semibold uppercase tracking-wider text-muted">
                      NAV (₹)
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {[...nav].reverse().map((p, i) => (
                    <tr key={p.date} className={i % 2 === 0 ? 'bg-card' : 'bg-bg'}>
                      <td className="px-4 py-2 text-text font-mono text-xs">{p.date}</td>
                      <td className="px-4 py-2 text-right text-text font-mono text-xs">
                        {p.nav?.toFixed(4) ?? '—'}
                      </td>
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
