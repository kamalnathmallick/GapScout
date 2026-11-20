"""Bridge module to run LLM outreach & enrichment evals inside API test suite."""

from evals.test_enrichment_evals import (
    test_eval_prompt_injection_safety_tags,
    test_eval_review_themes_schema,
    test_eval_website_audit_schema_and_score_bounds,
)
from evals.test_outreach_evals import (
    offer_profile,
    sample_place,
    test_eval_channel_length_caps,
    test_eval_grounded_citation_from_review_themes,
    test_eval_mandatory_opt_out_presence,
    test_eval_no_hallucinated_metrics,
    test_eval_prompt_injection_resistance,
)

__all__ = [
    "offer_profile",
    "sample_place",
    "test_eval_channel_length_caps",
    "test_eval_grounded_citation_from_review_themes",
    "test_eval_mandatory_opt_out_presence",
    "test_eval_no_hallucinated_metrics",
    "test_eval_prompt_injection_resistance",
    "test_eval_prompt_injection_safety_tags",
    "test_eval_review_themes_schema",
    "test_eval_website_audit_schema_and_score_bounds",
]
