"""Schemas for voice enrollment endpoints."""

from pydantic import BaseModel


class EnrollResponse(BaseModel):
    """Response from voice enrollment endpoint."""

    success: bool
    message: str


class EnrollErrorResponse(BaseModel):
    """Error response from voice enrollment endpoint."""

    success: bool = False
    error: str
    error_code: str
