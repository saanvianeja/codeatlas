import { useState } from 'react'
import type { AnalysisResult, ImpactResult } from './types'
import { API_BASE, errorMessage } from './api'
import RepoAnalyzer from './components/RepoAnalyzer'
import StatsCards from './components/StatsCards'
import DependencyGraph from './components/DependencyGraph'
import RepositoryFiles from './components/RepositoryFiles'
import SemanticSearch from './components/SemanticSearch'
import AskCodeAtlas from './components/AskCodeAtlas'

function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [impact, setImpact] = useState<ImpactResult | null>(null)
  const [impactLoading, setImpactLoading] = useState(false)
  const [impactError, setImpactError] = useState('')

  async function loadImpact(filePath: string) {
    if (!result) return

    setImpactLoading(true)
    setImpactError('')
    try {
      const params = new URLSearchParams({ file: filePath })
      const response = await fetch(
        `${API_BASE}/analyses/${result.analysis_id}/impact?${params.toString()}`
      )
      const data: unknown = await response.json()
      if (!response.ok) {
        throw new Error(errorMessage(data, 'Impact analysis failed'))
      }
      setImpact(data as ImpactResult)
    } catch (err) {
      setImpact(null)
      setImpactError(
        err instanceof Error ? err.message : 'Impact analysis failed'
      )
    } finally {
      setImpactLoading(false)
    }
  }

  async function analyzeRepo() {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE}/analyses`, {
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
      setImpact(null)
      setImpactError('')
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
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8 lg:py-12">
        <header className="mb-8 border-b border-slate-800 pb-8 sm:mb-10">
          <div className="flex items-start gap-3 sm:items-center">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-500 text-sm font-bold text-white">
              CA
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight sm:text-3xl md:text-4xl">
                CodeAtlas
              </h1>
              <p className="mt-1.5 max-w-2xl text-sm leading-6 text-slate-400 sm:text-base">
                Map a Python GitHub repository: static structure, import impact,
                semantic retrieval, and grounded answers with file and line citations.
              </p>
            </div>
          </div>
        </header>

        <RepoAnalyzer
          repoUrl={repoUrl}
          loading={loading}
          error={error}
          onRepoUrlChange={setRepoUrl}
          onAnalyze={analyzeRepo}
        />

        {loading && (
          <div className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 px-5 py-8 text-sm text-slate-400">
            Cloning the repository and running AST analysis. Large repos may take
            a minute.
          </div>
        )}

        {!result && !loading && (
          <div className="mb-8 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="text-sm font-medium text-slate-200">Structure</p>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                Symbols, files, and a path-based internal import graph.
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="text-sm font-medium text-slate-200">Semantic Search</p>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                Retrieved functions and classes with source snippets. No generated text.
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="text-sm font-medium text-slate-200">Ask CodeAtlas</p>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                An LLM explanation grounded in those retrieved symbols.
              </p>
            </div>
          </div>
        )}

        {result && (
          <>
            <StatsCards repoUrl={result.repo_url} files={result.files} />
            <DependencyGraph
              files={result.files}
              dependencies={result.dependencies}
              impact={impact}
              impactLoading={impactLoading}
              impactError={impactError}
              onSelectFile={loadImpact}
            />
            <RepositoryFiles files={result.files} />
          </>
        )}

        <div className="mt-8 space-y-6">
          <SemanticSearch analysisId={result?.analysis_id ?? null} />
          <AskCodeAtlas analysisId={result?.analysis_id ?? null} />
        </div>
      </div>
    </main>
  )
}

export default App
