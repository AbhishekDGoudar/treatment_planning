import React from 'react'

interface Props {
  plan: any
}

export default function PlanVisualizer({ plan }: Props) {
  if (!plan) return <div className="p-4 text-neutral-400 italic">Run "Explain" to see the execution plan.</div>

  // If plan is an array of steps, render them nicely
  if (Array.isArray(plan)) {
    return (
      <div className="p-4 rounded-2xl border bg-slate-50 space-y-3">
        <h3 className="font-semibold text-slate-700 border-b pb-2">Execution Plan</h3>
        <div className="space-y-2">
          {plan.map((step: any, idx: number) => (
            <div key={idx} className="flex gap-3 p-3 bg-white border border-slate-200 rounded-lg shadow-sm">
              <div className="font-mono text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded self-start">
                Step {idx + 1}
              </div>
              <div className="text-sm text-slate-800">
                {typeof step === 'string' ? step : JSON.stringify(step)}
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // Fallback: JSON Dump for debugging
  return (
    <div className="p-4 rounded-2xl border bg-slate-50 font-mono text-sm overflow-auto">
      <h3 className="font-bold text-slate-700 mb-2">Execution Plan (Raw)</h3>
      <pre className="whitespace-pre-wrap text-slate-600">{JSON.stringify(plan, null, 2)}</pre>
    </div>
  )
}