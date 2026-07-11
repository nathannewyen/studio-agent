from fastapi import APIRouter
from schemas.run_schema import RunRequest
from services.engine_service import run_agent

router = APIRouter(prefix="/v1/run")

@router.post("/")
def run(req: RunRequest):
    return run_agent(req.question)