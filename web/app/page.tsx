'use client'

import { useEffect, useState } from 'react'
import { useFund } from '@/lib/FundContext'
import { apiNAV, apiCAGRStats, type NAVPoint, type CAGRStatPoint } from '@/lib/api'
import MetricCard from '@/components/MetricCard'
import { formatPct, gainLossClass } from '@/lib/utils'
import { TrendingUp, Activity, PiggyBank } from 'lucide-react'

export default function DashboardPage() {
  const { selectedCode, selectedName, loading: fundsLoading } = useFund()
  const [nav, setNav] = useState<NAVPoint[]>([])
  const [stats, setStats] = useState<CAGRStatPoint[]>([])
  const [dataLoading, setDataLoading] = useState(false)

  useEffect(() => {
    if (!selectedCode) return
    setDataLoading(true)
    Promise.all([apiNAV(selectedCode), apiCAGRStats(selectedCode)])
      .then(([n, s]) => {
        setNav(n)
        setStats(s)
      })
      .catch(console.error)
      .finally(() => setDataLoading(false))
  }, [selectedCode])

  if (fundsLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-muted text-sm animate-pulse">Loading funds…</div>
      </div>
    )
  }

  const latest = nav.length > 0 ? nav[nav.length - 1] : null
  const prev = nav.length > 1 ? nav[nav.length - 2] : null
  const dayChange =
    latest && prev && latest.nav != null && prev.nav != null
      ? ((latest.nav - prev.nav) / prev.nav) * 100
      : null

  const oneYrStats = stats.find((s) => s.years === 1)
  const fiveYrStats = stats.find((s) => s.years === 5)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">Dashboard</h1>
        <p className="mt-1 text-sm text-muted line-clamp-1">{selectedName}</p>
      </div>

      {dataLoading ? (
        <div className="flex h-40 items-center justify-center text-muted text-sm animate-pulse">
          Loading data…
        </div>
      ) : (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <MetricCard
              label="Latest NAV"
              value={latest?.nav != null ? `₹${latest.nav.toFixed(4)}` : '—'}
              sub={latest?.date}
              highlight="accent"
            />
            <MetricCard
              label="Day Change"
              value={formatPct(dayChange)}
              highlight={dayChange != null ? (dayChange >= 0 ? 'gain' : 'loss') : 'neutral'}
            />
            <MetricCard
              label="1Y Median CAGR"
              value={formatPct(oneYrStats?.median)}
              sub={`Mean: ${formatPct(oneYrStats?.mean)}`}
              highlight={
                oneYrStats?.median != null
                  ? oneYrStats.median >= 0
                    ? 'gain'
                    : 'loss'
                  : 'neutral'
              }
            />
            <MetricCard
              label="5Y Median CAGR"
              value={formatPct(fiveYrStats?.median)}
              sub={`Mean: ${formatPct(fiveYrStats?.mean)}`}
              highlight={
                fiveYrStats?.median != null
                  ? fiveYrStats.median >= 0
                    ? 'gain'
                    : 'loss'
                  : 'neutral'
              }
            />
          </div>

          {/* CAGR summary table */}
          {stats.length > 0 && (
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="border-b border-border px-5 py-3">
                <h2 className="text-sm font-semibold text-text">Rolling CAGR Statistics</h2>
                <p className="text-xs text-muted">
                  Historical distribution of returns across holding periods
                </p>
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
                        <td className="px-4 py-3 font-medium text-text">{row.years}Y</td>
                        {[row.min, row.p25, row.median, row.mean, row.p75, row.max].map(
                          (v, j) => (
                            <td
                              key={j}
                              className={`px-4 py-3 text-right font-mono text-xs ${gainLossClass(v)} ${j === 2 ? 'font-semibold' : ''}`}
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

          {/* Quick links */}
          <div className="grid grid-cols-3 gap-3">
            {[
              {
                href: '/nav',
                label: 'NAV History',
                desc: 'Full price history & trends',
                icon: TrendingUp,
              },
              {
                href: '/cagr',
                label: 'CAGR Analysis',
                desc: 'Rolling return distributions',
                icon: Activity,
              },
              {
                href: '/sip',
                label: 'SIP Calculator',
                desc: 'Plan systematic investments',
                icon: PiggyBank,
              },
            ].map(({ href, label, desc, icon: Icon }) => (
              <a
                key={href}
                href={href}
                className="group rounded-xl border border-border bg-card p-4 hover:border-accent transition-colors"
              >
                <Icon className="h-5 w-5 text-accent mb-2" />
                <p className="text-sm font-semibold text-text group-hover:text-accent transition-colors">
                  {label}
                </p>
                <p className="text-xs text-muted mt-0.5">{desc}</p>
              </a>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
