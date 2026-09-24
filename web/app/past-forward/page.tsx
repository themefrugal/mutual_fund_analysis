'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useFund } from '@/lib/FundContext'
import { apiPastForward, type MatrixData, type PastForwardObservation, type PastForwardResult } from '@/lib/api'

type HistogramBin = { bucket: number; count: number }

function histogram(values: number[]): HistogramBin[] {
  if (values.length === 0) return []
  const min = Math.min(...values)
  const max = Math.max(...values)
  const width = (max - min) / 40 || 1
  const counts = new Array<number>(40).fill(0)
  values.forEach((value) => { counts[Math.min(Math.floor((value - min) / width), 39)]++ })
  return counts.map((count, index) => ({ bucket: +(min + index * width).toFixed(1), count }))
}

function ObservationTooltip({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload?: PastForwardObservation }> }) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null
  return (
    <div className="rounded-lg border border-border bg-[#0f1117] px-3 py-2 text-xs text-text shadow-lg">
      <p className="font-semibold">As-of date: {point.as_of_date}</p>
      <p className="text-muted">Trailing: {point.backward_start_date} to {point.as_of_date}</p>
      <p>Trailing CAGR: {point.trailing_cagr.toFixed(2)}%</p>
      <p className="text-muted">Subsequent: {point.as_of_date} to {point.forward_end_date}</p>
      <p>Subsequent CAGR: {point.forward_cagr.toFixed(2)}%</p>
    </div>
  )
}

function MatrixTable({ matrix }: { matrix: MatrixData | undefined }) {
  if (!matrix) return null
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[700px] text-xs">
        <thead><tr className="border-b border-border bg-bg"><th className="px-3 py-2 text-left text-muted">Trailing \ Forward</th>{matrix.columns.map((column) => <th key={column} className="px-3 py-2 text-right text-muted">{column}</th>)}</tr></thead>
        <tbody>{matrix.data.map((row, index) => <tr key={matrix.index[index]} className="border-b border-border/60"><td className="px-3 py-2 font-medium text-text">{matrix.index[index]}</td>{row.map((value, cell) => <td key={cell} className="px-3 py-2 text-right font-mono text-muted">{value}</td>)}</tr>)}</tbody>
      </table>
    </div>
  )
}

export default function PastForwardPage() {
  const { selectedCode, selectedName } = useFund()
  const [backwardYears, setBackwardYears] = useState(2)
  const [forwardYears, setForwardYears] = useState(3)
  const [frequency, setFrequency] = useState<'Daily' | 'Weekly' | 'Monthly'>('Weekly')
  const [nonOverlapping, setNonOverlapping] = useState(false)
  const [hurdleRate, setHurdleRate] = useState(0)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [targetReturn, setTargetReturn] = useState('')
  const [result, setResult] = useState<PastForwardResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [matrixTab, setMatrixTab] = useState('Pearson correlation')

  const runAnalysis = useCallback(async () => {
    if (!selectedCode) return
    setLoading(true); setError(null)
    try {
      const next = await apiPastForward({
        scheme_code: selectedCode, backward_years: backwardYears, forward_years: forwardYears,
        frequency, non_overlapping: nonOverlapping, hurdle_rate: hurdleRate,
        ...(startDate ? { start_date: startDate } : {}), ...(endDate ? { end_date: endDate } : {}),
        ...(targetReturn === '' ? {} : { target_return: Number(targetReturn) }),
      })
      setResult(next)
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Analysis failed.') }
    finally { setLoading(false) }
  }, [selectedCode, backwardYears, forwardYears, frequency, nonOverlapping, hurdleRate, startDate, endDate, targetReturn])

  useEffect(() => { void runAnalysis() }, [selectedCode])

  const [range, setRange] = useState<[number, number] | null>(null)
  const observations = result?.observations ?? []
  const minPast = observations.length ? Math.min(...observations.map((point) => point.trailing_cagr)) : 0
  const maxPast = observations.length ? Math.max(...observations.map((point) => point.trailing_cagr)) : 0
  const activeRange = range && range[0] >= minPast && range[1] <= maxPast ? range : [minPast, maxPast]
  const filteredFuture = useMemo(() => observations.filter((point) => point.trailing_cagr >= activeRange[0] && point.trailing_cagr <= activeRange[1]).map((point) => point.forward_cagr), [observations, activeRange])
  const distribution = useMemo(() => histogram(filteredFuture), [filteredFuture])
  const summary = result?.summary
  const slope = summary?.regression_slope
  const intercept = summary?.regression_intercept
  const matrixTabs = ['Pearson correlation', 'Spearman correlation', 'R-squared', 'Fitted line equation', 'Observation count', 'Regression slope', 'Regression intercept', 'Residual standard error']

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold text-text">Past vs Forward Returns</h1><p className="mt-1 text-sm text-muted line-clamp-1">{selectedName}</p></div>
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="grid gap-3 md:grid-cols-4">
          <label className="text-xs text-muted">Trailing period<select value={backwardYears} onChange={(e) => setBackwardYears(+e.target.value)} className="mt-1 block w-full rounded-lg border border-border bg-bg p-2 text-text">{[1, 2, 3, 4, 5].map((year) => <option key={year}>{year}</option>)}</select></label>
          <label className="text-xs text-muted">Forward period<select value={forwardYears} onChange={(e) => setForwardYears(+e.target.value)} className="mt-1 block w-full rounded-lg border border-border bg-bg p-2 text-text">{Array.from({ length: 10 }, (_, index) => index + 1).map((year) => <option key={year}>{year}</option>)}</select></label>
          <label className="text-xs text-muted">Observation frequency<select value={frequency} onChange={(e) => setFrequency(e.target.value as typeof frequency)} className="mt-1 block w-full rounded-lg border border-border bg-bg p-2 text-text">{(['Daily', 'Weekly', 'Monthly'] as const).map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="text-xs text-muted">Annual hurdle (%)<input type="number" value={hurdleRate} onChange={(e) => setHurdleRate(+e.target.value)} className="mt-1 block w-full rounded-lg border border-border bg-bg p-2 text-text" /></label>
          <label className="text-xs text-muted">Analysis start<input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="mt-1 block w-full rounded-lg border border-border bg-bg p-2 text-text" /></label>
          <label className="text-xs text-muted">Analysis end<input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="mt-1 block w-full rounded-lg border border-border bg-bg p-2 text-text" /></label>
          <label className="text-xs text-muted">Comparable trailing CAGR (%)<input type="number" placeholder={result?.current_trailing?.toFixed(2) ?? 'Current'} value={targetReturn} onChange={(e) => setTargetReturn(e.target.value)} className="mt-1 block w-full rounded-lg border border-border bg-bg p-2 text-text" /></label>
          <div className="flex items-end gap-3"><label className="mb-2 flex items-center gap-2 text-xs text-muted"><input type="checkbox" checked={nonOverlapping} onChange={(e) => setNonOverlapping(e.target.checked)} />Non-overlapping</label><button onClick={() => void runAnalysis()} className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-bg">Run analysis</button></div>
        </div>
      </div>
      {loading && <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-muted animate-pulse">Calculating historical return relationships…</div>}
      {error && <div className="rounded-xl border border-loss/30 bg-loss/10 p-4 text-sm text-loss">{error}</div>}
      {result && !loading && <>
        <div className="grid gap-3 md:grid-cols-4">{[
          ['Valid observations', summary?.valid_observations], ['Approx. independent windows', summary?.approx_independent_windows], ['Median trailing CAGR', `${Number(summary?.median_trailing).toFixed(2)}%`], ['Median subsequent CAGR', `${Number(summary?.median_forward).toFixed(2)}%`],
        ].map(([label, value]) => <div key={String(label)} className="rounded-xl border border-border bg-card p-4"><p className="text-xs text-muted">{label}</p><p className="mt-1 font-mono text-lg font-semibold text-text">{String(value)}</p></div>)}</div>
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">Rolling observations overlap. The visible point count overstates independent evidence; correlations and fitted lines are descriptive diagnostics, not forecasts.</div>
        <div className="rounded-xl border border-border bg-card p-5"><h2 className="text-sm font-semibold text-text">Trailing vs Subsequent CAGR</h2><p className="mb-4 text-xs text-muted">Each point is one historical as-of date. Recent dates are excluded until a complete forward window exists.</p><ResponsiveContainer width="100%" height={360}><ScatterChart margin={{ top: 8, right: 18, bottom: 24, left: 10 }}><CartesianGrid strokeDasharray="3 3" stroke="#1e2232" /><XAxis type="number" dataKey="trailing_cagr" tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={(value: number) => `${value.toFixed(0)}%`} label={{ value: `Trailing ${backwardYears}-year CAGR`, position: 'insideBottom', offset: -14, fill: '#6b7280', fontSize: 11 }} /><YAxis type="number" dataKey="forward_cagr" tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={(value: number) => `${value.toFixed(0)}%`} label={{ value: `Subsequent ${forwardYears}-year CAGR`, angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11 }} width={54} /><Tooltip content={<ObservationTooltip />} /><ReferenceLine x={0} stroke="#6b7280" strokeDasharray="4 4" /><ReferenceLine y={0} stroke="#6b7280" strokeDasharray="4 4" />{typeof slope === 'number' && typeof intercept === 'number' && <ReferenceLine segment={[{ x: minPast, y: intercept + slope * minPast }, { x: maxPast, y: intercept + slope * maxPast }]} stroke="#f59e0b" strokeWidth={2} />}<Scatter data={observations} fill="#60a5fa" fillOpacity={.7} /></ScatterChart></ResponsiveContainer></div>
        <div className="rounded-xl border border-border bg-card p-5"><label className="block text-xs font-semibold text-text">Trailing CAGR range for the distribution <span className="float-right font-mono text-muted">{activeRange[0].toFixed(1)}% – {activeRange[1].toFixed(1)}%</span></label><div className="mt-3 grid gap-1"><input type="range" min={minPast} max={maxPast} step={Math.max((maxPast - minPast) / 100, .01)} value={activeRange[0]} onChange={(e) => setRange((current) => { const high = current?.[1] ?? maxPast; return [Math.min(+e.target.value, high), high] })} className="w-full accent-accent" /><input type="range" min={minPast} max={maxPast} step={Math.max((maxPast - minPast) / 100, .01)} value={activeRange[1]} onChange={(e) => setRange((current) => { const low = current?.[0] ?? minPast; return [low, Math.max(+e.target.value, low)] })} className="w-full accent-accent" /></div><p className="mt-2 text-xs text-muted">{filteredFuture.length} matched observations</p><ResponsiveContainer width="100%" height={220}><BarChart data={distribution}><CartesianGrid strokeDasharray="3 3" stroke="#1e2232" /><XAxis dataKey="bucket" tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={(value: number) => `${value}%`} /><YAxis tick={{ fill: '#6b7280', fontSize: 10 }} /><Tooltip /><Bar dataKey="count" fill="#f59e0b" fillOpacity={.7} /></BarChart></ResponsiveContainer></div>
        <div className="rounded-xl border border-border bg-card p-5"><h2 className="text-sm font-semibold text-text">Deterministic interpretation</h2>{Object.entries(result.narrative).flatMap(([, lines]) => lines).map((line) => <p key={line} className="mt-2 text-sm text-muted">{line}</p>)}</div>
        <div className="rounded-xl border border-border bg-card p-5"><h2 className="text-sm font-semibold text-text">What historically followed similar trailing returns?</h2><p className="mt-1 text-xs text-muted">Historical conditional estimates from the nearest within-fund observations; they are not model predictions.</p><div className="mt-4 grid gap-3 sm:grid-cols-4">{Object.entries(result.conditional).map(([key, value]) => <div key={key} className="rounded-lg bg-bg p-3"><p className="text-[10px] uppercase text-muted">{key.replaceAll('_', ' ')}</p><p className="mt-1 font-mono text-sm text-text">{typeof value === 'number' ? value.toFixed(2) : '—'}</p></div>)}</div></div>
        <div className="rounded-xl border border-border bg-card p-5"><h2 className="text-sm font-semibold text-text">Return zones within this fund</h2><div className="mt-4 overflow-x-auto"><table className="w-full text-xs"><thead><tr className="border-b border-border">{Object.keys(result.zone_summary[0] ?? {}).map((key) => <th key={key} className="px-2 py-2 text-left text-muted">{key.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{result.zone_summary.map((row, index) => <tr key={index} className="border-b border-border/60">{Object.values(row).map((value, cell) => <td key={cell} className="px-2 py-2 text-muted">{String(value)}</td>)}</tr>)}</tbody></table></div></div>
        <div className="rounded-xl border border-border bg-card p-5"><h2 className="text-sm font-semibold text-text">Complete scatter-derived metric tables</h2><p className="mb-4 text-xs text-muted">Rows are trailing horizons (1–5 years); columns are subsequent horizons (1–10 years). Each cell comes from its own scatter.</p><div className="mb-4 flex flex-wrap gap-2">{matrixTabs.map((tab) => <button key={tab} onClick={() => setMatrixTab(tab)} className={`rounded-full border px-3 py-1 text-xs ${matrixTab === tab ? 'border-accent bg-accent/20 text-accent' : 'border-border text-muted'}`}>{tab}</button>)}</div><MatrixTable matrix={result.matrices[matrixTab]} /></div>
      </>}
    </div>
  )
}
