# Standard library imports
import os
from typing import Dict
# Third-party imports
from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
# Local imports
from src.state.graph_state import (
    GraphState,
    retrieve,
    generate,
    grade_documents,
    transform_query,
    web_search,
    decide_to_generate,
)
from src.utils.environment import setup_environment

def build_graph():
    """Build and compile the LangGraph."""
    memory = MemorySaver()
    workflow = StateGraph(GraphState)
    
    # Define the nodes
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("generate", generate)
    workflow.add_node("transform_query", transform_query)
    workflow.add_node("web_search_node", web_search)
    
    # Build graph
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "transform_query": "transform_query",
            "generate": "generate",
        },
    )
    workflow.add_edge("transform_query", "web_search_node")
    workflow.add_edge("web_search_node", "generate")
    workflow.add_edge("generate", END)
    
    config = {"configurable": {"thread_id": 2}}
    app = workflow.compile(checkpointer=memory)
    
    return app, config, memory

def stream_graph_updates(graph, user_input: str, config: Dict[str, Dict[str, str]]):
    for event in graph.stream({"question": user_input}, config=config):
        print("--------------")
        for value in event.values():
            print("--------------")
            print("Assistant:", value.get("generation", "No generation yet."))

if __name__ == "__main__":
    print("RAG System Ready (CRAG demo). Type your question or 'exit' to quit.")
    setup_environment()
    app, config, memory = build_graph()
    
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            stream_graph_updates(app, user_input, config)
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            user_input = "What do you know about LangGraph?"
            print("User: " + user_input)
            stream_graph_updates(app, user_input, config)
            break
