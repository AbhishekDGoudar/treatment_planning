export default function AnswerPane({ answer }: { answer: string }){
  if(!answer) return <div className="p-4 rounded-2xl border bg-white">Answer will appear here.</div>
  return (
    <div className="p-4 rounded-2xl border bg-white whitespace-pre-wrap">{answer}</div>
  )
}
