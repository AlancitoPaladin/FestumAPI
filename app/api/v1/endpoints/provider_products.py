from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.dependencies.provider import get_current_provider
from app.schemas.provider_product import (
    ProviderProductCreate,
    ProviderProductDeleteResponse,
    ProviderProductImageReferenceRequest,
    ProviderProductImageReorderRequest,
    ProviderProductImageUploadResponse,
    ProviderProductListResponse,
    ProviderProductResponse,
    ProviderProductUpdate,
)
from app.schemas.provider_reservation import ProviderReservationProductSummaryListResponse
from app.schemas.user import UserResponse
from app.services.provider_product_service import ProviderProductService

router = APIRouter()


@router.post("/me/services/{service_id}/products", response_model=ProviderProductResponse, status_code=201)
def create_my_product(
    service_id: str,
    payload: ProviderProductCreate,
    service: ProviderProductService = Depends(ProviderProductService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderProductResponse:
    return service.create_product(current_provider.id, service_id, payload)


@router.get("/me/services/{service_id}/products", response_model=ProviderProductListResponse)
def list_my_products(
    service_id: str,
    service: ProviderProductService = Depends(ProviderProductService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderProductListResponse:
    return service.list_products(current_provider.id, service_id)


@router.get("/me/services/by-name/{service_name}/products", response_model=ProviderProductListResponse)
def list_my_products_by_service_name(
    service_name: str,
    service: ProviderProductService = Depends(ProviderProductService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderProductListResponse:
    return service.list_products_by_service_name(current_provider.id, service_name)


@router.get("/me/products/reservations", response_model=ProviderReservationProductSummaryListResponse)
def list_my_products_for_reservations(
    service: ProviderProductService = Depends(ProviderProductService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderReservationProductSummaryListResponse:
    return service.list_products_for_reservations(current_provider.id)


@router.get("/me/services/{service_id}/products/{product_id}", response_model=ProviderProductResponse)
def get_my_product(
    service_id: str,
    product_id: str,
    service: ProviderProductService = Depends(ProviderProductService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderProductResponse:
    return service.get_product(current_provider.id, service_id, product_id)


@router.patch("/me/services/{service_id}/products/{product_id}", response_model=ProviderProductResponse)
def update_my_product(
    service_id: str,
    product_id: str,
    payload: ProviderProductUpdate,
    service: ProviderProductService = Depends(ProviderProductService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderProductResponse:
    return service.update_product(current_provider.id, service_id, product_id, payload)


@router.post(
    "/me/services/{service_id}/products/{product_id}/images",
    response_model=ProviderProductImageUploadResponse,
)
def upload_my_product_image(
    service_id: str,
    product_id: str,
    file: UploadFile = File(...),
    is_main: bool = Form(default=False),
    service: ProviderProductService = Depends(ProviderProductService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderProductImageUploadResponse:
    return service.upload_product_image(
        provider_id=current_provider.id,
        service_id=service_id,
        product_id=product_id,
        file=file,
        is_main=is_main,
    )


@router.patch(
    "/me/services/{service_id}/products/{product_id}/images/main",
    response_model=ProviderProductResponse,
)
def set_my_product_main_image(
    service_id: str,
    product_id: str,
    payload: ProviderProductImageReferenceRequest,
    service: ProviderProductService = Depends(ProviderProductService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderProductResponse:
    return service.set_main_product_image(
        provider_id=current_provider.id,
        service_id=service_id,
        product_id=product_id,
        payload=payload,
    )


@router.patch(
    "/me/services/{service_id}/products/{product_id}/images/reorder",
    response_model=ProviderProductResponse,
)
def reorder_my_product_images(
    service_id: str,
    product_id: str,
    payload: ProviderProductImageReorderRequest,
    service: ProviderProductService = Depends(ProviderProductService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderProductResponse:
    return service.reorder_product_images(
        provider_id=current_provider.id,
        service_id=service_id,
        product_id=product_id,
        payload=payload,
    )


@router.delete(
    "/me/services/{service_id}/products/{product_id}/images",
    response_model=ProviderProductResponse,
)
def delete_my_product_image(
    service_id: str,
    product_id: str,
    payload: ProviderProductImageReferenceRequest,
    service: ProviderProductService = Depends(ProviderProductService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderProductResponse:
    return service.delete_product_image(
        provider_id=current_provider.id,
        service_id=service_id,
        product_id=product_id,
        payload=payload,
    )


@router.delete(
    "/me/services/{service_id}/products/{product_id}",
    response_model=ProviderProductDeleteResponse,
)
def delete_my_product(
    service_id: str,
    product_id: str,
    service: ProviderProductService = Depends(ProviderProductService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderProductDeleteResponse:
    return service.delete_product(current_provider.id, service_id, product_id)


@router.delete("/me/products/{product_id}", response_model=ProviderProductDeleteResponse)
def delete_my_product_by_id(
    product_id: str,
    service: ProviderProductService = Depends(ProviderProductService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderProductDeleteResponse:
    return service.delete_product_by_id(current_provider.id, product_id)
