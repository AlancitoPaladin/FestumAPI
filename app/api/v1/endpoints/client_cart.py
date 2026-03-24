from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_current_user
from app.schemas.client import (
    AddCartItemRequest,
    CartContainsResponse,
    CartItem,
    CartItemsResponse,
    OkResponse,
    RemovedCartItemResponse,
    RestoreCartItemRequest,
)
from app.schemas.user import UserResponse
from app.services.client_cart_service import ClientCartService

router = APIRouter()


@router.get("/cart", response_model=CartItemsResponse)
def get_cart_items(
    current_user: UserResponse = Depends(get_current_user),
    service: ClientCartService = Depends(ClientCartService),
) -> CartItemsResponse:
    return service.list_items(current_user.id)


@router.delete("/cart", response_model=OkResponse)
def clear_cart(
    current_user: UserResponse = Depends(get_current_user),
    service: ClientCartService = Depends(ClientCartService),
) -> OkResponse:
    return service.clear(current_user.id)


@router.get("/cart/contains/{serviceId}", response_model=CartContainsResponse)
def cart_contains_service(
    serviceId: str,
    current_user: UserResponse = Depends(get_current_user),
    service: ClientCartService = Depends(ClientCartService),
) -> CartContainsResponse:
    return service.contains(current_user.id, serviceId)


@router.post("/cart/items", response_model=CartItem, status_code=status.HTTP_201_CREATED)
def add_cart_item(
    payload: AddCartItemRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: ClientCartService = Depends(ClientCartService),
) -> CartItem:
    return service.add(current_user.id, payload)


@router.delete("/cart/items/{id}", response_model=RemovedCartItemResponse)
def remove_cart_item(
    id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: ClientCartService = Depends(ClientCartService),
) -> RemovedCartItemResponse:
    return service.remove(current_user.id, id)


@router.post("/cart/restore", response_model=OkResponse)
def restore_cart_item(
    payload: RestoreCartItemRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: ClientCartService = Depends(ClientCartService),
) -> OkResponse:
    return service.restore(current_user.id, payload)
