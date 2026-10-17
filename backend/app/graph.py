from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send

from app.state import ResearchState
from app.nodes.planner import planner_node
from app.nodes.researcher import researcher_node
from app.nodes.synthesizer import synthesizer_node
from app.nodes.citations import citation_node
from app.nodes.redflag_scorer import redflag_scorer_node


def fan_out(state: ResearchState) -> list[Send]:
    return [
        Send("researcher", {
            "company": state["company"],
            "mode": state.get("mode", "competitive"),
            "sub_task": t,
        })
        for t in state["sub_tasks"]
    ]

def route_by_mode(state: ResearchState) -> str:
    """
    Conditional edge: after researchers join, pick the next node by mode.
    Returning a node NAME (string) means "go there" — this is the routing
    form of add_conditional_edges, distinct from the Send-list form
    used for fan-out above.
    """
    if state.get("mode") == "employer":
        return "redflag_scorer"
    return "synthesizer"



def build_graph(*, with_checkpointer: bool = False):
    """
    with_checkpointer=True enables aget_state() lookups by thread_id.
    The FastAPI server needs this; the CLI doesn't.
    """
    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("redflag_scorer", redflag_scorer_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("citation", citation_node)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", fan_out)

    # Mode Router
    graph.add_conditional_edges("researcher", route_by_mode, {
        "redflag_scorer": "redflag_scorer",
        "synthesizer": "synthesizer",
    })
    
    graph.add_edge("researcher", "synthesizer")
    graph.add_edge("synthesizer", "citation")
    graph.add_edge("citation", END)

    checkpointer = MemorySaver() if with_checkpointer else None
    return graph.compile(checkpointer=checkpointer)