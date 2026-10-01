from pydantic import BaseModel, ConfigDict, Field


class AnalysisCreateRequest(BaseModel):
    repo_url: str = Field(min_length=1)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)


class FileInfo(BaseModel):
    file: str
    imports: list[str | None]
    functions: list[str]
    classes: list[str]
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
