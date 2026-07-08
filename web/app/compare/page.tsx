'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts'
import { useFund } from '@/lib/FundContext'
import { apiCompare, type CompareResult } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import { X, Plus } from 'lucide-react'

const PALETTE = ['#f59e0b', '#60a5fa', '#34d399', '#f87171', '#a78bfa', '#fb923c']

function sample<T>(arr: T[], max: number): T[] {
  if (arr.length <= max) return arr
  const step = Math.ceil(arr.length / max)
  return arr.filter((_, i) => i % step === 0 || i === arr.length - 1)
}

export default function ComparePage() {
  const { selectedCode, funds: ctxFunds } = useFund()

  const [selectedCodes, setSelectedCodes] = useState<string[]>([])
  const [weights, setWeights] = useState<Record<string, string>>({})
  const [showCombo, setShowCombo] = useState(false)
  const [fromDate, setFromDate] = useState('2015-01-01')
  const [growthYear, setGrowthYear] = useState(5)
  const [cagrYear, setCagrYear] = useState(5)
  const [result, setResult] = useState<CompareResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [addSearch, setAddSearch] = useState('')
  const [showSearch, setShowSearch] = useState(false)

  useEffect(() => {
    if (selectedCode && !selectedCodes.includes(selectedCode)) {
      setSelectedCodes([selectedCode])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCode])

  const nameMap = useMemo(() => {
    const m: Record<string, string> = {}
    for (const f of ctxFunds) m[f.schemeCode] = f.schemeName
    return m
  }, [ctxFunds])

  const comparisonCodes = useMemo(() => selectedCodes.slice(1), [selectedCodes])

  const filteredSearch = useMemo(
    () =>
      addSearch.trim().length < 2
        ? []
        : ctxFunds
            .filter(
              (f) =>
                f.schemeName.toLowerCase().includes(addSearch.toLowerCase()) &&
                !selectedCodes.includes(f.schemeCode)
            )
            .slice(0, 30),
    [addSearch, ctxFunds, selectedCodes]
  )

  const addFund = (code: string) => {
    if (selectedCodes.length >= 6) return
    setSelectedCodes((p) => [...p, code])
    setWeights((w) => ({ ...w, [code]: '' }))
    setAddSearch('')
    setShowSearch(false)
  }

  const removeFund = (code: string) => {
    setSelectedCodes((p) => p.filter((c) => c !== code))
    setWeights((w) => { const n = { ...w }; delete n[code]; return n })
  }

  const comboWeights = useMemo(() => {
    if (!showCombo) return undefined
    const parsed = comparisonCodes.map((c) => parseFloat(weights[c] ?? '0') || 0)
    const total = parsed.reduce((s, v) => s + v, 0)
    return Math.abs(total - 100) < 0.01 ? parsed : undefined
  }, [showCombo, comparisonCodes, weights])

  const weightTotal = useMemo(() => {
    if (!showCombo) return 0
    return comparisonCodes.reduce((s, c) => s + (parseFloat(weights[c] ?? '0') || 0), 0)
  }, [showCombo, comparisonCodes, weights])

  const comboIsValid = !showCombo || (comparisonCodes.length > 0 && comboWeights !== undefined)

  const runCompare = useCallback(async () => {
    if (selectedCodes.length === 0) return
    if (showCombo && comparisonCodes.length === 0) {
      setError('Add at least one comparison fund to build a weighted combination.')
      return
    }
    if (showCombo && comboWeights === undefined) {
      setError('Weighted combination must sum to 100%.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const r = await apiCompare({
        scheme_codes: selectedCodes,
        from_date: fromDate,
        combo_weights: comboWeights,
      })
      setResult(r)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [selectedCodes, fromDate, showCombo, comparisonCodes.length, comboWeights])

  const fundNames = result?.funds.map((f) => f.name) ?? []

  // Cumulative returns
  const cumulChartData = useMemo(() => {
    if (!result) return []
    const dateMap = new Map<string, Record<string, number | string | null>>()
    for (const fund of result.funds) {
      for (const pt of fund.series) {
        if (!dateMap.has(pt.date)) dateMap.set(pt.date, { date: pt.date })
        dateMap.get(pt.date)![fund.name] = pt.rebased_nav != null ? (pt.rebased_nav - 1) * 100 : null
      }
    }
    return sample(
      Array.from(dateMap.values()).sort((a, b) => (a.date as string).localeCompare(b.date as string)),
      1000
    )
  }, [result])

  // Drawdown
  const drawdownData = useMemo(() => {
    if (!result) return []
    const dateMap = new Map<string, Record<string, number | string | null>>()
    for (const pt of result.drawdown) {
      if (!dateMap.has(pt.date)) dateMap.set(pt.date, { date: pt.date })
      dateMap.get(pt.date)![pt.mf] = pt.draw_down != null ? pt.draw_down * 100 : null
    }
    return sample(
      Array.from(dateMap.values()).sort((a, b) => (a.date as string).localeCompare(b.date as string)),
      1000
    )
  }, [result])

  // Rolling CAGR for selected year
  const cagrChartData = useMemo(() => {
    if (!result) return []
    const dateMap = new Map<string, Record<string, number | string | null>>()
    for (const pt of result.rolling_cagr) {
      if (pt.years !== cagrYear) continue
      if (!dateMap.has(pt.date)) dateMap.set(pt.date, { date: pt.date })
      dateMap.get(pt.date)![pt.mf] = pt.cagr
    }
    return sample(
      Array.from(dateMap.values()).sort((a, b) => (a.date as string).localeCompare(b.date as string)),
      1000
    )
  }, [result, cagrYear])

  // Growth of ₹1000 for selected holding year
  const growthChartData = useMemo(() => {
    if (!result) return []
    const suffix = `|${growthYear}Y`
    const dateMap = new Map<string, Record<string, number | string | null>>()
    for (const pt of result.growth_series) {
      if (!pt.mf.endsWith(suffix)) continue
      const name = pt.mf.slice(0, -suffix.length)
      if (!dateMap.has(pt.date)) dateMap.set(pt.date, { date: pt.date })
      dateMap.get(pt.date)![name] = pt.end_value
    }
    return sample(
      Array.from(dateMap.values()).sort((a, b) => (a.date as string).localeCompare(b.date as string)),
      1000
    )
  }, [result, growthYear])

  const tooltipStyle = {
    background: '#0f1117',
    border: '1px solid #1e2232',
    borderRadius: 8,
    fontSize: 11,
    color: '#e2e8f0',
  }

  const axisProps = {
    tick: { fill: '#6b7280', fontSize: 10 },
    tickLine: false,
    axisLine: { stroke: '#1e2232' },
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">Compare Funds</h1>
        <p className="text-sm text-muted mt-1">Compare up to 6 funds across multiple metrics</p>
      </div>

      {/* Fund selector */}
      <div className="rounded-xl border border-border bg-card p-5 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-text mb-3">Selected Funds ({selectedCodes.length}/6)</h2>
          <div className="flex flex-wrap gap-2">
            {selectedCodes.map((code, i) => (
              <div key={code} className="flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium"
                style={{ borderColor: PALETTE[i % PALETTE.length] + '80', color: PALETTE[i % PALETTE.length] }}>
                <span className="max-w-[200px] truncate">{nameMap[code] ?? code}</span>
                <button onClick={() => removeFund(code)} className="opacity-70 hover:opacity-100 ml-0.5">
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
            {selectedCodes.length < 6 && (
              <button onClick={() => setShowSearch((v) => !v)}
                className="flex items-center gap-1.5 rounded-full border border-dashed border-border px-3 py-1 text-xs text-muted hover:border-accent hover:text-accent transition-colors">
                <Plus className="h-3 w-3" /> Add fund
              </button>
            )}
          </div>

          {showSearch && (
            <div className="mt-3 relative">
              <input autoFocus value={addSearch} onChange={(e) => setAddSearch(e.target.value)}
                placeholder="Type to search funds…"
                className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text placeholder:text-muted outline-none focus:border-accent" />
              {filteredSearch.length > 0 && (
                <div className="absolute top-full left-0 right-0 z-10 mt-1 max-h-64 overflow-y-auto rounded-lg border border-border bg-card shadow-lg">
                  {filteredSearch.map((f) => (
                    <button key={f.schemeCode} onClick={() => addFund(f.schemeCode)}
                      className="w-full text-left px-3 py-2.5 hover:bg-bg transition-colors border-b border-border last:border-0">
                      <p className="text-sm text-text leading-tight">{f.schemeName}</p>
                      <p className="text-xs text-muted font-mono">{f.schemeCode}</p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Combo weights */}
        <div>
          <label className="flex items-center gap-2 text-sm text-text cursor-pointer">
            <input type="checkbox" checked={showCombo} onChange={(e) => setShowCombo(e.target.checked)}
              className="accent-accent" />
            Compare against a weighted combination
          </label>
          {showCombo && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-muted">Weights apply only to added comparison funds. The first selected fund is the benchmark.</p>
              {comparisonCodes.length === 0 ? (
                <p className="text-xs text-loss">Add at least one comparison fund.</p>
              ) : (
                <>
                  {comparisonCodes.map((code) => (
                    <div key={code} className="flex items-center gap-3">
                      <span className="text-xs text-muted w-48 truncate">{nameMap[code] ?? code}</span>
                      <input type="number" value={weights[code] ?? ''} placeholder="0"
                        onChange={(e) => setWeights((w) => ({ ...w, [code]: e.target.value }))}
                        className="w-20 rounded-lg border border-border bg-bg px-2 py-1 text-sm text-text outline-none focus:border-accent" />
                      <span className="text-xs text-muted">%</span>
                    </div>
                  ))}
                  <p className={`text-xs mt-1 ${Math.abs(weightTotal - 100) < 0.01 ? 'text-gain' : 'text-loss'}`}>
                    Total: {weightTotal.toFixed(1)}% {Math.abs(weightTotal - 100) < 0.01 ? 'OK' : '(must sum to 100)'}
                  </p>
                </>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted font-medium">From date:</label>
            <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)}
              className="rounded-lg border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none focus:border-accent" />
          </div>
          <button onClick={runCompare} disabled={selectedCodes.length === 0 || loading || !comboIsValid}
            className="rounded-lg bg-accent px-4 py-1.5 text-sm font-semibold text-bg hover:bg-accent-hover disabled:opacity-50 transition-colors">
            {loading ? 'Computing…' : 'Compare'}
          </button>
        </div>
      </div>

      {error && <div className="rounded-xl border border-loss/30 bg-loss/10 p-4 text-loss text-sm">{error}</div>}

      {result && (
        <>
          {/* Cumulative returns */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-text mb-4">Cumulative Returns (%)</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={cumulChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                <XAxis dataKey="date" {...axisProps} tickFormatter={(v: string) => v.slice(0, 7)} interval="preserveStartEnd" />
                <YAxis {...axisProps} tickFormatter={(v: number) => `${v.toFixed(0)}%`} width={55} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v, name) => [`${(v as number)?.toFixed(2)}%`, name as string]} />
                <Legend wrapperStyle={{ fontSize: 10, color: '#6b7280' }} />
                {fundNames.map((name, i) => (
                  <Line key={name} type="monotone" dataKey={name} stroke={PALETTE[i % PALETTE.length]}
                    strokeWidth={1.5} dot={false} connectNulls />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Drawdown */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-text mb-1">Drawdown (%)</h2>
            <p className="text-xs text-muted mb-4">Percentage decline from rolling all-time high</p>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={drawdownData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                <XAxis dataKey="date" {...axisProps} tickFormatter={(v: string) => v.slice(0, 7)} interval="preserveStartEnd" />
                <YAxis {...axisProps} tickFormatter={(v: number) => `${v.toFixed(0)}%`} width={55} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v, name) => [`${(v as number)?.toFixed(2)}%`, name as string]} />
                <Legend wrapperStyle={{ fontSize: 10, color: '#6b7280' }} />
                {fundNames.map((name, i) => (
                  <Line key={name} type="monotone" dataKey={name} stroke={PALETTE[i % PALETTE.length]}
                    strokeWidth={1.5} dot={false} connectNulls />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Rolling CAGR comparison */}
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-sm font-semibold text-text">Rolling CAGR Comparison</h2>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted">Period:</span>
                <select value={cagrYear} onChange={(e) => setCagrYear(+e.target.value)}
                  className="rounded-lg border border-border bg-bg text-xs text-text px-2 py-1 outline-none focus:border-accent">
                  {[1,2,3,4,5,6,7,8,9,10].map((y) => <option key={y} value={y}>{y}Y</option>)}
                </select>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={cagrChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                <XAxis dataKey="date" {...axisProps} tickFormatter={(v: string) => v.slice(0, 7)} interval="preserveStartEnd" />
                <YAxis {...axisProps} tickFormatter={(v: number) => `${v?.toFixed(0)}%`} width={55} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v, name) => [`${(v as number)?.toFixed(2)}%`, name as string]} />
                <Legend wrapperStyle={{ fontSize: 10, color: '#6b7280' }} />
                <ReferenceLine y={0} stroke="#1e2232" strokeDasharray="4 4" />
                {fundNames.map((name, i) => (
                  <Line key={name} type="monotone" dataKey={name} stroke={PALETTE[i % PALETTE.length]}
                    strokeWidth={1.5} dot={false} connectNulls />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Comparative growth ₹1000 */}
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
              <div>
                <h2 className="text-sm font-semibold text-text">Comparative Growth — Value of ₹1,000 Invested</h2>
                <p className="text-xs text-muted mt-0.5">End value of ₹1000 invested N years prior, at each date</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted">Holding period:</span>
                <select value={growthYear} onChange={(e) => setGrowthYear(+e.target.value)}
                  className="rounded-lg border border-border bg-bg text-xs text-text px-2 py-1 outline-none focus:border-accent">
                  {[1,2,3,4,5,6,7,8,9,10].map((y) => <option key={y} value={y}>{y}Y</option>)}
                </select>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={growthChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2232" />
                <XAxis dataKey="date" {...axisProps} tickFormatter={(v: string) => v.slice(0, 7)} interval="preserveStartEnd" />
                <YAxis {...axisProps} tickFormatter={(v: number) => formatCurrency(v)} width={72} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v, name) => [formatCurrency(v as number), name as string]} />
                <Legend wrapperStyle={{ fontSize: 10, color: '#6b7280' }} />
                <ReferenceLine y={1000} stroke="#4b5563" strokeDasharray="4 4" label={{ value: '₹1,000', fill: '#6b7280', fontSize: 9 }} />
                {fundNames.map((name, i) => (
                  <Line key={name} type="monotone" dataKey={name} stroke={PALETTE[i % PALETTE.length]}
                    strokeWidth={1.5} dot={false} connectNulls />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Drawdown recovery table */}
          {result.drawdown_recovery.length > 0 && (
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="border-b border-border px-5 py-3">
                <h2 className="text-sm font-semibold text-text">Drawdown Recovery</h2>
                <p className="text-xs text-muted mt-0.5">Earliest date when the current NAV level was last exceeded</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-bg">
                      {['Fund', 'Latest Date', 'Latest NAV', 'NAV Last Exceeded On', 'NAV Then'].map((h) => (
                        <th key={h} className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted text-left">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.drawdown_recovery.map((row, i) => (
                      <tr key={row.name} className={i % 2 === 0 ? 'bg-card' : 'bg-bg'}>
                        <td className="px-4 py-2.5 text-xs text-text font-medium max-w-[220px] truncate">{row.name}</td>
                        <td className="px-4 py-2.5 text-xs text-muted font-mono">{row.latest_date}</td>
                        <td className="px-4 py-2.5 text-xs text-text font-mono">{row.latest_nav?.toFixed(2) ?? '—'}</td>
                        <td className="px-4 py-2.5 text-xs font-mono">
                          {row.last_seen_date
                            ? <span className="text-loss">{row.last_seen_date}</span>
                            : <span className="text-gain">At all-time high</span>}
                        </td>
                        <td className="px-4 py-2.5 text-xs text-muted font-mono">{row.last_seen_nav?.toFixed(2) ?? '—'}</td>
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


