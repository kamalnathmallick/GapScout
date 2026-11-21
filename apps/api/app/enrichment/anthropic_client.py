"""Backward compatibility module re-exporting GeminiClient as AnthropicClient."""

from app.enrichment.gemini_client import (
    AnthropicClient,
    AnthropicEnrichmentError,
    GeminiClient,
    GeminiEnrichmentError,
    extract_json_from_text,
)

__all__ = [
    "AnthropicClient",
    "AnthropicEnrichmentError",
    "GeminiClient",
    "GeminiEnrichmentError",
    "extract_json_from_text",
]
