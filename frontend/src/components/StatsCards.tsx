import type { FileInfo } from '../types'

type StatsCardsProps = {
  repoUrl: string
  files: FileInfo[]
}

export default function StatsCards({ repoUrl, files }: StatsCardsProps) {
  const functionCount = files.reduce(
    (sum, file) =>
      sum + file.functions.length + (file.async_functions?.length ?? 0),
    0
  )
  const classCount = files.reduce((sum, file) => sum + file.classes.length, 0)
  const importCount = files.reduce((sum, file) => sum + file.imports.length, 0)

  const stats = [
    { label: 'Files', value: files.length },
    { label: 'Functions', value: functionCount },
    { label: 'Classes', value: classCount },
    { label: 'Imports', value: importCount },
  ]

  return (
    <section className="mb-8">
      <div className="mb-4">
        <h2 className="text-lg font-semibold tracking-tight sm:text-xl">
          Repository overview
        </h2>
        <p className="mt-1 truncate font-mono text-sm text-slate-500">{repoUrl}</p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-4 sm:p-5"
          >
            <p className="text-xs uppercase tracking-wide text-slate-500 sm:text-sm sm:normal-case sm:tracking-normal">
              {stat.label}
            </p>
            <p className="mt-2 text-2xl font-bold tabular-nums sm:text-3xl">
              {stat.value}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}
