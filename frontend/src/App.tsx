import { useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge
} from '@xyflow/react'

import '@xyflow/react/dist/style.css'

type FileInfo = {
  file: string
  imports: string[]
  functions: string[]
  classes: string[]
}

type AnalysisResult = {
  files: FileInfo[]
  dependencies: string[][]
}

function App() {
  const [repo_url, setrepourl] = useState('')
  const [result, setresult] =  useState<AnalysisResult | null>(null)
  const [loading, setloading] = useState(false)
  const [error, seterror] = useState('')
  const [nodes, setNodes] = useState<Node[]>([])
  const [edges, setEdges] = useState<Edge[]>([])
  const [selectedModule, setSelectedModule] = useState<string | null>(null)
  const [affectedModules, setAffectedModules] = useState<string[]>([])

  function buildGraph(data: AnalysisResult) {
    const moduleNames = new Set<string>()
  
    for (const dependency of data.dependencies) {
      moduleNames.add(dependency[0])
      moduleNames.add(dependency[1])
    }
  
    const newNodes = Array.from(moduleNames).map((moduleName, index) => {
      return {
        id: moduleName,
        position: {
          x: 0,
          y: index * 100
        },
        data: {
          label: moduleName
        },
        style: {
          color: '#0f172a',
          fontWeight: 600,
          borderRadius: '8px'
        }
      }
    })
    
    console.log(newNodes)

    const newEdges = data.dependencies.map((dependency, index) => {
      return {
        id: `edge-${index}`,
        source: dependency[0],
        target: dependency[1]
      }
    })
    
    console.log(newEdges)
    setNodes(newNodes)
    setEdges(newEdges)
  }

  function findAffectedModules(moduleName: string) {
    if (!result) return
  
    const queue = [moduleName]
    const visited = new Set<string>([moduleName]) //starts with what is selected, set bc only once
    const affected: string[] = []
  
    while (queue.length > 0) { //as long as something is waiting to be visited 
      const current = queue.shift() //removes the first item in the front, FIFO
  
      if (!current) continue
  
      for (const dependency of result.dependencies) {
        const source = dependency[0]
        const target = dependency[1]
  
        if (target === current && !visited.has(source)) {
          visited.add(source) //dont discover again, already visited
          affected.push(source) //part of final answer
          queue.push(source) //something could depend on this, need to investigate
        }
      }
    }
  
    setSelectedModule(moduleName)
    setAffectedModules(affected)
  }

  async function analyzeRepo(){
    setloading(true)
    seterror('')
    try{
      const response = await fetch("http://localhost:8000/analyze", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({repo_url})
      })
      if (!response.ok) {
        throw new Error("Analysis failed")
      }
      const data = await response.json()
      setresult(data)
      buildGraph(data)
      console.log(data)
    }
    catch(err){
      if (err instanceof Error){
        seterror(err.message)
      }
      else{
        seterror("Analysis failed")
      }
    }
    finally{
      setloading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-6 py-12">
  
        {/* Header */}
        <div className="mb-10">
          <div className="mb-3 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500 font-bold text-white">
              C
            </div>
  
            <h1 className="text-4xl font-bold tracking-tight">
              CodeAtlas
            </h1>
          </div>
  
          <p className="text-slate-400">
            Explore repository structure, dependencies, and code relationships.
          </p>
        </div>
  
        {/* Repository Input */}
        <div className="mb-8 flex gap-3">
          <input
            type="text"
            value={repo_url}
            onChange={(event) => setrepourl(event.target.value)}
            placeholder="https://github.com/user/repo"
            className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
          />
  
          <button
            onClick={analyzeRepo}
            disabled={loading}
            className="rounded-xl bg-indigo-500 px-6 py-3 font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Analyzing..." : "Analyze"}
          </button>
        </div>
  
        {error && (
          <div className="mb-6 rounded-xl border border-red-900 bg-red-950/40 px-4 py-3 text-red-300">
            {error}
          </div>
        )}
  
        {result && (
          <>
            {/* Stats */}
            <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
  
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <p className="text-sm text-slate-400">Files</p>
                <p className="mt-2 text-3xl font-bold">
                  {result.files.length}
                </p>
              </div>
  
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <p className="text-sm text-slate-400">Functions</p>
                <p className="mt-2 text-3xl font-bold">
                  {result.files.reduce(
                    (sum, file) => sum + file.functions.length,
                    0
                  )}
                </p>
              </div>
  
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <p className="text-sm text-slate-400">Classes</p>
                <p className="mt-2 text-3xl font-bold">
                  {result.files.reduce(
                    (sum, file) => sum + file.classes.length,
                    0
                  )}
                </p>
              </div>
  
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <p className="text-sm text-slate-400">Imports</p>
                <p className="mt-2 text-3xl font-bold">
                  {result.files.reduce(
                    (sum, file) => sum + file.imports.length,
                    0
                  )}
                </p>
              </div>
  
            </div>
  
            {/* Dependency Graph */}
            <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
              <div className="mb-5">
                <h2 className="text-xl font-semibold">
                  Dependency Graph
                </h2>
  
                <p className="mt-1 text-sm text-slate-400">
                  Visualize relationships between modules in the repository.
                </p>
              </div>
  
              <div className="h-[500px] overflow-hidden rounded-xl border border-slate-700 bg-slate-200">
              <ReactFlow
                nodes={nodes}
                edges={edges}
                fitView
                onNodeClick={(_, node) => findAffectedModules(node.id)}
              >
                {selectedModule && (
                  <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-4">
                    <p className="text-sm text-slate-400">
                      Impact analysis
                    </p>

                    <h3 className="mt-1 font-semibold">
                      If <span className="text-indigo-400">{selectedModule}</span> changes:
                    </h3>

                    {affectedModules.length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {affectedModules.map((module) => (
                          <span
                            key={module}
                            className="rounded-lg bg-indigo-500/10 px-3 py-1 text-sm text-indigo-300"
                          >
                            {module}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-3 text-sm text-slate-500">
                        No dependent modules found.
                      </p>
                    )}
                  </div>
                )}
                  <Background />
                  <Controls />
                </ReactFlow>
              </div>
            </section>
  
            {/* Files */}
            <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
              <div className="mb-5">
                <h2 className="text-xl font-semibold">
                  Repository Files
                </h2>
  
                <p className="mt-1 text-sm text-slate-400">
                  Python files discovered during analysis.
                </p>
              </div>
  
              <div className="grid gap-2">
                {result.files.map((fileinfo) => (
                  <div
                    key={fileinfo.file}
                    className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-4 py-3"
                  >
                    <span className="font-mono text-sm text-slate-300">
                      {fileinfo.file}
                    </span>
  
                    <span className="text-xs text-slate-500">
                      {fileinfo.functions.length} functions
                    </span>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  )
}
export default App