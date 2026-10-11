from fastapi import APIRouter
from app.api.v1.characters import router as characters_router
from app.api.v1.monsters import router as monsters_router
from app.api.v1.encounters import router as encounters_router
from app.api.v1.combat import router as combat_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(characters_router)
api_router.include_router(monsters_router)
api_router.include_router(encounters_router)
api_router.include_router(combat_router)