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
} from 'recharts'
import { useFund } from '@/lib/FundContext'
import { apiCompare, type CompareResult } from '@/lib/api'
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
  const [fromDate, setFromDate] = useState('2015-01-01')
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
    setAddSearch('')
    setShowSearch(false)
  }

  const removeFund = (code: string) => setSelectedCodes((p) => p.filter((c) => c !== code))

  const runCompare = useCallback(async () => {
    if (selectedCodes.length === 0) return
    setLoading(true)
    setError(null)
    try {
      const r = await apiCompare({ scheme_codes: selectedCodes, from_date: fromDate })
      setResult(r)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [selectedCodes, fromDate])

  // Pivot cumulative returns
  const cumulChartData = useMemo(() => {
    if (!result) return []
    const dateMap = new Map<string, Record<string, number | string | null>>()
    for (const fund of result.funds) {
      for (const pt of fund.series) {
        if (!dateMap.has(pt.date)) dateMap.set(pt.date, { date: pt.date })
        dateMap.get(pt.date)![fund.name] =
          pt.rebased_nav != null ? (pt.rebased_nav - 1) * 100 : null
      }
    }
    const arr = Array.from(dateMap.values()).sort((a, b) =>
      (a.date as string).localeCompare(b.date as string)
    )
    return sample(arr, 1000)
  }, [result])

  // Pivot drawdown
  const drawdownData = useMemo(() => {
    if (!result) return []
    const dateMap = new Map<string, Record<string, number | string | null>>()
    for (const pt of result.drawdown) {
      if (!dateMap.has(pt.date)) dateMap.set(pt.date, { date: pt.date })
      dateMap.get(pt.date)![pt.mf] = pt.draw_down != null ? pt.draw_down * 100 : null
    }
    const arr = Array.from(dateMap.values()).sort((a, b) =>
      (a.date as string).localeCompare(b.date as string)
    )
    return sample(arr, 1000)
  }, [result])

  const fundNames = result?.funds.map((f) => f.name) ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">Compare Funds</h1>
        <p className="text-sm text-muted mt-1">
          Compare up to 6 funds on cumulative returns and drawdown
        </p>
      </div>

      {/* Fund selector */}
      <div className="rounded-xl border border-border bg-card p-5 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-text mb-3">
            Selected Funds ({selectedCodes.length}/6)
          </h2>
          <div className="flex flex-wrap gap-2">
            {selectedCodes.map((code, i) => (
              <div
                key={code}
                className="flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium"
                style={{
                  borderColor: PALETTE[i % PALETTE.length] + '80',
                  color: PALETTE[i % PALETTE.length],
                }}
              >
                <span className="max-w-[200px] truncate">{nameMap[code] ?? code}</span>
                <button
                  onClick={() => removeFund(code)}
                  className="opacity-70 hover:opacity-100 ml-0.5"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
            {selectedCodes.length < 6 && (
              <button
                onClick={() => setShowSearch((v) => !v)}
                className="flex items-center gap-1.5 rounded-full border border-dashed border-border px-3 py-1 text-xs text-muted hover:border-accent hover:text-accent transition-colors"
              >
                <Plus className="h-3 w-3" /> Add fund
              </button>
            )}
          </div>

          {showSearch && (
            <div className="mt-3 relative">
              <input
                autoFocus
                value={addSearch}
                onChange={(e) => setAddSearch(e.target.value)}
                placeholder="Type to search funds…"
                className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text placeholder:text-muted outline-none focus:border-accent"
              />
              {filteredSearch.length > 0 && (
                <div className="absolute top-full left-0 right-0 z-10 mt-1 max-h-64 overflow-y-auto rounded-lg border border-border bg-card shadow-lg">
                  {filteredSearch.map((f) => (
                    <button
                      key={f.schemeCode}
                      onClick={() => addFund(f.schemeCode)}
                      className="w-full text-left px-3 py-2.5 hover:bg-bg transition-colors border-b border-border last:border-0"
                    >
                      <p className="text-sm text-text leading-tight">{f.schemeName}</p>
                      <p className="text-xs text-muted font-mono">{f.schemeCode}</p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted font-medium">From date:</label>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="rounded-lg border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none focus:border-accent"
            />
          </div>
          <button
            onClick={runCompare}
            disabled={selectedCodes.length === 0 || loading}
            className="rounded-lg bg-accent px-4 py-1.5 text-sm font-semibold text-bg hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {loading ? 'Computing…' : 'Compare'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-loss/30 bg-loss/10 p-4 text-loss text-sm">
          {error}
        </div>
      )}

      {result && (
        <>
          {/* Cumulative returns chart */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-text mb-4">Cumulative Returns (%)</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={cumulChartData}>
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
                  width={55}
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
                <Legend wrapperStyle={{ fontSize: 10, color: '#6b7280' }} />
                {fundNames.map((name, i) => (
                  <Line
                    key={name}
                    type="monotone"
                    dataKey={name}
                    stroke={PALETTE[i % PALETTE.length]}
                    strokeWidth={1.5}
                    dot={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Drawdown chart */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-text mb-1">Drawdown (%)</h2>
            <p className="text-xs text-muted mb-4">
              Percentage decline from rolling all-time high
            </p>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={drawdownData}>
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
                  width={55}
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
                <Legend wrapperStyle={{ fontSize: 10, color: '#6b7280' }} />
                {fundNames.map((name, i) => (
                  <Line
                    key={name}
                    type="monotone"
                    dataKey={name}
                    stroke={PALETTE[i % PALETTE.length]}
                    strokeWidth={1.5}
                    dot={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
