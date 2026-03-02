from fastapi import APIRouter, Depends

from app.services.health_service import HealthService

router = APIRouter()


@router.get("/health", summary="API health check")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/firebase", summary="Firebase connectivity health check")
def firebase_healthcheck(service: HealthService = Depends(HealthService)) -> dict[str, str]:
    service.check_firestore_connection()
    return {"status": "ok", "firebase": "connected"}

