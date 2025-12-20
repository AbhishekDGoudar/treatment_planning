import React, { useState } from 'react'
import QueryToolbar from './QueryToolbar'

// Updated Props Interface
type Props = { 
  onExecute: (q: string, f?: any) => void
  onExplain: (q: string, f?: any) => void
  isLoading?: boolean 
}

export default function AskBox({ onExecute, onExplain, isLoading = false }: Props){
  const [q, setQ] = useState('')
  const [year, setYear] = useState('')
  const [group, setGroup] = useState('')
  const [state, setState] = useState('')

  // Helper to bundle filters
  const getFilters = () => ({
    year: year ? Number(year) : undefined,
    group: group || undefined,
    state: state || undefined,
  })

  return (
    <div className="p-4 rounded-2xl border bg-white space-y-3 shadow-sm">
      {/* Input Area */}
      <input 
        className="w-full border rounded px-3 py-2 text-lg focus:outline-none focus:ring-2 focus:ring-blue-100" 
        placeholder="Describe the analysis you need..."
        value={q} 
        onChange={e=>setQ(e.target.value)} 
      />
      
      {/* Filters Area */}
      <div className="flex flex-wrap gap-2">
        <input className="border rounded px-2 py-1 w-28 text-sm" placeholder="Year" value={year} onChange={e=>setYear(e.target.value)} />
        <input className="border rounded px-2 py-1 w-48 text-sm" placeholder="Group" value={group} onChange={e=>setGroup(e.target.value)} />
        <input className="border rounded px-2 py-1 w-24 text-sm" placeholder="State" value={state} onChange={e=>setState(e.target.value)} />
      </div>

      {/* Action Toolbar */}
      <div className="border-t pt-2 mt-2">
        <QueryToolbar 
          onExecute={() => onExecute(q, getFilters())}
          onExplain={() => onExplain(q, getFilters())}
          isLoading={isLoading}
        />
      </div>
    </div>
  )
}