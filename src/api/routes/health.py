from fastapi import APIRouter
from config.settings import settings

router = APIRouter()


@router.get("/")
async def health_check():
    return {
        "status": "healthy",
        "env": settings.APP_ENV,
        "region": settings.AWS_REGION,
        "bedrock_model": settings.AWS_BEDROCK_MODEL_ID,
    }