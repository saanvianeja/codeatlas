import { useState } from 'react'
import type { AnalysisResult } from './types'
import RepoAnalyzer from './components/RepoAnalyzer'
import StatsCards from './components/StatsCards'
import DependencyGraph from './components/DependencyGraph'
import RepositoryFiles from './components/RepositoryFiles'
import SemanticSearch from './components/SemanticSearch'

function errorMessage(data: unknown, fallback: string) {
  if (
    typeof data === 'object' &&
    data !== null &&
    'detail' in data &&
    typeof data.detail === 'string'
  ) {
    return data.detail
  }
  return fallback
}

function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedModule, setSelectedModule] = useState<string | null>(null)
  const [affectedModules, setAffectedModules] = useState<string[]>([])

  function findAffectedModules(moduleName: string) {
    if (!result) return

    const queue = [moduleName]
    const visited = new Set<string>([moduleName])
    const affected: string[] = []

    while (queue.length > 0) {
      const current = queue.shift()

      if (!current) continue

      for (const dependency of result.dependencies) {
        const source = dependency.source
        const target = dependency.target

        if (target === current && !visited.has(source)) {
          visited.add(source)
          affected.push(source)
          queue.push(source)
        }
      }
    }

    setSelectedModule(moduleName)
    setAffectedModules(affected)
  }

  async function analyzeRepo() {
    setLoading(true)
    setError('')
    try {
      const response = await fetch('http://localhost:8000/analyses', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ repo_url: repoUrl }),
      })
      const data: unknown = await response.json()
      if (!response.ok) {
        throw new Error(errorMessage(data, 'Analysis failed'))
      }
      setResult(data as AnalysisResult)
      setSelectedModule(null)
      setAffectedModules([])
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Analysis failed')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="mb-10">
          <div className="mb-3 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500 font-bold text-white">
              C
            </div>

            <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
              CodeAtlas
            </h1>
          </div>

          <p className="text-slate-400">
            Explore repository structure, dependencies, and code relationships.
          </p>
        </div>

        <RepoAnalyzer
          repoUrl={repoUrl}
          loading={loading}
          error={error}
          onRepoUrlChange={setRepoUrl}
          onAnalyze={analyzeRepo}
        />

        {result && (
          <>
            <StatsCards files={result.files} />
            <DependencyGraph
              dependencies={result.dependencies}
              selectedModule={selectedModule}
              affectedModules={affectedModules}
              onSelectModule={findAffectedModules}
            />
            <RepositoryFiles files={result.files} />
          </>
        )}

        <SemanticSearch analysisId={result?.analysis_id ?? null} />
      </div>
    </main>
  )
}

export default App
