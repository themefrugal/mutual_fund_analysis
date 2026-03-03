'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'
import { apiFunds, type FundItem } from '@/lib/api'

interface FundContextType {
  funds: FundItem[]
  loading: boolean
  selectedCode: string
  selectedName: string
  setSelected: (code: string, name: string) => void
}

const FundContext = createContext<FundContextType>({
  funds: [],
  loading: true,
  selectedCode: '',
  selectedName: '',
  setSelected: () => {},
})

export function FundProvider({ children }: { children: React.ReactNode }) {
  const [funds, setFunds] = useState<FundItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCode, setSelectedCode] = useState('')
  const [selectedName, setSelectedName] = useState('')

  useEffect(() => {
    apiFunds()
      .then((data) => {
        setFunds(data)
        if (data.length > 0) {
          setSelectedCode(data[0].schemeCode)
          setSelectedName(data[0].schemeName)
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const setSelected = useCallback((code: string, name: string) => {
    setSelectedCode(code)
    setSelectedName(name)
  }, [])

  return (
    <FundContext.Provider value={{ funds, loading, selectedCode, selectedName, setSelected }}>
      {children}
    </FundContext.Provider>
  )
}

export function useFund() {
  return useContext(FundContext)
}
