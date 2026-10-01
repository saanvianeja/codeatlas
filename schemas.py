from pydantic import BaseModel, ConfigDict, Field


class AnalysisCreateRequest(BaseModel):
    repo_url: str = Field(min_length=1)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)


class ImportInfo(BaseModel):
    raw: str
    kind: str
    resolved_file: str | None = None


class SymbolInfo(BaseModel):
    name: str
    qualified_name: str
    type: str
    file: str
    lineno: int
    end_lineno: int
    arguments: list[str]
    docstring: str | None = None
    code: str


class FileInfo(BaseModel):
    file: str
    imports: list[ImportInfo]
    functions: list[str]
    async_functions: list[str] = []
    classes: list[str]
    methods: list[str] = []
    symbols: list[SymbolInfo] = []
    error: str | None = None


class Dependency(BaseModel):
    source: str
    target: str


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    repo_url: str
    files: list[FileInfo]
    dependencies: list[Dependency]


class SearchResult(BaseModel):
    name: str
    type: str
    file: str
    code: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]


class ImpactResponse(BaseModel):
    selected_file: str
    direct_dependents: list[str]
    transitive_dependents: list[str]
    all_impacted_files: list[str]
    total_impacted: int
    distances: dict[str, int]
