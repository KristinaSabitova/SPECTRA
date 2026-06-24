import { useEffect, useRef, useCallback } from 'react'
import * as d3 from 'd3'
import { useTranslation } from 'react-i18next'
import DOMPurify from 'dompurify'
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react'
import type { BlastRadiusDetail, GraphNodeDetail } from '@/types'

// ── Node type colors ──────────────────────────────────────────────────

const TYPE_COLOR: Record<string, string> = {
  endpoint:    '#3B82F6',
  entry:       '#3B82F6',
  llm:         '#8B5CF6',
  agent:       '#6366F1',
  coordinator: '#6366F1',
  database:    '#EF4444',
  sql:         '#EF4444',
  postgres:    '#EF4444',
  shell:       '#DC2626',
  exec:        '#DC2626',
  bash:        '#DC2626',
  email:       '#F97316',
  smtp:        '#F97316',
  filesystem:  '#EAB308',
  file:        '#CA8A04',
  search:      '#10B981',
  retriever:   '#059669',
  memory:      '#A855F7',
  vector:      '#9333EA',
  http:        '#0EA5E9',
  api:         '#0284C7',
  browser:     '#0EA5E9',
  capability:  '#64748B',
  tool:        '#94A3B8',
  unknown:     '#CBD5E1',
}

function nodeColor(type: string): string {
  const ltype = type.toLowerCase()
  if (ltype in TYPE_COLOR) return TYPE_COLOR[ltype]
  for (const [key, color] of Object.entries(TYPE_COLOR)) {
    if (ltype.includes(key)) return color
  }
  return TYPE_COLOR.unknown
}

// ── D3 types ──────────────────────────────────────────────────────────

interface D3Node extends d3.SimulationNodeDatum, GraphNodeDetail {
  isEntry?: boolean
}

interface D3Link extends d3.SimulationLinkDatum<D3Node> {
  source: string | D3Node
  target: string | D3Node
}

// ── Helpers ───────────────────────────────────────────────────────────

function buildGraphData(detail: BlastRadiusDetail): { nodes: D3Node[]; links: D3Link[] } {
  const nodeMap = new Map<string, D3Node>()

  // Entry node (not in node_details)
  const entryNode: D3Node = {
    id: detail.entry_node,
    label: 'Entry',
    type: 'entry',
    criticality: 0.5,
    depth: 0,
    isEntry: true,
  }
  nodeMap.set(entryNode.id, entryNode)

  for (const n of detail.node_details) {
    nodeMap.set(n.id, { ...n })
  }

  const nodes = Array.from(nodeMap.values())

  // Build links
  let links: D3Link[] = []
  if (detail.edges && detail.edges.length > 0) {
    links = detail.edges.map(e => ({ source: e.src, target: e.dst }))
  } else {
    // Reconstruct from depth
    const byDepth = new Map<number, D3Node[]>()
    for (const n of nodes) {
      const d = n.depth ?? 0
      byDepth.set(d, [...(byDepth.get(d) ?? []), n])
    }
    const depth1 = byDepth.get(1) ?? []
    for (const n of depth1) {
      links.push({ source: detail.entry_node, target: n.id })
    }
    const llmNode = nodes.find(n => n.type === 'llm' || n.id === 'llm')
    const hub = llmNode ?? depth1[0]
    for (let d = 2; d <= 8; d++) {
      for (const n of (byDepth.get(d) ?? [])) {
        const parentDepth = byDepth.get(d - 1) ?? []
        const parent = hub?.depth === d - 1 ? hub : parentDepth[0]
        if (parent) links.push({ source: parent.id, target: n.id })
      }
    }
  }

  return { nodes, links }
}

// ── Component ─────────────────────────────────────────────────────────

interface Props {
  detail: BlastRadiusDetail | null
}

export default function EcosystemGraph({ detail }: Props) {
  const { t } = useTranslation()
  const svgRef  = useRef<SVGSVGElement>(null)
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)

  const zoomIn  = useCallback(() => { if (svgRef.current && zoomRef.current) d3.select(svgRef.current).transition().call(zoomRef.current.scaleBy, 1.4) }, [])
  const zoomOut = useCallback(() => { if (svgRef.current && zoomRef.current) d3.select(svgRef.current).transition().call(zoomRef.current.scaleBy, 0.7) }, [])
  const reset   = useCallback(() => { if (svgRef.current && zoomRef.current) d3.select(svgRef.current).transition().call(zoomRef.current.transform, d3.zoomIdentity) }, [])

  useEffect(() => {
    if (!detail || !svgRef.current) return

    const { nodes, links } = buildGraphData(detail)
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const rect = svgRef.current.getBoundingClientRect()
    const W = rect.width  || 600
    const H = rect.height || 400

    // Arrowhead marker
    const defs = svg.append('defs')
    defs.append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -4 8 8')
      .attr('refX', 18)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-4L8,0L0,4')
      .attr('fill', '#94A3B8')

    const container = svg.append('g')

    // Zoom behaviour
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on('zoom', (e) => container.attr('transform', e.transform))
    zoomRef.current = zoom
    svg.call(zoom)
    svg.call(zoom.transform, d3.zoomIdentity.translate(W / 2, H / 2))

    // Force simulation
    const sim = d3.forceSimulation<D3Node>(nodes)
      .force('link',   d3.forceLink<D3Node, D3Link>(links).id(d => d.id).distance(90).strength(0.7))
      .force('charge', d3.forceManyBody().strength(-280))
      .force('center', d3.forceCenter(0, 0))
      .force('collision', d3.forceCollide<D3Node>().radius(d => nodeRadius(d) + 10))

    // Links
    const link = container.append('g')
      .selectAll<SVGLineElement, D3Link>('line')
      .data(links)
      .join('line')
      .attr('stroke', '#CBD5E1')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#arrow)')

    // Node groups
    const nodeG = container.append('g')
      .selectAll<SVGGElement, D3Node>('g')
      .data(nodes)
      .join('g')
      .style('cursor', 'pointer')
      .call(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        d3.drag<SVGGElement, any>()
          .on('start', (ev, d) => { if (!ev.active) sim.alphaTarget(0.3).restart(); (d as D3Node).fx = (d as D3Node).x; (d as D3Node).fy = (d as D3Node).y })
          .on('drag',  (ev, d) => { (d as D3Node).fx = ev.x; (d as D3Node).fy = ev.y })
          .on('end',   (ev, d) => { if (!ev.active) sim.alphaTarget(0); (d as D3Node).fx = null; (d as D3Node).fy = null }),
      )

    // Node circles
    nodeG.append('circle')
      .attr('r', d => nodeRadius(d))
      .attr('fill', d => nodeColor(d.type))
      .attr('stroke', d => d.isEntry ? '#1D4ED8' : 'white')
      .attr('stroke-width', d => d.isEntry ? 2.5 : 1.5)
      .attr('opacity', 0.92)

    // Criticality ring for high-risk nodes
    nodeG.filter(d => d.criticality >= 0.8)
      .append('circle')
      .attr('r', d => nodeRadius(d) + 4)
      .attr('fill', 'none')
      .attr('stroke', d => nodeColor(d.type))
      .attr('stroke-width', 1)
      .attr('opacity', 0.35)

    // Labels
    nodeG.append('text')
      .attr('dy', d => nodeRadius(d) + 13)
      .attr('text-anchor', 'middle')
      .attr('font-size', 11)
      .attr('fill', '#475569')
      .attr('font-family', 'Inter, sans-serif')
      .text(d => truncate(d.label, 14))

    // Tooltip on hover
    const tooltip = d3.select('body').append('div')
      .attr('class', 'graph-tooltip')
      .style('opacity', 0)

    nodeG
      .on('mouseenter', (ev, d) => {
        tooltip
          .style('opacity', 1)
          .html(DOMPurify.sanitize(`
            <strong>${d.label}</strong><br/>
            ${t(`graph.nodeTypes.${d.type}`, d.type)}<br/>
            ${t('graph.criticality')}: ${(d.criticality * 100).toFixed(0)}%<br/>
            ${t('graph.depth')}: ${d.depth}
          `))
          .style('left', `${ev.pageX + 12}px`)
          .style('top', `${ev.pageY - 8}px`)
      })
      .on('mousemove', (ev) => {
        tooltip.style('left', `${ev.pageX + 12}px`).style('top', `${ev.pageY - 8}px`)
      })
      .on('mouseleave', () => tooltip.style('opacity', 0))

    sim.on('tick', () => {
      link
        .attr('x1', d => (d.source as D3Node).x ?? 0)
        .attr('y1', d => (d.source as D3Node).y ?? 0)
        .attr('x2', d => (d.target as D3Node).x ?? 0)
        .attr('y2', d => (d.target as D3Node).y ?? 0)
      nodeG.attr('transform', d => `translate(${d.x ?? 0},${d.y ?? 0})`)
    })

    return () => {
      sim.stop()
      tooltip.remove()
    }
  }, [detail, t])

  if (!detail || detail.node_details.length === 0) {
    return (
      <div className="graph-empty">
        <p className="graph-empty-title">{t('graph.noData')}</p>
        <p className="graph-empty-desc">{t('graph.noDataDesc')}</p>
      </div>
    )
  }

  return (
    <div className="graph-wrapper">
      <svg ref={svgRef} className="graph-svg" />
      <div className="graph-controls">
        <button className="graph-ctrl-btn" onClick={zoomIn}  title={t('graph.zoom.in')}>
          <ZoomIn size={14} />
        </button>
        <button className="graph-ctrl-btn" onClick={zoomOut} title={t('graph.zoom.out')}>
          <ZoomOut size={14} />
        </button>
        <button className="graph-ctrl-btn" onClick={reset}   title={t('graph.zoom.reset')}>
          <Maximize2 size={14} />
        </button>
      </div>
      <div className="graph-legend">
        {[
          { type: 'entry',    label: 'Entry'    },
          { type: 'llm',      label: 'LLM'      },
          { type: 'database', label: 'DB'        },
          { type: 'tool',     label: 'Tool'      },
          { type: 'email',    label: 'Email'     },
        ].map(({ type, label }) => (
          <span key={type} className="graph-legend-item">
            <span className="graph-legend-dot" style={{ background: nodeColor(type) }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}

function nodeRadius(d: D3Node): number {
  return 8 + d.criticality * 12
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}
