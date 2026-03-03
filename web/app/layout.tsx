import type { Metadata } from 'next'
import '@/app/globals.css'
import Sidebar from '@/components/Sidebar'
import { FundProvider } from '@/lib/FundContext'

export const metadata: Metadata = {
  title: 'MF Analyser — India',
  description: 'Mutual fund NAV, CAGR, SIP, SWP and STP analysis for Indian markets.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">
        <FundProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 ml-64 min-h-screen bg-bg">
              <div className="mx-auto max-w-5xl p-6">
                {children}
              </div>
            </main>
          </div>
        </FundProvider>
      </body>
    </html>
  )
}
