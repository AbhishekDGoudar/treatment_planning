"use client"

import ForceGraph2D from "react-force-graph-2d"

/* =========================
   Types (matches backend)
   ========================= */

export type GraphNode = {
  id: string
  type: "Country" | "State" | "Waiver" | "Theme"
  title?: string
  state?: string
  score?: number
  value?: string
}

export type GraphEdge = {
  from: string
  to: string
  type: "HAS_STATE" | "HAS_APPLICATION" | "HAS_THEME"
}

export type GraphData = {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

/* =========================
   Transform for ForceGraph
   ========================= */

function toForceGraph(graph: GraphData) {
  return {
    nodes: graph.nodes.map(n => ({
      ...n,
      val:
        n.type === "Country" ? 14 :
        n.type === "State"   ? 12 :
        n.type === "Waiver"  ? 10 + (n.score ?? 0) * 12 :
                               6
    })),
    links: graph.edges.map(e => ({
      source: e.from,
      target: e.to,
      type: e.type
    }))
  }
}

/* =========================
   Graph Component
   ========================= */

export default function GraphView({ graph }: { graph?: GraphData }) {
  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="p-4 rounded-2xl border bg-white text-sm text-gray-500">
        Graph will appear here.
      </div>
    )
  }

  const data = toForceGraph(graph)

  return (
    <div className="p-4 rounded-2xl border bg-white h-[460px]">
      <ForceGraph2D
        graphData={data}

        /* ---------- Layout ---------- */
        dagMode="lr"
        dagLevelDistance={130}
        cooldownTicks={120}
        d3VelocityDecay={0.35}

        /* ---------- Nodes ---------- */
        nodeAutoColorBy="type"
        nodeLabel={(n: any) => {
          switch (n.type) {
            case "Country":
              return `Country: ${n.id}`
            case "State":
              return `State: ${n.id}`
            case "Waiver":
              return `${n.title}\nState: ${n.state}`
            case "Theme":
              return `${n.id}${n.value ? ` (${n.value})` : ""}`
            default:
              return n.id
          }
        }}

        /* ---------- Links ---------- */
        linkDirectionalArrowLength={6}
        linkDirectionalArrowRelPos={1}
        linkLabel={(l: any) => l.type}
        linkColor={(l: any) =>
          l.type === "HAS_THEME"
            ? "#10b981" // green
            : l.type === "HAS_APPLICATION"
            ? "#6366f1" // indigo
            : "#94a3b8" // gray
        }

        /* ---------- Canvas ---------- */
        height={420}
      />
    </div>
  )
}
