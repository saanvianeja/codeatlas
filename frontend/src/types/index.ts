export type FileInfo = {
  file: string
  imports: string[]
  functions: string[]
  classes: string[]
}

export type AnalysisResult = {
  files: FileInfo[]
  dependencies: string[][]
}

export type SemanticSearchResult = {
  Name: string
  Type: string
  File: string
  Code: string
  Score: number
}
