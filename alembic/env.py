import asyncio
from logging.config import fileConfig
import os

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# 1. Загружаем переменные из .env
load_dotenv()

# 2. Настройка логирования из alembic.ini
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 3. Переопределяем sqlalchemy.url значением из переменной окружения DATABASE_URL
db_url = os.getenv("DATABASE_URL")
if db_url:
    # Заменяем URL для корректного формата, если требуется
    config.set_main_option("sqlalchemy.url", db_url)

# 4. Импортируем метаданные ваших моделей
# Подключите ваш Base и файл(ы) моделей, чтобы Alembic "увидел" структуру таблиц
from app.database import Base  # Импорт вашего Base
from app.models.models import *  # Импорт всех моделей (Encounter, Combatant, Character, MonsterTemplate и т.д.)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в оффлайн-режиме (без подключения к живой БД)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Асинхронный запуск миграций (для asyncpg)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Запуск миграций в онлайн-режиме."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()