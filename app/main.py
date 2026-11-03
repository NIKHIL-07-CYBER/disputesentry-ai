"""DisputeSentry AI application entrypoint."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.approvals import router as approvals_router
from app.api.dashboard import router as dashboard_router
from app.api.disputes import router as disputes_router
from app.api.metrics import router as metrics_router
from app.api.webhooks import router as webhooks_router
from app.config import AppConfig, get_config


def create_app(config: AppConfig | None = None) -> FastAPI:
    """Instantiate and configure the FastAPI application.

    Args:
        config: Optional AppConfig instance. If None, default config is loaded.

    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    app_config = config or get_config()

    application = FastAPI(
        title="DisputeSentry AI",
        description=(
            "Automated PayPal dispute detection, evidence assembly, ROI evaluation, "
            "and API resolution."
        ),
        version=__version__,
    )

    application.state.config = app_config

    @application.get("/health")
    def health_check() -> dict[str, str]:
        """Health check endpoint for container and uptime monitoring."""
        return {
            "status": "healthy",
            "service": "disputesentry-ai",
            "version": __version__,
        }

    # Mount static assets
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        application.mount(
            "/static", StaticFiles(directory=str(static_dir)), name="static"
        )

    # Mount API routers
    application.include_router(dashboard_router)
    application.include_router(disputes_router)
    application.include_router(approvals_router)
    application.include_router(metrics_router)
    application.include_router(webhooks_router)

    return application


app = create_app()
