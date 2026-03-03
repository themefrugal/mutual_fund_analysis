'use client'

import { useEffect, useRef, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { Command } from 'cmdk'
import { Search, X } from 'lucide-react'
import { useFund } from '@/lib/FundContext'

export default function FundSearch() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const { funds, loading, selectedName, setSelected } = useFund()
  const inputRef = useRef<HTMLInputElement>(null)

  // Keyboard shortcut: Ctrl+K / Cmd+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setOpen((o) => !o)
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [])

  useEffect(() => {
    if (open) {
      setQuery('')
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  const filtered = query.trim()
    ? funds
        .filter(
          (f) =>
            f.schemeName.toLowerCase().includes(query.toLowerCase()) ||
            f.schemeCode.includes(query) ||
            f.schemeISIN.toLowerCase().includes(query.toLowerCase())
        )
        .slice(0, 50)
    : funds.slice(0, 50)

  const handleSelect = (code: string, name: string) => {
    setSelected(code, name)
    setOpen(false)
  }

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(true)}
        className="w-full flex items-center gap-2 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-muted hover:border-accent hover:text-text transition-colors"
      >
        <Search className="h-4 w-4 shrink-0" />
        <span className="flex-1 text-left truncate">
          {loading ? 'Loading funds…' : selectedName || 'Select fund…'}
        </span>
        <kbd className="hidden sm:inline-flex h-5 select-none items-center gap-0.5 rounded border border-border bg-card px-1.5 font-mono text-[10px] text-muted">
          ⌘K
        </kbd>
      </button>

      {/* Dialog */}
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
          <Dialog.Content
            className="fixed left-1/2 top-[15%] z-50 w-full max-w-xl -translate-x-1/2 overflow-hidden rounded-2xl border border-border bg-card shadow-2xl"
            aria-label="Fund search"
          >
            <Dialog.Title className="sr-only">Search Mutual Funds</Dialog.Title>
            <Command shouldFilter={false} className="flex flex-col">
              {/* Search input */}
              <div className="flex items-center gap-3 border-b border-border px-4 py-3">
                <Search className="h-4 w-4 shrink-0 text-muted" />
                <Command.Input
                  ref={inputRef}
                  value={query}
                  onValueChange={setQuery}
                  placeholder="Search by fund name, code or ISIN…"
                  className="flex-1 bg-transparent text-sm text-text placeholder:text-muted outline-none"
                />
                <button onClick={() => setOpen(false)} className="text-muted hover:text-text">
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Results */}
              <Command.List className="max-h-96 overflow-y-auto py-2">
                <Command.Empty className="px-4 py-8 text-center text-sm text-muted">
                  No funds found.
                </Command.Empty>

                {loading && (
                  <div className="px-4 py-8 text-center text-sm text-muted">Loading funds…</div>
                )}

                {!loading &&
                  filtered.map((f) => (
                    <Command.Item
                      key={f.schemeCode}
                      value={f.schemeCode}
                      onSelect={() => handleSelect(f.schemeCode, f.schemeName)}
                      className="flex flex-col gap-0.5 cursor-pointer px-4 py-2.5 text-sm hover:bg-bg data-[selected=true]:bg-bg transition-colors"
                    >
                      <span className="font-medium text-text leading-tight">{f.schemeName}</span>
                      <span className="text-xs text-muted font-mono">
                        {f.schemeCode} · {f.schemeISIN}
                      </span>
                    </Command.Item>
                  ))}

                {!loading && query.trim() === '' && funds.length > 50 && (
                  <p className="px-4 py-2 text-center text-xs text-muted">
                    Type to search {funds.length.toLocaleString()} funds…
                  </p>
                )}
              </Command.List>
            </Command>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  )
}
