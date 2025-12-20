import React, { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { ask, explain } from './lib/api' // ✅ Import explain
import AskBox from './components/AskBox'
import AnswerPane from './components/AnswerPane'
import SourceList from './components/SourceList'
import GraphView from './components/GraphView'
import FileUpload from './components/FileUpload' 
import WaiverTable from './components/WaiverTable'
import PlanVisualizer from './components/PlanVisualizer'

export default function App() {
  const [answer, setAnswer] = useState<string>('')
  const [sources, setSources] = useState<any[]>([])
  const [graph, setGraph] = useState<any[]>([])
  const [plan, setPlan] = useState<any>(null)
  
  const [isLoading, setIsLoading] = useState(false)
  const [viewMode, setViewMode] = useState<'results' | 'plan'>('results')

  const handleExecute = async (query: string, filters?: any) => {
    setIsLoading(true)
    setViewMode('results')
    try {
      const res = await ask(query, filters)
      setAnswer(res.answer)
      setSources(res.sources)
      setGraph(res.graph)
    } catch (e) {
      console.error(e)
      setAnswer("Error executing query.")
    } finally {
      setIsLoading(false)
    }
  }

  // ✅ Updated Handler using real API
  const handleExplain = async (query: string, filters?: any) => {
    setIsLoading(true)
    setViewMode('plan')
    try {
      const res = await explain(query, filters)
      
      // The API returns { plan: "...", cypher_query: "...", ... }
      // We can pass the whole object or just the plan string to the visualizer
      setPlan(res) 
      
    } catch (e) {
      console.error(e)
      setPlan({ error: "Failed to fetch plan." })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Router>
      <nav className="bg-white shadow p-4 mb-4">
        <div className="max-w-6xl mx-auto flex gap-4">
          <Link to="/" className="text-blue-600 hover:underline">Multimodal RAG</Link>
          <Link to="/upload" className="text-blue-600 hover:underline">Upload File</Link>
          <Link to="/documents" className="text-blue-600 hover:underline">Waiver Table</Link>
        </div>
      </nav>

      <Routes>
        <Route
          path="/"
          element={
            <div className="min-h-screen bg-neutral-50 text-neutral-900">
              <div className="max-w-6xl mx-auto p-6 space-y-4">
                <h1 className="text-2xl font-bold">Multimodal RAG</h1>
                
                <AskBox 
                  onExecute={handleExecute} 
                  onExplain={handleExplain}
                  isLoading={isLoading}
                />

                <div className="grid md:grid-cols-3 gap-4">
                  <div className="md:col-span-2 space-y-3">
                    {/* Toggle View based on button clicked */}
                    {viewMode === 'results' ? (
                      <>
                        <AnswerPane answer={answer} />
                        <SourceList sources={sources} />
                      </>
                    ) : (
                      <PlanVisualizer plan={plan} />
                    )}
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