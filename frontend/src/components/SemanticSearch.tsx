import { useEffect, useState } from 'react'
import type { SemanticSearchResult } from '../types'
import { API_BASE, errorMessage } from '../api'
import Section from './Section'

type SemanticSearchProps = {
  analysisId: string | null
}

export default function SemanticSearch({ analysisId }: SemanticSearchProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SemanticSearchResult[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)

  useEffect(() => {
    setSearchResults([])
    setSearchError('')
    setHasSearched(false)
  }, [analysisId])

  async function semanticSearch() {
    if (!searchQuery.trim() || !analysisId) return

    setSearchLoading(true)
    setSearchError('')
    setHasSearched(true)

    try {
      const response = await fetch(
        `${API_BASE}/analyses/${analysisId}/search`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: searchQuery,
          }),
        }
      )

      const data: unknown = await response.json()

      if (!response.ok) {
        throw new Error(errorMessage(data, 'Semantic search failed'))
      }

      if (
        typeof data !== 'object' ||
        data === null ||
        !('results' in data) ||
        !Array.isArray(data.results)
      ) {
        throw new Error('Semantic search failed')
      }

      setSearchResults(data.results as SemanticSearchResult[])
    } catch (error) {
      setSearchError(
        error instanceof Error ? error.message : 'Could not perform semantic search.'
      )
      setSearchResults([])
    } finally {
      setSearchLoading(false)
    }
  }

  return (
    <Section
      kicker="Retrieved code"
      title="Semantic Search"
      description="Natural-language lookup over cached MiniLM embeddings. Results are the matching symbols and their source — not an LLM summary."
    >
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          type="text"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              semanticSearch()
            }
          }}
          placeholder={
            analysisId
              ? 'e.g. Where is user authentication handled?'
              : 'Analyze a repository to search its code'
          }
          disabled={!analysisId}
          className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-50"
        />
        <button
          onClick={semanticSearch}
          disabled={!analysisId || searchLoading || !searchQuery.trim()}
          className="rounded-xl bg-indigo-500 px-6 py-3 font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {searchLoading ? 'Searching…' : 'Search'}
        </button>
      </div>

      {!analysisId && (
        <p className="mt-4 text-sm text-slate-500">
          Analyze a repository first. Search returns ranked symbols with file and line ranges.
        </p>
      )}

      {searchError && (
        <div className="mt-4 rounded-xl border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-300">
          {searchError}
        </div>
      )}

      {searchLoading && (
        <p className="mt-4 text-sm text-slate-400">
          Searching the indexed repository…
        </p>
      )}

      {!searchLoading && hasSearched && !searchError && searchResults.length === 0 && (
        <p className="mt-4 rounded-lg border border-slate-800 bg-slate-950 px-4 py-4 text-sm text-slate-500">
          No matching functions or classes were found.
        </p>
      )}

      {searchResults.length > 0 && (
        <div className="mt-6 space-y-4">
          {searchResults.map((result) => (
            <article
              key={`${result.file}-${result.qualified_name}-${result.start_line}`}
              className="rounded-xl border border-slate-800 bg-slate-950 p-4 sm:p-5"
            >
              <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-mono text-sm font-semibold text-slate-100 sm:text-base">
                      {result.qualified_name}
                    </h3>
                    <span className="rounded-md bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                      {result.type}
                    </span>
                  </div>
                  <p className="mt-1 truncate font-mono text-xs text-slate-400 sm:text-sm">
                    {result.file} · lines {result.start_line}–{result.end_line}
                  </p>
                </div>
                <div className="rounded-md border border-slate-800 bg-slate-900 px-2.5 py-1 text-right">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">
                    Similarity
                  </p>
                  <p className="font-mono text-sm text-indigo-300">
                    {result.similarity.toFixed(2)}
                  </p>
                </div>
              </div>
              <pre className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900 p-3 text-xs leading-6 text-slate-300 sm:p-4 sm:text-sm">
                <code>{result.code}</code>
              </pre>
            </article>
          ))}
        </div>
      )}
    </Section>
  )
}
