import os
import time
import uuid
from typing import Annotated, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from models.run_step_model import RunStepsModel
from services.tools.langchain_tools import LC_TOOL_REGISTRY


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    step: int
    step_index: int
    input_tokens: int
    output_tokens: int
    stop_reason: str


def _apply_cache_breakpoint(messages: list[BaseMessage]) -> None:
    # PROMPT CACHING: mark the newest message as a cache breakpoint on every
    # loop iteration. `messages` grows each step (assistant + tool results
    # get appended), and the ENTIRE history is re-sent to Anthropic on every
    # call. Marking the latest tells the API "cache everything up to here";
    # the next call reads that prefix at ~90% discount.
    #
    # Anthropic allows max 4 cache_control blocks per request, so we strip
    # stale markers from earlier iterations first — the newest marker's
    # prefix covers everything before it anyway.
    for msg in messages:
        content = msg.content
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and "cache_control" in block:
                    del block["cache_control"]

    last = messages[-1]
    if isinstance(last.content, list) and last.content:
        block = last.content[-1]
        if isinstance(block, dict):
            block["cache_control"] = {"type": "ephemeral"}
        else:
            last.content[-1] = {"type": "text", "text": str(block), "cache_control": {"type": "ephemeral"}}
    elif isinstance(last.content, str):
        last.content = [
            {"type": "text", "text": last.content, "cache_control": {"type": "ephemeral"}}
        ]


def build_graph(agent, db, run):
    allowed_tools = [LC_TOOL_REGISTRY[name] for name in agent.tools if name in LC_TOOL_REGISTRY]

    # PROMPT CACHING: cache the stable prefix (tools + system prompt).
    # The request is assembled tools -> system -> messages, so a cache marker
    # on the system prompt also covers the tool definitions above it. Tools
    # and system prompt never change between calls, so after the first call
    # they're always a cache hit for every subsequent call in this run.
    system = SystemMessage(
        content=[
            {
                "type": "text",
                "text": agent.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    )

    model = ChatAnthropic(
        model=agent.model,
        max_tokens=5000,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    ).bind_tools(allowed_tools)

    def call_model(state: AgentState) -> dict:
        messages = state["messages"]
        _apply_cache_breakpoint(messages)

        response: AIMessage = model.invoke([system] + messages)

        usage = response.usage_metadata or {}
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        cache_read = (usage.get("input_token_details") or {}).get("cache_read", 0)
        cache_write = (usage.get("input_token_details") or {}).get("cache_creation", 0)
        print(f"tokens — in: {in_tok}, cache_read: {cache_read}, cache_write: {cache_write}")

        stop_reason = (response.response_metadata or {}).get("stop_reason", "end_turn")

        return {
            "messages": [response],
            "input_tokens": state["input_tokens"] + in_tok,
            "output_tokens": state["output_tokens"] + out_tok,
            "step": state["step"] + 1,
            "stop_reason": stop_reason,
        }

    def execute_tools(state: AgentState) -> dict:
        last: AIMessage = state["messages"][-1]
        step_index = state["step_index"]
        tool_messages: list[ToolMessage] = []

        for i, call in enumerate(last.tool_calls):
            name = call["name"]
            args = call["args"]
            print(f"Step {state['step']}.{i}: model called {name} with {args}")

            tool = LC_TOOL_REGISTRY[name]
            start = time.time()
            try:
                result = tool.invoke(args)
                is_error = False
            except Exception as e:
                result = f"Tool failed: {e}"
                is_error = True

            latency_ms = int((time.time() - start) * 1000)

            tool_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=call["id"],
                    status="error" if is_error else "success",
                )
            )

            db.add(
                RunStepsModel(
                    id=str(uuid.uuid4()),
                    run_id=run.id,
                    step_index=step_index,
                    type="tool_call",
                    name=name,
                    input_payload=args,
                    output_payload={"result": str(result)},
                    status="failed" if is_error else "success",
                    latency_ms=latency_ms,
                    error=str(result) if is_error else None,
                )
            )
            db.commit()
            step_index += 1

        return {"messages": tool_messages, "step_index": step_index}

    def should_continue(state: AgentState) -> str:
        if state["step"] >= agent.max_steps:
            return END
        if state["stop_reason"] == "max_tokens":
            return END
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("model", call_model)
    graph.add_node("tools", execute_tools)
    graph.set_entry_point("model")
    graph.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "model")

    return graph.compile()


def run_graph(question: str, agent, db, run):
    compiled = build_graph(agent, db, run)
    initial: AgentState = {
        "messages": [HumanMessage(content=question)],
        "step": 0,
        "step_index": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "stop_reason": "",
    }
    # recursion_limit must exceed 2 * max_steps (model + tools per step) plus a bit.
    final = compiled.invoke(initial, config={"recursion_limit": agent.max_steps * 2 + 5})
    return final
