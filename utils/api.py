from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json
from typing import List, Optional, Dict
import os
from .config import Config
from .grading import GradingSystem

app = FastAPI(title="Assignment Grading API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize grading system
grading_system = GradingSystem()

# Request/Response Models
class GradingRequest(BaseModel):
    student_solution: str
    ideal_solution: str
    grading_instructions: str
    model: str = Config.DEFAULT_MODEL

class ModelResponse(BaseModel):
    model: str
    response: str
    total_duration: Optional[int]
    eval_count: Optional[int]
    eval_duration: Optional[int]

class GradingResponse(BaseModel):
    score: float
    feedback: str
    improvements: List[str]

class APIResponse(BaseModel):
    status: str
    data: Dict
    message: str

class HealthResponse(BaseModel):
    status: str
    models: List[str]

# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint that also returns available models"""
    return {
        "status": "healthy",
        "models": Config.AVAILABLE_MODELS
    }

@app.post("/api/grade", response_model=APIResponse)
async def grade_submission(request: GradingRequest, background_tasks: BackgroundTasks):
    """Grade a submission using the local LLM API"""
    try:
        # Use the improved GradingSystem for evaluation
        grading_result = grading_system.evaluate_submission(
            student_solution=request.student_solution,
            ideal_solution=request.ideal_solution,
            grading_instructions=request.grading_instructions,
            model=request.model
        )

        return APIResponse(
            status="success",
            data=grading_result,
            message="Grading completed successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Grading failed: {str(e)}"
        )

@app.get("/api/models")
async def list_models():
    """List available models from local Ollama instance"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if not response.ok:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch models"
            )
        
        return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch models: {str(e)}"
        )
