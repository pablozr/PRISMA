from contextlib import asynccontextmanager
from fastapi.openapi.docs import get_swagger_ui_html
from core.config.config import settings
from core.http.http_client import http_client
from core.postgresql.postgresql import postgresql
from fastapi import FastAPI

from core.redis.redis_cache import redis_cache
from routes.auth.router import router as auth_router
from routes.admin.router import router as admin_router
from routes.catalogues.router import router as catalogues_router
from routes.projects.router import router as projects_router


from fastapi.middleware.cors import CORSMiddleware

API_PREFIX = "/api/v1/unirio"
OPENAPI_URL = f"{API_PREFIX}/openapi.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando conexões...")
    await postgresql.connect()
    await redis_cache.connect()
    await http_client.connect()
    print("Todos os serviços conectados com sucesso!")

    yield

    print("Encerrando conexões...")
    await postgresql.disconnect()
    await redis_cache.disconnect()
    await http_client.disconnect()
    print("Todos os serviços desconectados com sucesso!")


app = FastAPI(lifespan=lifespan, openapi_url=OPENAPI_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=f"{API_PREFIX}/auth", tags=["auth"])
app.include_router(admin_router, prefix=f"{API_PREFIX}/admin", tags=["admin"])
app.include_router(catalogues_router, prefix=f"{API_PREFIX}/catalogues", tags=["catalogues"])
app.include_router(projects_router, prefix=API_PREFIX, tags=["projects"])


@app.get(f"{API_PREFIX}/docs", include_in_schema=False)
async def custom_docs():
    return get_swagger_ui_html(
        openapi_url=OPENAPI_URL,
        title="Documentação da API - PRISMA UNIRIO",
    )


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
