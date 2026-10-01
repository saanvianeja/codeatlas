from uuid import UUID

from fastapi import APIRouter

import services
from schemas import (
    AnalysisCreateRequest,
    AnalysisResponse,
    SearchRequest,
    SearchResponse,
)

router = APIRouter()


@router.post("/analyses", response_model=AnalysisResponse)
def create_analysis(request: AnalysisCreateRequest):
    return services.create_analysis(request.repo_url)


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: UUID):
    return services.get_analysis(str(analysis_id))


@router.post("/analyses/{analysis_id}/search", response_model=SearchResponse)
def search_analysis(analysis_id: UUID, request: SearchRequest):
    results = services.search_analysis(str(analysis_id), request.query)
    return {"results": results}
