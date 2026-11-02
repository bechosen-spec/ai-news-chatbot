import logging

from fastapi import APIRouter, HTTPException, Request, status

from backend.app.schemas.ml import (
    ClassificationRequest,
    ClassificationResponse,
    ModelInfoResponse,
)
from backend.app.services.model_service import ModelUnavailableError

LOGGER = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ml", tags=["machine-learning"])


@router.get("/model-info", response_model=ModelInfoResponse)
def model_info(request: Request) -> dict:
    return request.app.state.model_service.metadata()


@router.post("/classify", response_model=ClassificationResponse)
def classify(payload: ClassificationRequest, request: Request) -> dict:
    text = "\n\n".join(part for part in (payload.title, payload.content) if part)
    try:
        return request.app.state.model_service.classify(text)
    except ModelUnavailableError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except Exception as error:
        LOGGER.exception("Unexpected classification failure")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Classification failed"
        ) from error
