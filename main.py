from contextlib import asynccontextmanager
from fastapi.openapi.docs import get_swagger_ui_html
from core.postgresql.postgresql import postgresql
from core.rabbitmq.rabbitmq import rabbitmq
from fastapi import FastAPI

from core.redis.redis_cache import redis_cache
from routes.auth.router import router as auth_router
from routes.users.router import router as users_router


from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando conexões...")
    await postgresql.connect()
    await redis_cache.connect()
    await rabbitmq.connect()
    print("✅ Todos os serviços conectados com sucesso!")

    yield

    print("Encerrando conexões...")
    await postgresql.disconnect()
    await redis_cache.disconnect()
    await rabbitmq.disconnect()
    print("✅ Todos os serviços desconectados com sucesso!")


app = FastAPI(lifespan=lifespan, openapi_url="/api/v1/unirio/openapi.json", root_path="/api/v1/unirio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])

@app.get("/api/v1/unirio/docs", include_in_schema=False)
async def custom_docs():
    return get_swagger_ui_html(
        openapi_url="/api/v1/unirio/openapi.json",
        title="Documentação da API - Extensao Unirio",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
