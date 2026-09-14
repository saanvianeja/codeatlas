type RepoAnalyzerProps = {
  repoUrl: string
  loading: boolean
  error: string
  onRepoUrlChange: (value: string) => void
  onAnalyze: () => void
}

export default function RepoAnalyzer({
  repoUrl,
  loading,
  error,
  onRepoUrlChange,
  onAnalyze,
}: RepoAnalyzerProps) {
  return (
    <div className="mb-8">
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          type="text"
          value={repoUrl}
          onChange={(event) => onRepoUrlChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !loading) {
              onAnalyze()
            }
          }}
          placeholder="https://github.com/user/repo"
          className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
        />

        <button
          onClick={onAnalyze}
          disabled={loading}
          className="rounded-xl bg-indigo-500 px-6 py-3 font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-900 bg-red-950/40 px-4 py-3 text-red-300">
          {error}
        </div>
      )}
    </div>
  )
}
