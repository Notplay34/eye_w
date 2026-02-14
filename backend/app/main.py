from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.database import engine, Base
from app.core.logging_config import setup_logging, get_logger
from app.models import Employee, Order, Payment, Plate
from app.api.orders import router as orders_router
from app.api.employees import router as employees_router
from app.api.documents import router as documents_router
from app.api.analytics import router as analytics_router

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Таблицы БД проверены/созданы")
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
app.include_router(analytics_router)
app.include_router(employees_router)


@app.get("/health")
def health():
    return {"status": "ok"}
