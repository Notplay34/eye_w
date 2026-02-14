from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app.core.database import engine, Base, async_session_maker
from app.core.logging_config import setup_logging, get_logger
from app.models import DocumentPrice, Employee
from app.models.employee import EmployeeRole
from app.data.price_list import PRICE_LIST as DEFAULT_PRICE_LIST
from app.api.orders import router as orders_router
from app.api.employees import router as employees_router
from app.api.documents import router as documents_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.price_list import router as price_list_router
from app.services.auth_service import hash_password

setup_logging()
logger = get_logger(__name__)

SUPERUSER_LOGIN = "sergey151"
SUPERUSER_PASSWORD = "1wq21wq2"
SUPERUSER_NAME = "Сергей"


async def ensure_columns_and_enum():
    """Добавить колонки login, password_hash и ROLE_MANAGER в enum для старых БД."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='employees' AND column_name='login') THEN
                    ALTER TABLE employees ADD COLUMN login VARCHAR(64) UNIQUE;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='employees' AND column_name='password_hash') THEN
                    ALTER TABLE employees ADD COLUMN password_hash VARCHAR(255);
                END IF;
            END $$;
        """))
    try:
        async with engine.connect() as conn:
            await conn.execute(text("ALTER TYPE employeerole ADD VALUE 'ROLE_MANAGER'"))
            await conn.commit()
    except Exception as e:
        if "already exists" not in str(e).lower():
            logger.warning("Enum ROLE_MANAGER: %s", e)


async def ensure_superuser():
    """Создать суперпользователя sergey151, если такого логина ещё нет."""
    async with async_session_maker() as session:
        r = await session.execute(select(Employee).where(Employee.login == SUPERUSER_LOGIN))
        if r.scalar_one_or_none() is not None:
            return
        emp = Employee(
            name=SUPERUSER_NAME,
            role=EmployeeRole.ROLE_ADMIN,
            login=SUPERUSER_LOGIN,
            password_hash=hash_password(SUPERUSER_PASSWORD),
            is_active=True,
        )
        session.add(emp)
        await session.commit()
        logger.info("Создан суперпользователь: %s", SUPERUSER_LOGIN)


async def seed_document_prices():
    """Заполнить прейскурант из дефолтного списка, если таблица пуста."""
    async with async_session_maker() as session:
        r = await session.execute(select(DocumentPrice).limit(1))
        if r.scalar_one_or_none() is not None:
            return
        for i, item in enumerate(DEFAULT_PRICE_LIST):
            row = DocumentPrice(
                template=item["template"],
                label=item["label"],
                price=item["price"],
                sort_order=i,
            )
            session.add(row)
        await session.commit()
        logger.info("Прейскурант заполнен из дефолтного списка (%s позиций)", len(DEFAULT_PRICE_LIST))


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Таблицы БД проверены/созданы")
    try:
        await ensure_columns_and_enum()
    except Exception as e:
        logger.warning("Миграция колонок: %s", e)
    try:
        await ensure_superuser()
    except Exception as e:
        logger.warning("Суперпользователь: %s", e)
    try:
        await seed_document_prices()
    except Exception as e:
        logger.warning("Прейскурант: %s", e)
    yield
    await engine.dispose()


app = FastAPI(title="Павильоны МРЭО", version="0.1.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Необработанная ошибка: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(orders_router)
app.include_router(documents_router)
app.include_router(price_list_router)
app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(employees_router)


@app.get("/health")
def health():
    return {"status": "ok"}
