from fastapi import FastAPI

from app.core.config import APP_DESCRIPTION, APP_NAME, APP_VERSION
from app.core.init_db import init_db
from app.modules.data_input.routes import router as data_input_router
from app.modules.contract_parsing.routes import router as contract_parsing_router
from app.modules.product_split.routes import router as product_split_router
from app.modules.phase_income_calc.routes import router as phase_income_calc_router
from app.modules.result_storage.routes import router as result_storage_router
from app.modules.query_display.routes import router as query_display_router

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
    app.include_router(product_split_router)
    app.include_router(phase_income_calc_router)
    app.include_router(result_storage_router)
    app.include_router(query_display_router)
    return app


app = create_app()