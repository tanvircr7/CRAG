# Graph State ---------------------------------------------------------------------------------------------------

from typing import List, Dict, Any
from typing_extensions import TypedDict
from langchain.schema import Document

# Import components using correct import syntax
from src.components import (
    create_chain,
    create_grader,
    create_search_tool,
    create_index,
    create_index_URL,
    create_rewriter
)

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        web_search: whether to add search
        documents: list of documents
    """

    question: str
    generation: str
    web_search: str
    documents: List[str]


def retrieve(state):
    """
    Retrieve documents

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    print("---RETRIEVE---")
    question = state["question"]
    retriever = create_index()

    # Retrieval
    documents = retriever.get_relevant_documents(question)
    return {"documents": documents, "question": question}


def generate(state):
    """
    Generate answer

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    print("---GENERATE---")
    question = state["question"]
    documents = state["documents"]
    rag_chain = create_chain()

    # RAG generation
    generation = rag_chain.invoke({"context": documents, "question": question})
    return {"documents": documents, "question": question, "generation": generation}


def grade_documents(state):
    """
    Determines whether the retrieved documents are relevant to the question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates documents key with only filtered relevant documents
    """

    print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state["documents"]
    retrieval_grader = create_grader()

    # Score each doc
    filtered_docs = []
    web_search = "No"
    for d in documents:
        score = retrieval_grader.invoke(
            {"question": question, "document": d.page_content}
        )
        grade = score.binary_score
        if grade == "yes":
            print("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(d)
        else:
            print("---GRADE: DOCUMENT NOT RELEVANT---")
            web_search = "Yes"
            continue
    return {"documents": filtered_docs, "question": question, "web_search": web_search}


def transform_query(state):
    """
    Transform the query to produce a better question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates question key with a re-phrased question
    """

    print("---TRANSFORM QUERY---")
    question = state["question"]
    documents = state["documents"]
    question_rewriter = create_rewriter()

    # Re-write question
    better_question = question_rewriter.invoke({"question": question})
    return {"documents": documents, "question": better_question}


def web_search(state):
    """
    Web search based on the re-phrased question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates documents key with appended web results
    """

    print("---WEB SEARCH---")
    question = state["question"]
    documents = state["documents"]
    web_search_tool = create_search_tool()

    # Web search
    docs = web_search_tool.invoke({"query": question})
    web_results = "\n".join([d["content"] for d in docs])
    web_results = Document(page_content=web_results)
    documents.append(web_results)

    return {"documents": documents, "question": question}


### Edges
def decide_to_generate(state):
    """
    Determines whether to generate an answer, or re-generate a question.

    Args:
        state (dict): The current graph state

    Returns:
        str: Binary decision for next node to call
    """

    print("---ASSESS GRADED DOCUMENTS---")
    state["question"]
    web_search = state["web_search"]
    state["documents"]

    if web_search == "Yes":
        # All documents have been filtered check_relevance
        # We will re-generate a new query
        print(
            "---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY---"
        )
        return "transform_query"
    else:
        # We have relevant documents, so generate answer
        print("---DECISION: GENERATE---")
        return "generate"



# ---------- SECTION 5: BUILD GRAPH ----------
# from langgraph.graph import END, StateGraph, START
# from langgraph.graph import END, StateGraph, START

# def build_graph():
#     """Build and compile the LangGraph."""
#     # Define checkpoint configuration - we need to use a properly configured checkpointer
#     # Use LocalStateCheckpointer instead of MemorySaver, which seems to be giving errors
#     from langgraph.checkpoint.memory import MemorySaver
#     memory = MemorySaver()
    
#     # Create graph
#     workflow = StateGraph(GraphState)
    
#     # Define the nodes
#     workflow.add_node("retrieve", retrieve)
#     workflow.add_node("grade_documents", grade_documents)
#     workflow.add_node("generate", generate)
#     workflow.add_node("transform_query", transform_query)
#     workflow.add_node("web_search_node", web_search)
    
#     # Build graph
#     workflow.add_edge(START, "retrieve")
#     workflow.add_edge("retrieve", "grade_documents")
#     workflow.add_conditional_edges(
#         "grade_documents",
#         decide_to_generate,
#         {
#             "transform_query": "transform_query",
#             "generate": "generate",
#         },
#     )
#     workflow.add_edge("transform_query", "web_search_node")
#     workflow.add_edge("web_search_node", "generate")
#     workflow.add_edge("generate", END)
    
#     # Compile graph with checkpoint configuration
#     # config = {"configurable": {"thread_id": "default_thread", "checkpoint_id": "default"}}
#     config = {"configurable": {"thread_id": 2}}
#     app = workflow.compile(checkpointer=memory)
    
#     return app, config, memory