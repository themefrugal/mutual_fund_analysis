'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  TrendingUp,
  BarChart2,
  GitCompare,
  PiggyBank,
  Wallet,
  ArrowLeftRight,
  LayoutDashboard,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import FundSearch from '@/components/FundSearch'
import { useFund } from '@/lib/FundContext'

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/nav', label: 'NAV History', icon: TrendingUp },
  { href: '/cagr', label: 'CAGR Analysis', icon: BarChart2 },
  { href: '/compare', label: 'Compare Funds', icon: GitCompare },
  { href: '/sip', label: 'SIP Calculator', icon: PiggyBank },
  { href: '/swp', label: 'SWP Calculator', icon: Wallet },
  { href: '/stp', label: 'STP Calculator', icon: ArrowLeftRight },
]

export default function Sidebar() {
  const pathname = usePathname()
  const { selectedCode, selectedName } = useFund()

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-sidebar border-r border-border">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2.5 border-b border-border px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent">
          <TrendingUp className="h-4 w-4 text-bg" strokeWidth={2.5} />
        </div>
        <div>
          <p className="text-sm font-bold text-text leading-tight">MF Analyser</p>
          <p className="text-[10px] text-muted uppercase tracking-widest">India</p>
        </div>
      </div>

      {/* Fund search */}
      <div className="border-b border-border p-3">
        <p className="mb-2 px-1 text-[10px] font-semibold uppercase tracking-widest text-muted">
          Active Fund
        </p>
        <FundSearch />
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-widest text-muted">
          Analysis
        </p>
        <ul className="space-y-0.5">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                    active
                      ? 'bg-accent/15 text-accent'
                      : 'text-muted hover:bg-bg hover:text-text'
                  )}
                >
                  <Icon
                    className={cn('h-4 w-4 shrink-0', active ? 'text-accent' : '')}
                  />
                  {label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Selected fund badge */}
      {selectedCode && (
        <div className="border-t border-border p-3">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-1.5">
            Selected Fund
          </p>
          <div className="rounded-lg bg-bg p-2.5 border border-border">
            <p className="text-xs font-medium text-text leading-snug line-clamp-2">
              {selectedName}
            </p>
            <p className="mt-1 text-[10px] font-mono text-accent">{selectedCode}</p>
          </div>
        </div>
      )}
    </aside>
  )
}
