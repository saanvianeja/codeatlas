from uuid import UUID

from fastapi import APIRouter, Query

import services
from schemas import (
    AnalysisCreateRequest,
    AnalysisResponse,
    ImpactResponse,
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


@router.get("/analyses/{analysis_id}/impact", response_model=ImpactResponse)
def get_impact(
    analysis_id: UUID,
    file: str = Query(
        ...,
        min_length=1,
        description="Repository-relative Python file path",
    ),
):
    return services.get_impact(str(analysis_id), file)
