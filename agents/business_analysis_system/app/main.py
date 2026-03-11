from fastapi import FastAPI

from app.core.config import APP_DESCRIPTION, APP_NAME, APP_VERSION
from app.core.init_db import init_db
from app.modules.data_input.routes import router as data_input_router
from app.modules.contract_parsing.routes import router as contract_parsing_router

def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description=APP_DESCRIPTION,
    )

    @app.on_event("startup")
    def on_startup():
        init_db()

    @app.get("/health")
    def health_check():
        return {
            "status": "ok",
            "service": "business_analysis_system",
            "version": APP_VERSION,
        }

    app.include_router(data_input_router)
    app.include_router(contract_parsing_router) 
    return app


app = create_app()