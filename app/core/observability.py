import logging
from app.core.utils import _settings

logger = logging.getLogger(__name__)


def setup_observability():
    if not _settings.PHOENIX_ENABLED:
        logger.info("Phoenix observability disabled. Skipping initialization.")
        return 
    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor
        from phoenix.otel import register

        tracer_provider = register(
            project_name="thelook-genai-agent",
            endpoint=_settings.PHOENIX_COLLECTOR_ENDPOINT,
        )
        GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("Arize Phoenix tracing enabled -> %s", _settings.PHOENIX_COLLECTOR_ENDPOINT)
    except Exception:  # noqa: BLE001 — observability must never crash the app
        logger.exception("Failed to initialize Phoenix tracing; continuing without it.")

