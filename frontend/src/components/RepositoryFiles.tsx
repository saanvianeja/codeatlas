import type { FileInfo } from '../types'
import Section from './Section'

type RepositoryFilesProps = {
  files: FileInfo[]
}

export default function RepositoryFiles({ files }: RepositoryFilesProps) {
  return (
    <Section
      className="mb-8"
      title="Repository files"
      description="Python files discovered during analysis. Parse failures are listed without executing repository code."
    >
      {files.length === 0 ? (
        <p className="rounded-lg border border-slate-800 bg-slate-950 px-4 py-6 text-sm text-slate-500">
          No Python files were found in this repository.
        </p>
      ) : (
        <div className="grid max-h-[28rem] gap-2 overflow-y-auto">
          {files.map((fileinfo) => {
            const fnCount =
              fileinfo.functions.length + (fileinfo.async_functions?.length ?? 0)
            const classCount = fileinfo.classes.length
            return (
              <div
                key={fileinfo.file}
                className="flex items-center justify-between gap-4 rounded-lg border border-slate-800 bg-slate-950 px-4 py-3"
              >
                <span className="truncate font-mono text-sm text-slate-300">
                  {fileinfo.file}
                </span>
                <span className="shrink-0 text-xs text-slate-500">
                  {fileinfo.error
                    ? 'parse error'
                    : `${fnCount} functions · ${classCount} classes`}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </Section>
  )
}
