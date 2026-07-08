import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value as number)) return '—'
  const v = value as number
  if (Math.abs(v) >= 1_00_00_000) {
    return `₹${(v / 1_00_00_000).toFixed(2)} Cr`
  }
  if (Math.abs(v) >= 1_00_000) {
    return `₹${(v / 1_00_000).toFixed(2)} L`
  }
  if (Math.abs(v) >= 1_000) {
    return `₹${(v / 1_000).toFixed(1)} K`
  }
  return `₹${v.toFixed(2)}`
}

export function formatPct(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || isNaN(value as number)) return '—'
  return `${(value as number).toFixed(decimals)}%`
}

export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || isNaN(value as number)) return '—'
  return (value as number).toLocaleString('en-IN', { maximumFractionDigits: decimals })
}

export function formatNavDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function gainLossClass(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'text-muted'
  return (value as number) >= 0 ? 'text-gain' : 'text-loss'
}

export function matchesFundSearch(
  query: string,
  fund: { schemeName: string; schemeCode: string; schemeISIN: string }
): boolean {
  const tokens = normalizeSearch(query).split(' ').filter(Boolean)
  if (tokens.length === 0) return true

  const searchable = normalizeSearch(`${fund.schemeName} ${fund.schemeCode} ${fund.schemeISIN}`)
  return tokens.every((token) => searchable.includes(token))
}

function normalizeSearch(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}
