from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from schemas.run_schema import RunRequest
from services.engine_service import run_agent

router = APIRouter(prefix="/v1/run")

@router.post("/")
def run(req: RunRequest, db: Session = Depends(get_db)):
    return run_agent(req.question, req.agent_id, db)