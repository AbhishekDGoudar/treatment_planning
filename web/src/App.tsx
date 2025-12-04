import React, { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { ask } from './lib/api'
import AskBox from './components/AskBox'
import AnswerPane from './components/AnswerPane'
import SourceList from './components/SourceList'
import GraphView from './components/GraphView'
import FileUpload from './components/FileUpload' 
import WaiverTable from './components/WaiverTable'


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
    <Router>
      {/* ✅ Navigation Bar */}
      <nav className="bg-white shadow p-4 mb-4">
        <div className="max-w-6xl mx-auto flex gap-4">
          <Link to="/" className="text-blue-600 hover:underline">Multimodal RAG</Link>
          <Link to="/upload" className="text-blue-600 hover:underline">Upload File</Link>
          <Link to="/documents" className="text-blue-600 hover:underline">Waiver Table</Link>
        </div>
      </nav>

      {/* ✅ Routes */}
      <Routes>
        <Route
          path="/"
          element={
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
          }
        />
        <Route path="/upload" element={<FileUpload />} />


        <Route path="/documents" element={<WaiverTable />} />
      </Routes>
    </Router>
  )
}