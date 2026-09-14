import { useState } from 'react'
import type { SemanticSearchResult } from '../types'

type SearchResponse = SemanticSearchResult[] | { error: string }

export default function SemanticSearch() {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SemanticSearchResult[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)

  async function semanticSearch() {
    if (!searchQuery.trim()) return

    setSearchLoading(true)
    setSearchError('')
    setHasSearched(true)

    try {
      const response = await fetch('http://127.0.0.1:8000/semantic_search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
        }),
      })

      const data: SearchResponse = await response.json()

      if (!response.ok) {
        throw new Error('Semantic search failed')
      }

      if (!Array.isArray(data)) {
        setSearchError(data.error || 'Semantic search failed')
        setSearchResults([])
        return
      }

      setSearchResults(data)
    } catch (error) {
      console.error(error)
      setSearchError('Could not perform semantic search.')
      setSearchResults([])
    } finally {
      setSearchLoading(false)
    }
  }

  return (
    <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-5">
        <h2 className="text-xl font-semibold">Semantic Code Search</h2>
        <p className="mt-1 text-sm text-slate-400">
          Search the repository using natural language.
        </p>
      </div>

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
          placeholder="e.g. Where is user authentication handled?"
          className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
        />

        <button
          onClick={semanticSearch}
          disabled={searchLoading || !searchQuery.trim()}
          className="rounded-xl bg-indigo-500 px-6 py-3 font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {searchLoading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {searchError && (
        <div className="mt-4 rounded-xl border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-300">
          {searchError}
        </div>
      )}

      {searchLoading && (
        <p className="mt-4 text-sm text-slate-400">Searching the indexed repository...</p>
      )}

      {!searchLoading && hasSearched && !searchError && searchResults.length === 0 && (
        <p className="mt-4 text-sm text-slate-500">
          No matching functions or classes were found.
        </p>
      )}

      {searchResults.length > 0 && (
        <div className="mt-6 space-y-4">
          {searchResults.map((result, index) => (
            <article
              key={`${result.File}-${result.Name}-${index}`}
              className="rounded-xl border border-slate-800 bg-slate-950 p-5"
            >
              <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-mono text-base font-semibold text-slate-100">
                      {result.Name}
                    </h3>
                    <span className="rounded-md bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                      {result.Type}
                    </span>
                  </div>
                  <p className="mt-1 truncate font-mono text-sm text-slate-400">
                    {result.File}
                  </p>
                </div>

                <div className="rounded-md border border-slate-800 bg-slate-900 px-2.5 py-1 text-right">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">
                    Similarity
                  </p>
                  <p className="font-mono text-sm text-indigo-300">
                    {result.Score.toFixed(3)}
                  </p>
                </div>
              </div>

              <pre className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900 p-4 text-sm leading-6 text-slate-300">
                <code>{result.Code}</code>
              </pre>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
