"""API v1 root router aggregating all resource sub-routers."""
from fastapi import APIRouter
from app.api.v1.endpoints import admin, articles, auth, projects, providers, publishing

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(articles.router, prefix="/articles", tags=["Articles"])
api_router.include_router(providers.router, prefix="/providers", tags=["AI Providers"])
api_router.include_router(publishing.router, prefix="/publishing", tags=["Publishing"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin & Governance"])
