import type { FileInfo } from '../types'

type StatsCardsProps = {
  files: FileInfo[]
}

export default function StatsCards({ files }: StatsCardsProps) {
  const functionCount = files.reduce(
    (sum, file) => sum + file.functions.length,
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
    <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="rounded-xl border border-slate-800 bg-slate-900 p-5"
        >
          <p className="text-sm text-slate-400">{stat.label}</p>
          <p className="mt-2 text-3xl font-bold">{stat.value}</p>
        </div>
      ))}
    </div>
  )
}
