import os
from typing import TypedDict

from langgraph.graph import StateGraph
from openai import OpenAI

from agents import dance_agent, booking_agent
from prompts.router_prompt import build_router_prompt


class GraphState(TypedDict):
    user_input: str
    intent: str
    response: str


def router_node(state: GraphState) -> GraphState:
    prompt_text = build_router_prompt(state["user_input"])

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    openai_model = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")

    intent = "dance_analysis"
    if openai_api_key:
        try:
            client = OpenAI(api_key=openai_api_key)
            resp = client.responses.create(
                model=openai_model,
                input=[{"role": "user", "content": [{"type": "input_text", "text": prompt_text}]}],
                text={"format": {"type": "text"}, "verbosity": "medium"},
                reasoning={"effort": "medium", "summary": "auto"},
                store=False,
            )

            # extract intent text robustly from resp.output
            try:
                outputs = getattr(resp, "output", None) or resp.get("output", [])
                for out in outputs:
                    contents = getattr(out, "content", None) if hasattr(out, "content") else out.get("content", [])
                    if not contents:
                        continue
                    for c in contents:
                        if isinstance(c, dict):
                            t = c.get("text")
                        else:
                            t = getattr(c, "text", None)
                        if t:
                            intent_text = t.strip()
                            if intent_text in {"dance_analysis", "room_booking"}:
                                intent = intent_text
                                break
                    if intent != "dance_analysis":
                        break
            except Exception:
                pass

        except Exception:
            intent = "room_booking" if "練習室" in state["user_input"] or "房間" in state["user_input"] else "dance_analysis"
    else:
        intent = "room_booking" if any(keyword in state["user_input"] for keyword in ["練習室", "練舞室", "房間", "預約", "可預約", "場地"]) else "dance_analysis"

    return {"intent": intent}


def route_after_router(state: GraphState) -> str:
    return state["intent"]


def dance_node(state: GraphState) -> GraphState:
    return {"response": dance_agent.analyze_dance(state["user_input"])}


def booking_node(state: GraphState) -> GraphState:
    return {"response": booking_agent.mock_response(state["user_input"])}


graph = StateGraph(state_schema=GraphState)
graph.add_node("router", router_node)
graph.add_node("dance", dance_node)
graph.add_node("booking", booking_node)
graph.set_entry_point("router")
graph.set_finish_point("dance")
graph.set_finish_point("booking")
graph.add_conditional_edges(
    "router",
    route_after_router,
    {"dance_analysis": "dance", "room_booking": "booking"},
)
compiled_graph = graph.compile()


def run_graph(user_input: str) -> str:
    state = compiled_graph.invoke({"user_input": user_input})
    return state.get("response", "無回應")
