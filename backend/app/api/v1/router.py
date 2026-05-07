from fastapi import APIRouter
from app.api.v1 import auth, cases, documents, quesitos, ai, processing_jobs

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(cases.router)
api_router.include_router(documents.router)
api_router.include_router(processing_jobs.router)
api_router.include_router(quesitos.router)
api_router.include_router(ai.router)
