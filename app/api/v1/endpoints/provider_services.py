from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.dependencies.provider import get_current_provider
from app.schemas.provider_service import (
    ProviderServiceCreate,
    ProviderServiceDeleteResponse,
    ProviderServiceDraftCreate,
    ProviderServiceImageReferenceRequest,
    ProviderServiceImageReorderRequest,
    ProviderServiceImageUploadResponse,
    ProviderServiceListResponse,
    ProviderServiceResponse,
    ProviderServiceUpdate,
)
from app.schemas.user import UserResponse
from app.services.provider_service_catalog_service import ProviderServiceCatalogService

router = APIRouter()


@router.post("/me/services", response_model=ProviderServiceResponse, status_code=201)
def create_my_service(
    payload: ProviderServiceCreate,
    service: ProviderServiceCatalogService = Depends(ProviderServiceCatalogService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderServiceResponse:
    return service.create_service(current_provider.id, payload)


@router.post("/me/services/drafts", response_model=ProviderServiceResponse, status_code=201)
def create_my_service_draft(
    payload: ProviderServiceDraftCreate,
    service: ProviderServiceCatalogService = Depends(ProviderServiceCatalogService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderServiceResponse:
    return service.create_draft_service(current_provider.id, payload)


@router.get("/me/services", response_model=ProviderServiceListResponse)
def list_my_services(
    service: ProviderServiceCatalogService = Depends(ProviderServiceCatalogService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderServiceListResponse:
    return service.list_services(current_provider.id)


@router.get("/me/services/{service_id}", response_model=ProviderServiceResponse)
def get_my_service(
    service_id: str,
    service: ProviderServiceCatalogService = Depends(ProviderServiceCatalogService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderServiceResponse:
    return service.get_service(current_provider.id, service_id)


@router.patch("/me/services/{service_id}", response_model=ProviderServiceResponse)
def update_my_service(
    service_id: str,
    payload: ProviderServiceUpdate,
    service: ProviderServiceCatalogService = Depends(ProviderServiceCatalogService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderServiceResponse:
    return service.update_service(current_provider.id, service_id, payload)


@router.post("/me/services/{service_id}/images", response_model=ProviderServiceImageUploadResponse)
def upload_my_service_image(
    service_id: str,
    file: UploadFile = File(...),
    is_main: bool = Form(default=False),
    service: ProviderServiceCatalogService = Depends(ProviderServiceCatalogService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderServiceImageUploadResponse:
    return service.upload_service_image(
        provider_id=current_provider.id,
        service_id=service_id,
        file=file,
        is_main=is_main,
    )


@router.patch("/me/services/{service_id}/images/main", response_model=ProviderServiceResponse)
def set_my_service_main_image(
    service_id: str,
    payload: ProviderServiceImageReferenceRequest,
    service: ProviderServiceCatalogService = Depends(ProviderServiceCatalogService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderServiceResponse:
    return service.set_main_service_image(
        provider_id=current_provider.id,
        service_id=service_id,
        payload=payload,
    )


@router.patch("/me/services/{service_id}/images/reorder", response_model=ProviderServiceResponse)
def reorder_my_service_images(
    service_id: str,
    payload: ProviderServiceImageReorderRequest,
    service: ProviderServiceCatalogService = Depends(ProviderServiceCatalogService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderServiceResponse:
    return service.reorder_service_images(
        provider_id=current_provider.id,
        service_id=service_id,
        payload=payload,
    )


@router.delete("/me/services/{service_id}/images", response_model=ProviderServiceResponse)
def delete_my_service_image(
    service_id: str,
    payload: ProviderServiceImageReferenceRequest,
    service: ProviderServiceCatalogService = Depends(ProviderServiceCatalogService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderServiceResponse:
    return service.delete_service_image(
        provider_id=current_provider.id,
        service_id=service_id,
        payload=payload,
    )


@router.delete("/me/services/{service_id}", response_model=ProviderServiceDeleteResponse)
def delete_my_service(
    service_id: str,
    service: ProviderServiceCatalogService = Depends(ProviderServiceCatalogService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderServiceDeleteResponse:
    return service.delete_service(current_provider.id, service_id)
