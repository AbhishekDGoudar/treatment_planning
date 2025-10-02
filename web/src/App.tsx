import React, { useState } from 'react'
import { ask } from './lib/api'
import AskBox from './components/AskBox'
import AnswerPane from './components/AnswerPane'
import SourceList from './components/SourceList'
import GraphView from './components/GraphView'

export default function App() {
  const [answer, setAnswer] = useState<string>('')
  const [sources, setSources] = useState<any[]>([])
  const [graph, setGraph] = useState<any[]>([])

  const onAsk = async (query: string, filters?: any) => {
    const res = await ask(query, filters)
    setAnswer(res.answer)
    setSources(res.sources)
    setGraph(res.graph)
  }

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900">
      <div className="max-w-6xl mx-auto p-6 space-y-4">
        <h1 className="text-2xl font-bold">Multimodal RAG</h1>
        <AskBox onAsk={onAsk} />
        <div className="grid md:grid-cols-3 gap-4">
          <div className="md:col-span-2 space-y-3">
            <AnswerPane answer={answer} />
            <SourceList sources={sources} />
          </div>
          <div className="md:col-span-1">
            <GraphView raw={graph} />
          </div>
        </div>
      </div>
    </div>
  )
}
