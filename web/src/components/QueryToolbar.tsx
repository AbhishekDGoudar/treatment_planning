import React from 'react'

interface Props {
  onExecute: () => void
  onExplain: () => void
  isLoading: boolean
}

export default function QueryToolbar({ onExecute, onExplain, isLoading }: Props) {
  return (
    <div className="flex items-center gap-3 pt-2">
      {/* Primary Action: EXECUTE */}
      <button
        onClick={onExecute}
        disabled={isLoading}
        className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded shadow-sm transition-all disabled:opacity-50"
      >
        {/* Play Icon SVG */}
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
        <span>Run Query</span>
      </button>

      {/* Secondary Action: EXPLAIN / PLAN */}
      <button
        onClick={onExplain}
        disabled={isLoading}
        className="flex items-center gap-2 px-4 py-2 text-neutral-700 bg-neutral-100 hover:bg-neutral-200 border border-neutral-300 rounded transition-all disabled:opacity-50"
        title="Check processing steps without generating full answer"
      >
        {/* Search/Inspect Icon SVG */}
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <span>Explain Plan</span>
      </button>

      {isLoading && <span className="text-sm text-neutral-500 animate-pulse">Processing...</span>}
    </div>
  )
}