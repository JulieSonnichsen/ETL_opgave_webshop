from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI

from app.fault_engine import FaultEngine
from app.routes.products import router as products_router
from app.routes.specifications import router as specifications_router


def create_app(
    fault_mode: str = "normal",
    fault_options: Mapping[str, Mapping[str, Any]] | None = None,
) -> FastAPI:
    application = FastAPI(title="Product API")
    application.include_router(products_router)
    application.include_router(specifications_router)
    application.add_middleware(
        FaultEngine,
        mode=fault_mode,
        fault_options=fault_options,
    )
    return application


app = create_app()
