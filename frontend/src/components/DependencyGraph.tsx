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
import type { Dependency, FileInfo, ImpactResult } from '../types'

import '@xyflow/react/dist/style.css'

const NODE_HEIGHT = 48
const MIN_NODE_WIDTH = 140
const MAX_NODE_WIDTH = 360

type DependencyGraphProps = {
  files: FileInfo[]
  dependencies: Dependency[]
  impact: ImpactResult | null
  impactLoading: boolean
  impactError: string
  onSelectFile: (filePath: string) => void
}

function nodeWidthForLabel(label: string) {
  return Math.min(MAX_NODE_WIDTH, Math.max(MIN_NODE_WIDTH, 32 + label.length * 8))
}

function layoutGraph(
  files: FileInfo[],
  dependencies: Dependency[],
  impact: ImpactResult | null
): { nodes: Node[]; edges: Edge[] } {
  const moduleNames = new Set<string>()

  for (const file of files) {
    moduleNames.add(file.file)
  }

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

  const modules = Array.from(moduleNames).sort()

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

  const selected = impact?.selected_file ?? null
  const directSet = new Set(impact?.direct_dependents ?? [])
  const transitiveSet = new Set(impact?.transitive_dependents ?? [])
  const impactedSet = new Set(impact?.all_impacted_files ?? [])

  const nodes: Node[] = modules.map((moduleName) => {
    const layoutNode = graph.node(moduleName)
    const width = nodeWidthForLabel(moduleName)
    const isSelected = selected === moduleName
    const isDirect = directSet.has(moduleName)
    const isTransitive = transitiveSet.has(moduleName)
    const isUnrelated = selected !== null && !isSelected && !isDirect && !isTransitive

    let background = '#e2e8f0'
    let border = '1px solid #94a3b8'
    let color = '#0f172a'
    let opacity = 1

    if (isSelected) {
      background = '#6366f1'
      border = '2px solid #a5b4fc'
      color = '#f8fafc'
    } else if (isDirect) {
      background = '#312e81'
      border = '2px solid #818cf8'
      color = '#e0e7ff'
    } else if (isTransitive) {
      background = '#1e293b'
      border = '2px solid #64748b'
      color = '#cbd5e1'
    } else if (isUnrelated) {
      opacity = 0.4
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
        fontSize: 12,
        borderRadius: 8,
        background,
        border,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        opacity,
      },
    }
  })

  const edges: Edge[] = dependencies.map((dependency, index) => {
    const highlighted =
      selected !== null &&
      (dependency.source === selected ||
        dependency.target === selected ||
        impactedSet.has(dependency.source) ||
        impactedSet.has(dependency.target))

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
        opacity: selected !== null && !highlighted ? 0.25 : 1,
      },
    }
  })

  return { nodes, edges }
}

export default function DependencyGraph({
  files,
  dependencies,
  impact,
  impactLoading,
  impactError,
  onSelectFile,
}: DependencyGraphProps) {
  const { nodes, edges } = useMemo(
    () => layoutGraph(files, dependencies, impact),
    [files, dependencies, impact]
  )

  const graphKey = useMemo(
    () =>
      [
        ...files.map((file) => file.file),
        ...dependencies.map(
          (dependency) => `${dependency.source}>${dependency.target}`
        ),
      ].join('|'),
    [files, dependencies]
  )

  return (
    <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-5 sm:p-6">
      <div className="mb-5">
        <h2 className="text-lg font-semibold tracking-tight sm:text-xl">
          Dependency graph
        </h2>
        <p className="mt-1.5 max-w-3xl text-sm leading-6 text-slate-400">
          An edge from A to B means A imports B. Select a file for server-side
          BFS potential-impact: files that would be affected if this module
          changed.
        </p>
      </div>

      {files.length === 0 ? (
        <p className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-8 text-sm text-slate-500">
          No Python files were found in this repository.
        </p>
      ) : (
        <>
        {dependencies.length === 0 && (
          <p className="mb-4 rounded-lg border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-500">
            No internal import edges were resolved. Isolated files still appear as nodes.
          </p>
        )}
        <div className="flex flex-col gap-4 lg:flex-row">
          <div className="h-[420px] min-h-[280px] min-w-0 flex-1 overflow-hidden rounded-xl border border-slate-700 bg-slate-950 sm:h-[520px]">
            <ReactFlow
              key={graphKey}
              nodes={nodes}
              edges={edges}
              fitView
              fitViewOptions={{ padding: 0.24, minZoom: 0.2, maxZoom: 1.25 }}
              minZoom={0.15}
              maxZoom={1.5}
              nodesConnectable={false}
              onNodeClick={(_, node) => onSelectFile(node.id)}
            >
              <Background color="#334155" gap={18} />
              <Controls />
            </ReactFlow>
          </div>

          <aside className="flex w-full shrink-0 flex-col rounded-xl border border-slate-800 bg-slate-950 p-4 lg:w-80">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Potential downstream impact
            </p>

            {impactLoading && (
              <p className="mt-3 text-sm text-slate-400">Calculating dependents…</p>
            )}

            {impactError && (
              <p className="mt-3 rounded-lg border border-red-900 bg-red-950/40 px-3 py-2 text-sm text-red-300">
                {impactError}
              </p>
            )}

            {!impactLoading && !impactError && impact ? (
              <>
                <h3 className="mt-2 text-sm font-semibold leading-6">
                  Selected:{' '}
                  <span className="font-mono text-indigo-400">
                    {impact.selected_file}
                  </span>
                </h3>

                <div className="mt-4 grid grid-cols-2 gap-2">
                  <div className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2">
                    <p className="text-[11px] uppercase tracking-wide text-slate-500">
                      Direct dependents
                    </p>
                    <p className="mt-1 text-xl font-semibold">
                      {impact.direct_dependents.length}
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2">
                    <p className="text-[11px] uppercase tracking-wide text-slate-500">
                      Total downstream
                    </p>
                    <p className="mt-1 text-xl font-semibold">
                      {impact.total_impacted}
                    </p>
                  </div>
                </div>

                {impact.total_impacted > 0 ? (
                  <ul className="mt-3 flex max-h-[300px] flex-col gap-2 overflow-y-auto">
                    {impact.all_impacted_files.map((filePath) => (
                      <li
                        key={filePath}
                        className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 font-mono text-sm text-slate-200"
                      >
                        <span className="block truncate">{filePath}</span>
                        <span className="text-xs text-slate-500">
                          distance {impact.distances[filePath]}
                          {impact.distances[filePath] === 1
                            ? ' · direct'
                            : ' · transitive'}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-4 rounded-lg border border-slate-800 bg-slate-900 px-3 py-4 text-sm text-slate-500">
                    No other files import this file, directly or transitively.
                  </p>
                )}
              </>
            ) : (
              !impactLoading &&
              !impactError && (
                <p className="mt-3 text-sm leading-6 text-slate-500">
                  Select a file in the graph to see potential downstream
                  dependents.
                </p>
              )
            )}

            <div className="mt-auto flex flex-col gap-2 pt-6 text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-indigo-500" />
                Selected
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-indigo-900 ring-1 ring-indigo-400" />
                Direct dependent
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-slate-800 ring-1 ring-slate-500" />
                Transitive dependent
              </span>
            </div>
          </aside>
        </div>
        </>
      )}
    </section>
  )
}
