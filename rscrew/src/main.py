from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

app = FastAPI(
    title="Test Simple Request",
    description="Simple test request implementation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/test")
async def test_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle test request"""
    return {
        "status": "success",
        "message": "Request processed successfully",
        "data": payload
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)