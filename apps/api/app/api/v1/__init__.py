"""API version 1 router aggregator."""

from fastapi import APIRouter

from app.api.v1.account import router as account_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dnc import router as dnc_router
from app.api.v1.gap import router as gap_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.leads import router as leads_router
from app.api.v1.models import router as models_router
from app.api.v1.offer_profile import router as offer_profile_router
from app.api.v1.places import router as places_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(dnc_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(places_router)
api_v1_router.include_router(gap_router)
api_v1_router.include_router(leads_router)
api_v1_router.include_router(models_router)
api_v1_router.include_router(offer_profile_router)
api_v1_router.include_router(account_router)

__all__ = ["api_v1_router"]
