"""DisputeSentry AI application entrypoint."""

from fastapi import FastAPI

from app import __version__
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

    # Mount API routers
    application.include_router(webhooks_router)

    return application


app = create_app()
