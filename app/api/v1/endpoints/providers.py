from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies.provider import get_current_provider
from app.schemas.provider import (
    ProviderBusinessAssetUploadResponse,
    ProviderBusinessProfileResponse,
    ProviderBusinessProfileUpsert,
)
from app.services.provider_service import ProviderService

router = APIRouter()


@router.get("/me/business-profile", response_model=ProviderBusinessProfileResponse)
def get_my_business_profile(
    service: ProviderService = Depends(ProviderService),
    current_provider=Depends(get_current_provider),
) -> ProviderBusinessProfileResponse:
    return service.get_business_profile(current_provider.id)


@router.put("/me/business-profile", response_model=ProviderBusinessProfileResponse)
def upsert_my_business_profile(
    payload: ProviderBusinessProfileUpsert,
    service: ProviderService = Depends(ProviderService),
    current_provider=Depends(get_current_provider),
) -> ProviderBusinessProfileResponse:
    return service.upsert_business_profile(current_provider.id, payload)


@router.post("/me/business-profile/logo", response_model=ProviderBusinessAssetUploadResponse)
def upload_my_business_logo(
    file: UploadFile = File(...),
    service: ProviderService = Depends(ProviderService),
    current_provider=Depends(get_current_provider),
) -> ProviderBusinessAssetUploadResponse:
    return service.upload_logo(current_provider.id, file)


@router.post("/me/business-profile/photos", response_model=ProviderBusinessAssetUploadResponse)
def upload_my_business_photo(
    file: UploadFile = File(...),
    service: ProviderService = Depends(ProviderService),
    current_provider=Depends(get_current_provider),
) -> ProviderBusinessAssetUploadResponse:
    return service.upload_photo(current_provider.id, file)
