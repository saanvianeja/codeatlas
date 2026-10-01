from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalysisCreateRequest(BaseModel):
    repo_url: str = Field(min_length=1)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=25)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Query must not be empty.")
        return stripped


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
    rank: int
    name: str
    qualified_name: str
    type: str
    file: str
    start_line: int
    end_line: int
    similarity: float
    code: str


class SearchResponse(BaseModel):
    results: list[SearchResult]


class AskRequest(BaseModel):
    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Question must not be empty.")
        return stripped


class AskSource(BaseModel):
    file: str
    qualified_name: str
    start_line: int
    end_line: int


class AskResponse(BaseModel):
    answer: str
    sources: list[AskSource]


class ImpactResponse(BaseModel):
    selected_file: str
    direct_dependents: list[str]
    transitive_dependents: list[str]
    all_impacted_files: list[str]
    total_impacted: int
    distances: dict[str, int]
