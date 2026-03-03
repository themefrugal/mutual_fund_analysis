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
  Legend,
  BarChart,
  Bar,
  ReferenceLine,
} from 'recharts'
import { useFund } from '@/lib/FundContext'
import { apiCAGR, apiCAGRStats, type CAGRPoint, type CAGRStatPoint } from '@/lib/api'
import { formatPct, gainLossClass } from '@/lib/utils'

const YEAR_COLORS: Record<number, string> = {
  1: '#f59e0b',
  2: '#fbbf24',
  3: '#34d399',
  4: '#4ade80',
  5: '#60a5fa',
  6: '#818cf8',
  7: '#a78bfa',
  8: '#e879f9',
  9: '#fb923c',
  10: '#f87171',
}

function sample<T>(arr: T[], max: number): T[] {
  if (arr.length <= max) return arr
  const step = Math.ceil(arr.length / max)
  return arr.filter((_, i) => i % step === 0 || i === arr.length - 1)
}

export default function CAGRPage() {
  const { selectedCode, selectedName } = useFund()
  const [data, setData] = useState<CAGRPoint[]>([])
  const [stats, setStats] = useState<CAGRStatPoint[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedYears, setSelectedYears] = useState<number[]>([1, 3, 5, 10])
  const [histYear, setHistYear] = useState(5)

  useEffect(() => {
    if (!selectedCode) return
    setLoading(true)
    setError(null)
    Promise.all([apiCAGR(selectedCode), apiCAGRStats(selectedCode)])
      .then(([d, s]) => {
        setData(d)
        setStats(s)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [selectedCode])

  // Pivot data for multi-line chart
  const pivoted = useMemo(() => {
    if (data.length === 0) return []
    const byDate = new Map<string, Record<string, unknown>>()
    for (const p of data) {
      if (!byDate.has(p.date)) byDate.set(p.date, { date: p.date })
      byDate.get(p.date)![`y${p.years}`] = p.cagr
    }
    const arr = Array.from(byDate.values()).sort((a, b) =>
      (a.date as string).localeCompare(b.date as string)
    )
    return sample(arr, 1000)
  }, [data])

  // Histogram data for selected year
  const histData = useMemo(() => {
    const vals = data
      .filter((p) => p.years === histYear && p.cagr != null)
      .map((p) => p.cagr as number)
    if (vals.length === 0) return []
    const min = Math.min(...vals)
    const max = Math.max(...vals)
    const buckets = 40
    const width = (max - min) / buckets || 1
    const counts = new Array(buckets).fill(0)
    for (const v of vals) {
      const i = Math.min(Math.floor((v - min) / width), buckets - 1)
      counts[i]++
    }
    return counts.map((count, i) => ({
      bucket: +(min + i * width).toFixed(1),
      count,
    }))
  }, [data, histYear])

  const histStats = stats.find((s) => s.years === histYear)
  const allYears = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

  const toggleYear = (y: number) => {
    setSelectedYears((prev) =>
      prev.includes(y) ? prev.filter((x) => x !== y) : [...prev, y]
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">CAGR Analysis</h1>
        <p className="mt-1 text-sm text-muted line-clamp-1">{selectedName}</p>
      </div>

      {loading && (
        <div className="flex h-64 items-center justify-center text-muted text-sm animate-pulse">
          Computing rolling CAGR…
        </div>
      )}
      {error && (
        <div className="rounded-xl border border-loss/30 bg-loss/10 p-4 text-loss text-sm">
          {error}
        </div>
      )}

      {!loading && !error && data.length > 0 && (
        <>
          {/* Rolling CAGR lines */}
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-sm font-semibold text-text">Rolling CAGR Over Time</h2>
              <div className="flex flex-wrap gap-1.5">
                {allYears.map((y) => (
                  <button
                    key={y}
                    onClick={() => toggleYear(y)}
                    className={`rounded-full px-2.5 py-0.5 text-xs font-semibold border transition-colors ${
                      selectedYears.includes(y)
                        ? 'border-accent bg-accent/20 text-accent'
                        : 'border-border text-muted hover:border-muted'
                    }`}
                  >
                    {y}Y
                  </button>
                ))}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={pivoted}>
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
                  tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                  width={48}
                />
                <Tooltip
                  contentStyle={{
                    background: '#0f1117',
                    border: '1px solid #1e2232',
                    borderRadius: 8,
                    fontSize: 11,
                    color: '#e2e8f0',
                  }}
                  formatter={(v: number | undefined, name: string | undefined) => [`${v?.toFixed(2)}%`, name]}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: '#6b7280' }} />
                <ReferenceLine y={0} stroke="#1e2232" strokeDasharray="4 4" />
                {selectedYears.map((y) => (
                  <Line
                    key={y}
                    type="monotone"
                    dataKey={`y${y}`}
                    name={`${y}Y CAGR`}
                    stroke={YEAR_COLORS[y] ?? '#94a3b8'}
                    strokeWidth={1.5}
                    dot={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* CAGR Histogram */}
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-sm font-semibold text-text">CAGR Distribution</h2>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted">Period:</span>
                <select
                  value={histYear}
                  onChange={(e) => setHistYear(+e.target.value)}
                  className="rounded-lg border border-border bg-bg text-xs text-text px-2 py-1 outline-none focus:border-accent"
                >
                  {allYears.map((y) => (
                    <option key={y} value={y}>
                      {y} Year
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {histStats && (
              <div className="mb-4 flex flex-wrap gap-5 text-xs">
                {[
                  { label: 'Min', val: histStats.min },
                  { label: 'P25', val: histStats.p25 },
                  { label: 'Median', val: histStats.median },
                  { label: 'Mean', val: histStats.mean },
                  { label: 'P75', val: histStats.p75 },
                  { label: 'Max', val: histStats.max },
                ].map(({ label, val }) => (
                  <div key={label} className="flex flex-col gap-0.5">
                    <span className="text-muted uppercase tracking-wider">{label}</span>
                    <span className={`font-semibold font-mono ${gainLossClass(val)}`}>
                      {formatPct(val)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={histData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                <XAxis
                  dataKey="bucket"
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  tickLine={false}
                  axisLine={{ stroke: '#1e2232' }}
                  tickFormatter={(v: number) => `${v}%`}
                />
                <YAxis
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  tickLine={false}
                  axisLine={{ stroke: '#1e2232' }}
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
                  formatter={(v: number | undefined, _n?: unknown) => [v, 'Occurrences']}
                  labelFormatter={(l) => `CAGR ~${l}%`}
                />
                {histStats?.mean != null && (
                  <ReferenceLine
                    x={+histStats.mean.toFixed(1)}
                    stroke="#f59e0b"
                    strokeDasharray="4 4"
                    label={{ value: 'Mean', fill: '#f59e0b', fontSize: 10 }}
                  />
                )}
                {histStats?.median != null && (
                  <ReferenceLine
                    x={+histStats.median.toFixed(1)}
                    stroke="#34d399"
                    strokeDasharray="4 4"
                    label={{ value: 'Median', fill: '#34d399', fontSize: 10 }}
                  />
                )}
                <Bar dataKey="count" fill="#f59e0b" fillOpacity={0.7} radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Stats Table */}
          {stats.length > 0 && (
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="border-b border-border px-5 py-3">
                <h2 className="text-sm font-semibold text-text">CAGR Statistics Summary</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-bg">
                      {['Period', 'Min', 'P25', 'Median', 'Mean', 'P75', 'Max'].map((h) => (
                        <th
                          key={h}
                          className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted text-right first:text-left"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {stats.map((row, i) => (
                      <tr key={row.years} className={i % 2 === 0 ? 'bg-card' : 'bg-bg'}>
                        <td className="px-4 py-2.5 font-medium text-text">{row.years}Y</td>
                        {[row.min, row.p25, row.median, row.mean, row.p75, row.max].map(
                          (v, j) => (
                            <td
                              key={j}
                              className={`px-4 py-2.5 text-right font-mono text-xs ${gainLossClass(v)} ${j === 2 ? 'font-semibold' : ''}`}
                            >
                              {formatPct(v)}
                            </td>
                          )
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
