from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send

from app.state import ResearchState
from app.nodes.planner import planner_node
from app.nodes.researcher import researcher_node
from app.nodes.synthesizer import synthesizer_node
from app.nodes.citations import citation_node


def fan_out(state: ResearchState) -> list[Send]:
    return [
        Send("researcher", {"company": state["company"], "sub_task": t})
        for t in state["sub_tasks"]
    ]


def build_graph(*, with_checkpointer: bool = False):
    """
    with_checkpointer=True enables aget_state() lookups by thread_id.
    The FastAPI server needs this; the CLI doesn't.
    """
    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("citation", citation_node)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", fan_out)
    graph.add_edge("researcher", "synthesizer")
    graph.add_edge("synthesizer", "citation")
    graph.add_edge("citation", END)

    checkpointer = MemorySaver() if with_checkpointer else None
    return graph.compile(checkpointer=checkpointer)