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
