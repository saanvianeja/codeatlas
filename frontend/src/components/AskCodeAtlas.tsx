import { useEffect, useState } from 'react'
import type { AskResult } from '../types'
import { API_BASE, errorMessage } from '../api'
import Section from './Section'

type AskCodeAtlasProps = {
  analysisId: string | null
}

export default function AskCodeAtlas({ analysisId }: AskCodeAtlasProps) {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<AskResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setResult(null)
    setError('')
  }, [analysisId])

  async function ask() {
    if (!question.trim() || !analysisId) return

    setLoading(true)
    setError('')
    try {
      const response = await fetch(
        `${API_BASE}/analyses/${analysisId}/ask`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question }),
        }
      )
      const data: unknown = await response.json()
      if (!response.ok) {
        throw new Error(errorMessage(data, 'Ask failed'))
      }
      setResult(data as AskResult)
    } catch (err) {
      setResult(null)
      setError(err instanceof Error ? err.message : 'Ask failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Section
      className="mt-0"
      kicker="Generated explanation"
      title="Ask CodeAtlas"
      description="Retrieves the same top symbols as Semantic Search, adds a few import edges, and asks an LLM to answer only from that context. Citations use [file.py:L10-L25]."
    >
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              ask()
            }
          }}
          placeholder={
            analysisId
              ? 'e.g. How does repository cloning work?'
              : 'Analyze a repository to ask questions'
          }
          disabled={!analysisId}
          className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-50"
        />
        <button
          onClick={ask}
          disabled={!analysisId || loading || !question.trim()}
          className="rounded-xl bg-indigo-500 px-6 py-3 font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? 'Asking…' : 'Ask'}
        </button>
      </div>

      {!analysisId && (
        <p className="mt-4 text-sm text-slate-500">
          Requires an analyzed repository and{' '}
          <span className="font-mono text-slate-400">CODEATLAS_LLM_API_KEY</span>{' '}
          on the server.
        </p>
      )}

      {error && (
        <div className="mt-4 rounded-xl border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {loading && (
        <p className="mt-4 text-sm text-slate-400">
          Retrieving symbols and generating a grounded answer…
        </p>
      )}

      {result && (
        <div className="mt-6 space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm leading-6 whitespace-pre-wrap text-slate-200 sm:p-5">
            {result.answer}
          </div>
          {result.sources.length > 0 ? (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Sources
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                {result.sources.map((source) => (
                  <div
                    key={`${source.file}-${source.qualified_name}-${source.start_line}`}
                    className="rounded-lg border border-slate-800 bg-slate-950 px-4 py-3"
                  >
                    <p className="font-mono text-sm text-slate-200">
                      {source.qualified_name}
                    </p>
                    <p className="mt-1 font-mono text-xs text-slate-500">
                      {source.file} · lines {source.start_line}–{source.end_line}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">No source symbols were retrieved.</p>
          )}
        </div>
      )}
    </Section>
  )
}
