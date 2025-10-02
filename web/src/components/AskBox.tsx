import React, { useState } from 'react'

type Props = { onAsk: (q: string, f?: any) => void }
export default function AskBox({ onAsk }: Props){
  const [q, setQ] = useState('')
  const [year, setYear] = useState('')
  const [group, setGroup] = useState('')
  const [state, setState] = useState('')

  return (
    <div className="p-4 rounded-2xl border bg-white space-y-2">
      <div className="flex gap-2">
        <input className="flex-1 border rounded px-3 py-2" placeholder="Ask a question"
          value={q} onChange={e=>setQ(e.target.value)} />
        <button className="px-4 py-2 rounded bg-black text-white" onClick={()=>onAsk(q, {
          year: year? Number(year): undefined,
          group: group||undefined,
          state: state||undefined,
        })}>Ask</button>
      </div>
      <div className="flex gap-2">
        <input className="border rounded px-2 py-1 w-28" placeholder="Year" value={year} onChange={e=>setYear(e.target.value)} />
        <input className="border rounded px-2 py-1 w-48" placeholder="Group" value={group} onChange={e=>setGroup(e.target.value)} />
        <input className="border rounded px-2 py-1 w-24" placeholder="State" value={state} onChange={e=>setState(e.target.value)} />
      </div>
    </div>
  )
}
