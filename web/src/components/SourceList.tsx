export default function SourceList({ sources }: { sources: any[] }){
  if(!sources?.length) return null
  return (
    <div className="p-4 rounded-2xl border bg-white">
      <div className="font-semibold mb-2">Sources</div>
      <ol className="list-decimal ml-5 space-y-1">
        {sources.map(s => (
          <li key={s.rank}>
            <span className="font-mono">{s.path}</span>
            {s.page !== null && s.page !== undefined ? ` (p.${s.page})` : ''}
            {` — score ${s.score}`}
          </li>
        ))}
      </ol>
    </div>
  )
}
