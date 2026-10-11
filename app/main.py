from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
import app.models.models
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("База данных и таблицы успешно инициализированы!")

    yield

    await engine.dispose()
    print("Подключение к БД закрыто.")


app = FastAPI(
    title="D&D Initiative",
    description="Backend API для автоматизации инициативы и боевых сцен D&D",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# Настройка CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы (GET, POST, PUT, DELETE и т.д.)
    allow_headers=["*"],  # Разрешаем все заголовки
)

#Подключаем роуты
app.include_router(api_router)
