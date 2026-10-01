export type ImportKind = "internal" | "stdlib" | "third_party" | "unresolved"

export type ImportInfo = {
  raw: string
  kind: ImportKind
  resolved_file: string | null
}

export type SymbolInfo = {
  name: string
  qualified_name: string
  type: string
  file: string
  lineno: number
  end_lineno: number
  arguments: string[]
  docstring: string | null
  code: string
}

export type FileInfo = {
  file: string
  imports: ImportInfo[]
  functions: string[]
  async_functions?: string[]
  classes: string[]
  methods?: string[]
  symbols?: SymbolInfo[]
  error?: string | null
}

export type Dependency = {
  source: string
  target: string
}

export type AnalysisResult = {
  analysis_id: string
  repo_url: string
  files: FileInfo[]
  dependencies: Dependency[]
}

export type SemanticSearchResult = {
  rank: number
  name: string
  qualified_name: string
  type: string
  file: string
  start_line: number
  end_line: number
  similarity: number
  code: string
}

export type ImpactResult = {
  selected_file: string
  direct_dependents: string[]
  transitive_dependents: string[]
  all_impacted_files: string[]
  total_impacted: number
  distances: Record<string, number>
}
