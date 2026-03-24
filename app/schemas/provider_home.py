from datetime import datetime

from pydantic import BaseModel, Field


class ProviderQuickStatsResponse(BaseModel):
    reservations_this_month: int = 0
    active_services: int = 0


class ProviderFeaturedServiceResponse(BaseModel):
    id: str
    title: str
    category: str
    status: str
    price_label: str
    reservations: int = 0
    image_url: str = ""


class ProviderHomeDashboardResponse(BaseModel):
    provider_id: str
    display_name: str
    business_name: str = ""
    avatar_url: str = ""
    quick_stats: ProviderQuickStatsResponse
    featured_services: list[ProviderFeaturedServiceResponse] = Field(default_factory=list)


class ProviderNotificationResponse(BaseModel):
    id: str
    title: str
    subtitle: str
    is_unread: bool = True
    created_at: datetime
    updated_at: datetime


class ProviderNotificationListResponse(BaseModel):
    items: list[ProviderNotificationResponse] = Field(default_factory=list)
    unread_count: int = 0


class ProviderNotificationsBulkActionResponse(BaseModel):
    affected_count: int = 0
