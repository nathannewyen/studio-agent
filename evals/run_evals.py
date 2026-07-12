import json
import sys
import datetime

sys.path.append(".")  # so imports work when run from project root

from models.trace_model import TracesModel
from models.run_model import RunsModel
from models.run_step_model import RunStepsModel

from dotenv import load_dotenv
load_dotenv()

from database.database import SessionLocal
from services.engine_service import run_agent, client

AGENT_ID = "2fd51d12-aa3c-493e-b62c-bf0555da21c7"  # your Research Agent

JUDGE_PROMPT = """You are grading a research agent's answer for FAITHFULNESS TO ITS EVIDENCE.

The agent searched the live web. Its knowledge is MORE CURRENT than yours — do NOT
penalize facts, dates, or versions that are newer than your training data.

Question: {question}
Expected qualities: {expect}

EVIDENCE the agent gathered (actual tool outputs):
{evidence}

Agent's answer: {answer}

Score 1-5 based ONLY on:
- Is every claim in the answer supported by the evidence above?
- Does it directly address the question?
- Does it cite/attribute sources?
- Is it internally consistent?

A 1 means: claims NOT found in the evidence (true fabrication).
Reply ONLY with JSON: {{"score": <1-5>, "reasoning": "<one sentence>"}}"""

def get_evidence(db, question):
    trace = db.query(TracesModel).filter(TracesModel.input == question)\
              .order_by(TracesModel.started_at.desc()).first()
    run = db.query(RunsModel).filter(RunsModel.trace_id == trace.id).first()
    steps = db.query(RunStepsModel).filter(RunStepsModel.run_id == run.id)\
              .order_by(RunStepsModel.step_index).all()
    return "\n\n".join(
        f"[{s.name}] input: {s.input_payload}\noutput: {str(s.output_payload)[:1500]}"
        for s in steps
    )


def judge(question, expect, answer, evidence):
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(
            question=question, expect=expect, answer=answer, evidence=evidence
        )}],
    )
    text = response.content[0].text.strip()
    # strip markdown fences if the model added them
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def main():
    with open("evals/eval_set.json") as f:
        eval_set = json.load(f)

    db = SessionLocal()
    results = []

    for case in eval_set:
        print(f"\n=== Running: {case['id']} ===")
        result = run_agent(case["question"], AGENT_ID, db)
        answer = result.get("answer") or f"[NO ANSWER: {result.get('message')}]"

        evidence = get_evidence(db, case["question"])
        grade = judge(case["question"], case["expect"], answer, evidence)

        print(f"Score: {grade['score']} — {grade['reasoning']}")

        results.append({
            "id": case["id"],
            "score": grade["score"],
            "reasoning": grade["reasoning"],
        })

    db.close()

    avg = sum(r["score"] for r in results) / len(results)
    print(f"\n{'='*40}\nAVERAGE SCORE: {avg:.2f}")

    # save timestamped results for before/after comparison
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"evals/results_{stamp}.json", "w") as f:
        json.dump({"average": avg, "results": results}, f, indent=2)


if __name__ == "__main__":
    main()