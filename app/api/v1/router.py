from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.client_cart import router as client_cart_router
from app.api.v1.endpoints.client_orders import router as client_orders_router
from app.api.v1.endpoints.client_products import router as client_products_router
from app.api.v1.endpoints.client_services import router as client_services_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.provider_availability import router as provider_availability_router
from app.api.v1.endpoints.provider_bookings import router as provider_bookings_router
from app.api.v1.endpoints.provider_home import router as provider_home_router
from app.api.v1.endpoints.provider_products import router as provider_products_router
from app.api.v1.endpoints.provider_services import router as provider_services_router
from app.api.v1.endpoints.providers import router as providers_router
from app.api.v1.endpoints.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])

api_router.include_router(client_services_router, prefix="/client", tags=["client"])
api_router.include_router(client_products_router, prefix="/client", tags=["client"])
api_router.include_router(client_cart_router, prefix="/client", tags=["client"])
api_router.include_router(client_orders_router, prefix="/client", tags=["client"])

api_router.include_router(provider_home_router, prefix="/providers", tags=["providers"])
api_router.include_router(providers_router, prefix="/providers", tags=["providers"])
api_router.include_router(provider_services_router, prefix="/providers", tags=["providers"])
api_router.include_router(provider_products_router, prefix="/providers", tags=["providers"])
api_router.include_router(provider_bookings_router, prefix="/providers", tags=["providers"])
api_router.include_router(provider_availability_router, prefix="/providers", tags=["providers"])
