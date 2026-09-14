import type { FileInfo } from '../types'

type RepositoryFilesProps = {
  files: FileInfo[]
}

export default function RepositoryFiles({ files }: RepositoryFilesProps) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-5">
        <h2 className="text-xl font-semibold">Repository Files</h2>
        <p className="mt-1 text-sm text-slate-400">
          Python files discovered during analysis.
        </p>
      </div>

      {files.length === 0 ? (
        <p className="rounded-lg border border-slate-800 bg-slate-950 px-4 py-6 text-sm text-slate-500">
          No Python files were found in this repository.
        </p>
      ) : (
        <div className="grid gap-2">
          {files.map((fileinfo) => (
            <div
              key={fileinfo.file}
              className="flex items-center justify-between gap-4 rounded-lg border border-slate-800 bg-slate-950 px-4 py-3"
            >
              <span className="truncate font-mono text-sm text-slate-300">
                {fileinfo.file}
              </span>

              <span className="shrink-0 text-xs text-slate-500">
                {fileinfo.functions.length} functions
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
