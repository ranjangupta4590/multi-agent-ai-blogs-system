"""API v1 root router aggregating all resource sub-routers."""
from fastapi import APIRouter
from app.api.v1.endpoints import admin, articles, auth, payments, projects, providers, public, superadmin_companies

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(articles.router, prefix="/articles", tags=["Articles"])
api_router.include_router(providers.router, prefix="/providers", tags=["AI Providers"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin & Governance"])
api_router.include_router(public.router, prefix="/public", tags=["Public Blog"])
api_router.include_router(superadmin_companies.router, prefix="/superadmin", tags=["Superadmin & Studio"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments & Webhooks"])

