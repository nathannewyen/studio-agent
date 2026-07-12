from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import get_db
from models.trace_model import TracesModel
from models.run_model import RunsModel
from models.run_step_model import RunStepsModel

router = APIRouter(prefix="/v1/traces")


@router.get("/{id}")
def get_trace(id: str, db: Session = Depends(get_db)):
    trace = db.query(TracesModel).filter(TracesModel.id == id).first()
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

    run = db.query(RunsModel).filter(RunsModel.trace_id == trace.id).first()

    return {
        "id": trace.id,
        "agent_id": trace.agent_id,
        "input": trace.input,
        "status": trace.status,
        "source": trace.source,
        "started_at": trace.started_at,
        "finished_at": trace.finished_at,
        "run": {
            "id": run.id,
            "model_name": run.model_name,
            "input_tokens": run.input_tokens,
            "output_tokens": run.output_tokens,
            "total_tokens": run.total_tokens,
        } if run else None,
    }


@router.get("/{id}/steps")
def get_trace_steps(id: str, db: Session = Depends(get_db)):
    trace = db.query(TracesModel).filter(TracesModel.id == id).first()
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

    run = db.query(RunsModel).filter(RunsModel.trace_id == trace.id).first()
    if run is None:
        return {"steps": []}

    steps = db.query(RunStepsModel).filter(RunStepsModel.run_id == run.id)\
              .order_by(RunStepsModel.step_index).all()

    return {
        "steps": [
            {
                "index": s.step_index,
                "type": s.type,
                "name": s.name,
                "input": s.input_payload,
                "output": s.output_payload,
                "status": s.status,
                "latency_ms": s.latency_ms,
                "error": s.error,
            }
            for s in steps
        ]
    }