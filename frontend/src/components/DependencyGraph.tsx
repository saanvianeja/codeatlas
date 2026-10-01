import { useMemo } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  type Edge,
  type Node,
} from '@xyflow/react'
import dagre from '@dagrejs/dagre'
import type { Dependency } from '../types'

import '@xyflow/react/dist/style.css'

const NODE_HEIGHT = 48
const MIN_NODE_WIDTH = 140
const MAX_NODE_WIDTH = 280

type DependencyGraphProps = {
  dependencies: Dependency[]
  selectedModule: string | null
  affectedModules: string[]
  onSelectModule: (moduleName: string) => void
}

function nodeWidthForLabel(label: string) {
  return Math.min(MAX_NODE_WIDTH, Math.max(MIN_NODE_WIDTH, 32 + label.length * 8))
}

function layoutGraph(
  dependencies: Dependency[],
  selectedModule: string | null,
  affectedSet: Set<string>
): { nodes: Node[]; edges: Edge[] } {
  const moduleNames = new Set<string>()

  for (const dependency of dependencies) {
    moduleNames.add(dependency.source)
    moduleNames.add(dependency.target)
  }

  const graph = new dagre.graphlib.Graph()
  graph.setDefaultEdgeLabel(() => ({}))
  graph.setGraph({
    rankdir: 'LR',
    nodesep: 48,
    ranksep: 88,
    marginx: 24,
    marginy: 24,
  })

  const modules = Array.from(moduleNames)

  for (const moduleName of modules) {
    graph.setNode(moduleName, {
      width: nodeWidthForLabel(moduleName),
      height: NODE_HEIGHT,
    })
  }

  dependencies.forEach((dependency, index) => {
    graph.setEdge(dependency.source, dependency.target, { id: `edge-${index}` })
  })

  dagre.layout(graph)

  const nodes: Node[] = modules.map((moduleName) => {
    const layoutNode = graph.node(moduleName)
    const width = nodeWidthForLabel(moduleName)
    const isSelected = selectedModule === moduleName
    const isAffected = affectedSet.has(moduleName)

    let background = '#e2e8f0'
    let border = '1px solid #94a3b8'
    let color = '#0f172a'

    if (isSelected) {
      background = '#6366f1'
      border = '2px solid #a5b4fc'
      color = '#f8fafc'
    } else if (isAffected) {
      background = '#312e81'
      border = '2px solid #818cf8'
      color = '#e0e7ff'
    }

    return {
      id: moduleName,
      position: {
        x: layoutNode.x - width / 2,
        y: layoutNode.y - NODE_HEIGHT / 2,
      },
      data: {
        label: moduleName,
      },
      style: {
        width,
        height: NODE_HEIGHT,
        color,
        fontWeight: 600,
        fontSize: 13,
        borderRadius: 8,
        background,
        border,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      },
    }
  })

  const edges: Edge[] = dependencies.map((dependency, index) => {
    const highlighted =
      selectedModule !== null &&
      (dependency.source === selectedModule ||
        dependency.target === selectedModule ||
        affectedSet.has(dependency.source) ||
        affectedSet.has(dependency.target))

    return {
      id: `edge-${index}`,
      source: dependency.source,
      target: dependency.target,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 16,
        height: 16,
        color: highlighted ? '#818cf8' : '#64748b',
      },
      style: {
        stroke: highlighted ? '#818cf8' : '#64748b',
        strokeWidth: highlighted ? 2 : 1.25,
      },
    }
  })

  return { nodes, edges }
}

export default function DependencyGraph({
  dependencies,
  selectedModule,
  affectedModules,
  onSelectModule,
}: DependencyGraphProps) {
  const affectedSet = useMemo(() => new Set(affectedModules), [affectedModules])

  const { nodes, edges } = useMemo(
    () => layoutGraph(dependencies, selectedModule, affectedSet),
    [dependencies, selectedModule, affectedSet]
  )

  const graphKey = useMemo(
    () =>
      dependencies
        .map((dependency) => `${dependency.source}>${dependency.target}`)
        .join('|'),
    [dependencies]
  )

  return (
    <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-5">
        <h2 className="text-xl font-semibold">Dependency Graph</h2>
        <p className="mt-1 text-sm text-slate-400">
          Visualize relationships between modules in the repository. An edge
          from A to B means A depends on B.
        </p>
      </div>

      {dependencies.length === 0 ? (
        <p className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-8 text-sm text-slate-500">
          No module dependencies were found in this repository.
        </p>
      ) : (
        <div className="flex flex-col gap-4 lg:flex-row">
          <div className="h-[520px] min-h-[360px] min-w-0 flex-1 overflow-hidden rounded-xl border border-slate-700 bg-slate-950">
            <ReactFlow
              key={graphKey}
              nodes={nodes}
              edges={edges}
              fitView
              fitViewOptions={{ padding: 0.24, minZoom: 0.2, maxZoom: 1.25 }}
              minZoom={0.15}
              maxZoom={1.5}
              nodesConnectable={false}
              onNodeClick={(_, node) => onSelectModule(node.id)}
            >
              <Background color="#334155" gap={18} />
              <Controls />
            </ReactFlow>
          </div>

          <aside className="flex w-full shrink-0 flex-col rounded-xl border border-slate-800 bg-slate-950 p-4 lg:w-80">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Impact analysis
            </p>

            {selectedModule ? (
              <>
                <h3 className="mt-2 text-base font-semibold leading-6">
                  If{' '}
                  <span className="text-indigo-400">{selectedModule}</span>{' '}
                  changes
                </h3>

                <p className="mt-3 text-sm text-slate-400">
                  {affectedModules.length} affected module
                  {affectedModules.length === 1 ? '' : 's'}
                </p>

                {affectedModules.length > 0 ? (
                  <ul className="mt-3 flex max-h-[380px] flex-col gap-2 overflow-y-auto">
                    {affectedModules.map((moduleName) => (
                      <li
                        key={moduleName}
                        className="rounded-lg border border-indigo-500/20 bg-indigo-500/10 px-3 py-2 font-mono text-sm text-indigo-200"
                      >
                        {moduleName}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-4 rounded-lg border border-slate-800 bg-slate-900 px-3 py-4 text-sm text-slate-500">
                    No other modules depend on this module.
                  </p>
                )}
              </>
            ) : (
              <p className="mt-3 text-sm leading-6 text-slate-500">
                Select a module in the graph to see which modules would be
                affected by a change.
              </p>
            )}

            <div className="mt-auto hidden gap-4 pt-6 text-xs text-slate-500 lg:flex">
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-indigo-500" />
                Selected
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-indigo-900 ring-1 ring-indigo-400" />
                Affected
              </span>
            </div>
          </aside>
        </div>
      )}
    </section>
  )
}
