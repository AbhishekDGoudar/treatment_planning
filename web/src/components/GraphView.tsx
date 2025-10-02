import ForceGraph2D from 'react-force-graph-2d'

function toGraph(raw: any[]){
  const nodes: any[] = []
  const links: any[] = []
  const byId = new Map<string, any>()
  for(const row of raw){
    const d = row.d?.properties || row["d"]?.properties || row["d"]
    const n = row.n?.properties || row["n"]?.properties || row["n"]
    if(d){
      const nid = d.path
      if(!byId.has(nid)){ byId.set(nid, { id: nid, label: 'Document' }); nodes.push(byId.get(nid)) }
    }
    if(n){
      const nid = Object.values(n)[0] as string
      const label = Object.keys(n)[0]
      if(!byId.has(nid)){ byId.set(nid, { id: nid, label }); nodes.push(byId.get(nid)) }
    }
    if(d && n){
      links.push({ source: d.path, target: Object.values(n)[0] })
    }
  }
  return { nodes, links }
}

export default function GraphView({ raw }: { raw: any[] }){
  if(!raw?.length) return <div className="p-4 rounded-2xl border bg-white">Graph will appear here.</div>
  const data = toGraph(raw)
  return (
    <div className="p-4 rounded-2xl border bg-white h-[420px]">
      <ForceGraph2D graphData={data} nodeLabel={(n:any)=>n.id} width={undefined} height={400} />
    </div>
  )
}
