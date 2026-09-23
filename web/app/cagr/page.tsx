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
  Scatter,
  ScatterChart,
  ReferenceLine,
  ComposedChart,
  Area,
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

type ForwardReturnPoint = {
  anchorDate: string
  pastStartDate: string
  futureEndDate: string
  pastCagr: number
  futureCagr: number
}

type HistogramData = {
  bins: { bucket: number; count: number }[]
  mean: number | null
  median: number | null
}

function ForwardReturnTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: ReadonlyArray<{ payload?: ForwardReturnPoint }>
}) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null

  return (
    <div className="rounded-lg border border-border bg-[#0f1117] px-3 py-2 text-xs text-text shadow-lg">
      <p className="mb-1 font-semibold">Anchor date: {point.anchorDate}</p>
      <p className="text-muted">Past window: {point.pastStartDate} to {point.anchorDate}</p>
      <p className="text-muted">Future window: {point.anchorDate} to {point.futureEndDate}</p>
      <p className="mt-1">Past return: <span className={gainLossClass(point.pastCagr)}>{point.pastCagr.toFixed(2)}%</span></p>
      <p>Future return: <span className={gainLossClass(point.futureCagr)}>{point.futureCagr.toFixed(2)}%</span></p>
    </div>
  )
}

function shiftByDays(date: string, days: number): string {
  const result = new Date(`${date}T00:00:00Z`)
  result.setUTCDate(result.getUTCDate() + days)
  return result.toISOString().slice(0, 10)
}

function buildHistogram(values: number[]): HistogramData {
  if (values.length === 0) return { bins: [], mean: null, median: null }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const buckets = 40
  const width = (max - min) / buckets || 1
  const counts = new Array<number>(buckets).fill(0)
  for (const value of values) {
    const index = Math.min(Math.floor((value - min) / width), buckets - 1)
    counts[index]++
  }
  const ordered = [...values].sort((a, b) => a - b)
  const middle = Math.floor(ordered.length / 2)
  const median = ordered.length % 2 === 0
    ? (ordered[middle - 1] + ordered[middle]) / 2
    : ordered[middle]
  return {
    bins: counts.map((count, index) => ({ bucket: +(min + index * width).toFixed(1), count })),
    mean: values.reduce((sum, value) => sum + value, 0) / values.length,
    median,
  }
}

function ForwardReturnHistogram({
  data,
  allFutureReturns,
  pastYears,
  futureYears,
}: {
  data: ForwardReturnPoint[]
  allFutureReturns: number[]
  pastYears: number
  futureYears: number
}) {
  const minimum = Math.min(...data.map((point) => point.pastCagr))
  const maximum = Math.max(...data.map((point) => point.pastCagr))
  const [range, setRange] = useState<[number, number]>([minimum, maximum])
  const step = Math.max((maximum - minimum) / 100, 0.01)
  const filtered = data.filter((point) => point.pastCagr >= range[0] && point.pastCagr <= range[1])
  const fullRange = range[0] === minimum && range[1] === maximum
  const histogram = useMemo(
    () => buildHistogram(fullRange ? allFutureReturns : filtered.map((point) => point.futureCagr)),
    [allFutureReturns, filtered, fullRange]
  )

  return (
    <div className="mt-5 border-t border-border pt-5">
      {minimum < maximum ? (
        <div className="mb-5 ml-[60px] mr-4">
          <div className="mb-2 flex items-center justify-between text-xs">
            <label className="font-semibold text-text">Past {pastYears}-year CAGR range for the histogram</label>
            <span className="font-mono text-muted">{range[0].toFixed(1)}% – {range[1].toFixed(1)}%</span>
          </div>
          <div className="space-y-1">
            <input
              aria-label="Minimum past CAGR"
              type="range"
              min={minimum}
              max={maximum}
              step={step}
              value={range[0]}
              onChange={(e) => setRange((current) => [Math.min(+e.target.value, current[1]), current[1]])}
              className="h-2 w-full cursor-pointer accent-accent"
            />
            <input
              aria-label="Maximum past CAGR"
              type="range"
              min={minimum}
              max={maximum}
              step={step}
              value={range[1]}
              onChange={(e) => setRange((current) => [current[0], Math.max(+e.target.value, current[0])])}
              className="h-2 w-full cursor-pointer accent-accent"
            />
          </div>
          <div className="mt-1 flex justify-between text-[10px] text-muted"><span>{minimum.toFixed(1)}%</span><span>{maximum.toFixed(1)}%</span></div>
        </div>
      ) : (
        <p className="mb-5 text-xs text-muted">Past {pastYears}-year CAGR is {minimum.toFixed(2)}% for every point.</p>
      )}
      <h3 className="mb-1 text-xs font-semibold text-text">Distribution of Next {futureYears}-year Returns</h3>
      <p className="mb-3 text-xs text-muted">{fullRange ? allFutureReturns.length : filtered.length.toLocaleString()} of {allFutureReturns.length.toLocaleString()} future-return observations are shown.</p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={histogram.bins}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
          <XAxis dataKey="bucket" tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#1e2232' }} tickFormatter={(v: number) => `${v}%`} />
          <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#1e2232' }} width={40} />
          <Tooltip contentStyle={{ background: '#0f1117', border: '1px solid #1e2232', borderRadius: 8, fontSize: 11, color: '#e2e8f0' }} formatter={(v: number | undefined) => [v, 'Occurrences']} labelFormatter={(v) => `Future CAGR ~${v}%`} />
          {histogram.mean != null && <ReferenceLine x={+histogram.mean.toFixed(1)} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: 'Mean', fill: '#f59e0b', fontSize: 10 }} />}
          {histogram.median != null && <ReferenceLine x={+histogram.median.toFixed(1)} stroke="#34d399" strokeDasharray="4 4" label={{ value: 'Median', fill: '#34d399', fontSize: 10 }} />}
          <Bar dataKey="count" fill="#f59e0b" fillOpacity={0.7} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function CAGRPage() {
  const { selectedCode, selectedName } = useFund()
  const [data, setData] = useState<CAGRPoint[]>([])
  const [stats, setStats] = useState<CAGRStatPoint[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedYears, setSelectedYears] = useState<number[]>([1, 3, 5, 10])
  const [histYear, setHistYear] = useState(3)
  const [pastYears, setPastYears] = useState(2)
  const [futureYears, setFutureYears] = useState(3)

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

  const forwardReturnData = useMemo<ForwardReturnPoint[]>(() => {
    const returnsByPeriod = new Map<number, Map<string, number>>()
    for (const point of data) {
      if (point.cagr == null) continue
      if (!returnsByPeriod.has(point.years)) returnsByPeriod.set(point.years, new Map())
      returnsByPeriod.get(point.years)!.set(point.date, point.cagr)
    }

    const pastReturns = returnsByPeriod.get(pastYears)
    const futureReturns = returnsByPeriod.get(futureYears)
    if (!pastReturns || !futureReturns) return []

    return Array.from(pastReturns.entries()).flatMap(([anchorDate, pastCagr]) => {
      // CAGR periods use fixed 365-day windows in the backend, so use the same
      // convention when locating the end of the forward-looking window.
      const futureEndDate = shiftByDays(anchorDate, 365 * futureYears)
      const futureCagr = futureReturns.get(futureEndDate)
      if (futureCagr == null) return []
      return [{
        anchorDate,
        pastStartDate: shiftByDays(anchorDate, -365 * pastYears),
        futureEndDate,
        pastCagr,
        futureCagr,
      }]
    })
  }, [data, pastYears, futureYears])

  const allFutureReturns = useMemo(
    () => data.filter((point) => point.years === futureYears && point.cagr != null).map((point) => point.cagr as number),
    [data, futureYears]
  )

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

          {/* Past-to-future return scatter */}
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="mb-1 flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-sm font-semibold text-text">Past Return vs Future Return</h2>
              <div className="flex items-center gap-3 text-xs">
                <label className="flex items-center gap-2 text-muted">
                  Past return:
                  <select
                    value={pastYears}
                    onChange={(e) => setPastYears(+e.target.value)}
                    className="rounded-lg border border-border bg-bg px-2 py-1 text-text outline-none focus:border-accent"
                  >
                    {allYears.map((y) => <option key={y} value={y}>{y} Year{y === 1 ? '' : 's'}</option>)}
                  </select>
                </label>
                <label className="flex items-center gap-2 text-muted">
                  Future return:
                  <select
                    value={futureYears}
                    onChange={(e) => {
                      const years = +e.target.value
                      setFutureYears(years)
                      setHistYear(years)
                    }}
                    className="rounded-lg border border-border bg-bg px-2 py-1 text-text outline-none focus:border-accent"
                  >
                    {allYears.map((y) => <option key={y} value={y}>{y} Year{y === 1 ? '' : 's'}</option>)}
                  </select>
                </label>
              </div>
            </div>
            <p className="mb-4 text-xs text-muted">
              Each dot pairs the return before an anchor date with the return after it. Time determines neither position nor order.
            </p>
            {forwardReturnData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={320}>
                  <ScatterChart margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                    <XAxis
                      type="number"
                      dataKey="pastCagr"
                      name={`Past ${pastYears}-year CAGR`}
                      tick={{ fill: '#6b7280', fontSize: 10 }}
                      tickLine={false}
                      axisLine={{ stroke: '#1e2232' }}
                      tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                      label={{ value: `Past ${pastYears}-year CAGR`, position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 11 }}
                    />
                    <YAxis
                      type="number"
                      dataKey="futureCagr"
                      name={`Next ${futureYears}-year CAGR`}
                      tick={{ fill: '#6b7280', fontSize: 10 }}
                      tickLine={false}
                      axisLine={{ stroke: '#1e2232' }}
                      tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                      label={{ value: `Next ${futureYears}-year CAGR`, angle: -90, position: 'insideLeft', offset: 0, fill: '#6b7280', fontSize: 11 }}
                      width={52}
                    />
                    <Tooltip content={<ForwardReturnTooltip />} cursor={{ stroke: '#6b7280', strokeDasharray: '4 4' }} />
                    <ReferenceLine x={0} stroke="#6b7280" strokeDasharray="4 4" />
                    <ReferenceLine y={0} stroke="#6b7280" strokeDasharray="4 4" />
                    <Scatter data={forwardReturnData} fill="#60a5fa" fillOpacity={0.6} />
                  </ScatterChart>
                </ResponsiveContainer>
                <ForwardReturnHistogram key={`${pastYears}-${futureYears}`} data={forwardReturnData} allFutureReturns={allFutureReturns} pastYears={pastYears} futureYears={futureYears} />
              </>
            ) : (
              <div className="flex h-80 items-center justify-center text-sm text-muted">
                Not enough history to pair a past {pastYears}-year return with a future {futureYears}-year return.
              </div>
            )}
          </div>

          {/* Equity Yield Curve */}
          {stats.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-sm font-semibold text-text mb-1">Equity Yield Curve</h2>
              <p className="text-xs text-muted mb-4">
                Min and max CAGR achieved across all windows, by holding period
              </p>
              <ResponsiveContainer width="100%" height={240}>
                <ComposedChart data={stats.map((s) => ({ period: `${s.years}Y`, min: s.min, max: s.max, median: s.median }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                  <XAxis dataKey="period" tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#1e2232' }} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#1e2232' }}
                    tickFormatter={(v: number) => `${v.toFixed(0)}%`} width={48} />
                  <Tooltip contentStyle={{ background: '#0f1117', border: '1px solid #1e2232', borderRadius: 8, fontSize: 11, color: '#e2e8f0' }}
                    formatter={(v, name) => [`${(v as number)?.toFixed(2)}%`, name]} />
                  <Legend wrapperStyle={{ fontSize: 11, color: '#6b7280' }} />
                  <ReferenceLine y={0} stroke="#1e2232" strokeDasharray="4 4" />
                  <Area type="monotone" dataKey="max" name="Max CAGR" stroke="#34d399" fill="#34d399" fillOpacity={0.15} strokeWidth={2} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="median" name="Median CAGR" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} strokeDasharray="5 3" />
                  <Area type="monotone" dataKey="min" name="Min CAGR" stroke="#f87171" fill="#f87171" fillOpacity={0.15} strokeWidth={2} dot={{ r: 4 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

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
