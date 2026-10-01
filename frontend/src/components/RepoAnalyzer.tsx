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
    <div className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-5 sm:p-6">
      <label htmlFor="repo-url" className="text-sm font-medium text-slate-200">
        GitHub repository
      </label>
      <p className="mt-1 text-sm text-slate-500">
        Public HTTPS URL only, for example{' '}
        <span className="font-mono text-slate-400">
          https://github.com/pallets/flask
        </span>
      </p>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row">
        <input
          id="repo-url"
          type="text"
          value={repoUrl}
          onChange={(event) => onRepoUrlChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !loading) {
              onAnalyze()
            }
          }}
          placeholder="https://github.com/user/repo"
          disabled={loading}
          className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-60"
        />
        <button
          onClick={onAnalyze}
          disabled={loading || !repoUrl.trim()}
          className="rounded-xl bg-indigo-500 px-6 py-3 font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>
      {error && (
        <div className="mt-4 rounded-xl border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}
    </div>
  )
}
