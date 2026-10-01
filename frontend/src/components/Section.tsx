import type { ReactNode } from 'react'

type SectionProps = {
  title: string
  kicker?: string
  description: string
  children: ReactNode
  className?: string
}

export default function Section({
  title,
  kicker,
  description,
  children,
  className = '',
}: SectionProps) {
  return (
    <section
      className={`rounded-2xl border border-slate-800 bg-slate-900 p-5 sm:p-6 ${className}`}
    >
      <div className="mb-5">
        {kicker ? (
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-indigo-400">
            {kicker}
          </p>
        ) : null}
        <h2 className="text-lg font-semibold tracking-tight sm:text-xl">{title}</h2>
        <p className="mt-1.5 max-w-3xl text-sm leading-6 text-slate-400">
          {description}
        </p>
      </div>
      {children}
    </section>
  )
}
