import os
import uuid
import time
import datetime
from anthropic import Anthropic

from services import agent_service
from services.tools.web_search_tool import WebSearchTool
from services.tools.fetch_page_tool import FetchPageTool

from models.trace_model import TracesModel
from models.run_model import RunsModel
from models.run_step_model import RunStepsModel

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

TOOL_REGISTRY = {
    "web_search": WebSearchTool(),
    "fetch_page": FetchPageTool(),
}

tools = [
    {
        "name": "web_search",
        "description": "Search the web for current information.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }
    },
    {
        "name": "fetch_page",
        "description": "Fetch the full text content of a web page by URL.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    }
]

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

def run_agent(question, agent_id, db):

    agent = agent_service.get_agent_by_id(agent_id, db)
    if agent is None:
        return {"answer": None, "truncated": False, "message": "Agent not found."}

    max_steps = agent.max_steps
    allowed_tools = [t for t in tools if t["name"] in agent.tools]
        
    # Create trace data
    trace = TracesModel(
        id = str(uuid.uuid4()),
        agent_id = agent_id,
        input = question,
        status = "running"
    )

    db.add(trace)
    db.commit()

    # Create run data
    run = RunsModel(
        id = str(uuid.uuid4()),
        trace_id = trace.id,
        model_name = agent.model,
        status = "running",
    )

    db.add(run)
    db.commit()

    messages = [{"role": "user", "content": question}]
    step = 0
    step_index = 0
    input_tokens = 0
    output_tokens = 0
    completed = False

    while step < max_steps:
        # PROMPT CACHING: mark the newest point in the
        # conversation history as a cache breakpoint.
        #
        # `messages` grows every iteration (tool results get appended),
        # and the ENTIRE history is re-sent to the API on every call.
        # By marking the last message, we tell Anthropic: "cache everything
        # up to here." On the NEXT call, all of that prefix is read from
        # cache at ~90% discount instead of being processed at full price.
        #
        # The isinstance check: only list-style content (like our
        # tool_result messages) can carry a cache marker. The very first
        # user message is a plain string, so it's skipped, which is fine.
        # It's tiny, and caching needs ~1024+ tokens to activate anyway.
        if isinstance(messages[-1]["content"], list):
            messages[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}

        response = client.messages.create(
            model = agent.model,
            max_tokens = 5000,
            # PROMPT CACHING: cache the stable prefix.
            #
            # The request is assembled in order: tools -> system -> messages.
            # A cache marker caches everything UP TO its position, so this
            # marker on the system prompt also covers the tool definitions
            # above it. Tools + system prompt never change between calls,
            # so after the first call they're always a cache hit, for every
            # subsequent call in every run of this agent.
            #
            # "ephemeral" = the cache entry lives ~5 minutes, refreshed on
            # each use. Our loop iterates within seconds, so it never expires
            # mid-run.
            system=[
                {
                    "type": "text",
                    "text": agent.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools = allowed_tools,
            messages = messages
        )

        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
        print(f"tokens — in: {response.usage.input_tokens}, cache_read: {cache_read}, cache_write: {cache_write}")

    
        if response.stop_reason == "tool_use":
            # Save Claude's response to history
            messages.append({"role": "assistant", "content": response.content})

            # findAll tool_use blocks, not just the first
            tool_uses = [b for b in response.content if b.type == "tool_use"]

            tool_results = []
            # Find what tool Claude wants + its input
            for i, tool_use in enumerate(tool_uses):
                tool_name = tool_use.name
                tool_input = tool_use.input

                print(f"Step {step}.{i}: Claude called {tool_name} with {tool_input}")

                # Run the actual tool
                tool = TOOL_REGISTRY[tool_name]
                start = time.time()
                try:
                    result = tool.run(**tool_input)
                    is_error = False
                except Exception as e:
                    result = f"Tool failed: {e}"
                    is_error = True
                
                latency_ms = int((time.time() - start) * 1000)
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": str(result),
                    "is_error": is_error,
                })

                # Save step
                run_step = RunStepsModel(
                    id=str(uuid.uuid4()),
                    run_id=run.id,
                    step_index=step_index,
                    type="tool_call",
                    name=tool_name,
                    input_payload=tool_input,
                    output_payload={"result": str(result)},
                    status="failed" if is_error else "success",
                    latency_ms=latency_ms,
                    error=str(result) if is_error else None,
                )
                db.add(run_step)
                db.commit()

                step_index += 1

            # Send the result back to Claude in one message
            messages.append({"role": "user", "content": tool_results})
        elif response.stop_reason == "end_turn":
            completed = True
            break
        elif response.stop_reason == "max_tokens":
            finish(db, trace, run, "failed", input_tokens, output_tokens)
            return {
                "answer": None,
                "message": "Sorry, that's a big question. I'm on a budget and my token allowance ran out mid-thought 🥹",
                "truncated": True,
            }
        else:
            raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")
    
        step += 1

    if not completed:
        finish(db, trace, run, "failed", input_tokens, output_tokens)
        return {
            "answer": None,
            "truncated": False,
            "message": " couldn't finish that one, ran out of steps while researching 😞."
        }

    finish(db, trace, run, "success", input_tokens, output_tokens)

    return {
        "answer": response.content[0].text,
        "truncated": False,
    }