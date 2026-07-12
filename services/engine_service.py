import uuid
import datetime

from anthropic import APIError
from langchain_core.messages import AIMessage

from services import agent_service
from services.graph_service import run_graph

from models.trace_model import TracesModel
from models.run_model import RunsModel
from models.run_step_model import RunStepsModel


def _friendly_anthropic_message(err: APIError) -> str:
    status = getattr(err, "status_code", None)
    body = getattr(err, "body", None) or {}
    detail = (body.get("error") or {}).get("message", "") if isinstance(body, dict) else ""

    if status == 400 and "credit balance is too low" in detail.lower():
        return "Model provider ran out of credits"
    if status == 401:
        return "Model provider rejected the API key."
    if status == 429:
        return "Model provider rate-limited us. Try again in a moment."
    if status in (500, 502, 503, 529):
        return "Model provider is overloaded. Try again in a moment."
    return f"Model call failed ({status or 'unknown'}): {detail or str(err)}"


def finish(db, trace, run, status, input_tokens=0, output_tokens=0):
    now = datetime.datetime.now(datetime.UTC)
    trace.status = status
    trace.finished_at = now
    run.status = status
    run.finished_at = now
    run.input_tokens = input_tokens
    run.output_tokens = output_tokens
    run.total_tokens = input_tokens + output_tokens
    db.commit()


def _extract_answer(final_message: AIMessage) -> str:
    content = final_message.content
    if isinstance(content, str):
        return content
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            return block.get("text", "")
    return ""


def run_agent(question, agent_id, db, source="api"):
    agent = agent_service.get_agent_by_id(agent_id, db)
    if agent is None:
        return {"answer": None, "truncated": False, "message": "Agent not found."}

    trace = TracesModel(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        input=question,
        status="running",
        source=source,
    )
    db.add(trace)
    db.commit()

    run = RunsModel(
        id=str(uuid.uuid4()),
        trace_id=trace.id,
        model_name=agent.model,
        status="running",
    )
    db.add(run)
    db.commit()

    try:
        final_state = run_graph(question, agent, db, run)
    except APIError as e:
        finish(db, trace, run, "failed", 0, 0)
        return {
            "answer": None,
            "truncated": False,
            "message": _friendly_anthropic_message(e),
            "trace_id": trace.id,
            "run_id": run.id,
        }

    input_tokens = final_state["input_tokens"]
    output_tokens = final_state["output_tokens"]
    last = final_state["messages"][-1]
    stop_reason = final_state.get("stop_reason", "end_turn")

    if stop_reason == "max_tokens":
        finish(db, trace, run, "failed", input_tokens, output_tokens)
        return {
            "answer": None,
            "message": "Sorry, that's a big question. I'm on a budget and my token allowance ran out mid-thought 🥹",
            "truncated": True,
            "trace_id": trace.id,
            "run_id": run.id,
        }

    completed = isinstance(last, AIMessage) and not last.tool_calls
    if not completed:
        finish(db, trace, run, "failed", input_tokens, output_tokens)
        return {
            "answer": None,
            "truncated": False,
            "message": " couldn't finish that one, ran out of steps while researching 😞.",
            "trace_id": trace.id,
            "run_id": run.id,
        }

    finish(db, trace, run, "success", input_tokens, output_tokens)

    steps = (
        db.query(RunStepsModel)
        .filter(RunStepsModel.run_id == run.id)
        .order_by(RunStepsModel.step_index)
        .all()
    )

    return {
        "answer": _extract_answer(last),
        "truncated": False,
        "trace_id": trace.id,
        "run_id": run.id,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
        "steps": [
            {
                "index": s.step_index,
                "type": s.type,
                "name": s.name,
                "input": s.input_payload,
                "output": s.output_payload,
                "status": s.status,
                "latency_ms": s.latency_ms,
            }
            for s in steps
        ],
    }
