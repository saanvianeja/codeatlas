export type FileInfo = {
  file: string
  imports: Array<string | null>
  functions: string[]
  classes: string[]
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
  name: string
  type: string
  file: string
  code: string
  score: number
}
