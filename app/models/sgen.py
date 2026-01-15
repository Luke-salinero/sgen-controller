from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SGenSubmitRequest(BaseModel):
    """
    Public request model for submitting an SGen job.

    This is treated as an opaque config by sgen-controller.
    Validation here is structural, not semantic.
    """

    # execution mode
    mode: str = Field(
        default="mock",
        description="Execution mode: mock or live",
        examples=["mock", "live"],
    )

    # opaque configuration payload for sgen
    config: Dict[str, Any] = Field(
        ...,
        description="Opaque configuration passed directly to sgen",
    )

    # optional metadata (future-proofing)
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional user or system metadata",
    )


class SGenSubmitResponse(BaseModel):
    """
    This model exists for symmetry and documentation only.

    The controller actually returns JobCreatedResponse / JobResultResponse,
    but keeping this here avoids confusion when comparing with the gateway.
    """

    job_id: str
    status: str
    mode: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
