"""Johnny-Johnny FastAPI application."""

from fastapi import FastAPI

from johnny_johnny_agent.api.errors import install_exception_handlers
from johnny_johnny_agent.api.routes import PROJECT_VERSION, router


def create_app() -> FastAPI:
    application = FastAPI(
        title="Johnny-Johnny Agent",
        version=PROJECT_VERSION,
        description=(
            "Typed REST adapter over the same PostgreSQL-backed application "
            "workflows used by the Johnny-Johnny CLI."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    install_exception_handlers(application)
    application.include_router(router)

    @application.get("/hello", include_in_schema=False)
    def hello() -> dict[str, str]:
        return {"message": "Hello from Johnny-Johnny"}

    return application


app = create_app()
