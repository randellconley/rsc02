from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class TestRequest(BaseModel):
    """Test request model with validation"""
    test_id: str = Field(..., description="Unique test identifier")
    payload: Dict[str, Any] = Field(..., description="Test request payload")
    metadata: Dict[str, str] = Field(
        ...,
        description="Request metadata",
        example={
            "timestamp": "2025-01-01T00:00:00Z",
            "version": "1.0"
        }
    )

    class Config:
        schema_extra = {
            "example": {
                "test_id": "test-123",
                "payload": {
                    "field1": "value1",
                    "field2": "value2"
                },
                "metadata": {
                    "timestamp": "2025-01-01T00:00:00Z",
                    "version": "1.0"
                }
            }
        }

class TestResponse(BaseModel):
    """Test response model"""
    status: str = Field(..., description="Response status (success/error)")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[Dict[str, str]] = Field(None, description="Error details if any")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "result": "Operation completed",
                    "timestamp": "2025-01-01T00:00:00Z"
                },
                "error": None
            }
        }