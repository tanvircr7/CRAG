import os
from getpass import getpass

from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

import os
from dotenv import load_dotenv

'''
# # Load environment variables from .env file
# load_dotenv()

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
# if not OPENAI_API_KEY:
#     raise ValueError("No OPENAI_API_KEY found in environment or .env file.")
# os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# # Securely get API keys (user prompt or env vars)
# def get_api_key(key_name):
#     return os.environ.get(key_name) or getpass(f"Enter {key_name}: ")

# os.environ["OPENAI_API_KEY"] = get_api_key("OPENAI_API_KEY")


'''
# ---------- SECTION 1: SETUP & ENVIRONMENT ----------
import os
from typing import List, Dict, Any, TypedDict, Literal, Union
from dotenv import load_dotenv
from pprint import pprint

# Load environment variables
load_dotenv()

def _set_env(env_var: str):
    """Set environment variable if not already set."""
    if not os.getenv(env_var):
        os.environ[env_var] = input(f"Enter {env_var}: ")
    print(f"{env_var}: {'•' * 10}")  # Hide actual key values

# Set required API keys
_set_env("OPENAI_API_KEY")
_set_env("TAVILY_API_KEY")

# CREATE INDEX -----------------------------------------------------------------------------------------------
def create_index_URL():
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import WebBaseLoader
    from langchain_community.vectorstores import Chroma
    from langchain_openai import OpenAIEmbeddings

    urls = [
        "https://lilianweng.github.io/posts/2023-06-23-agent/",
        # "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/",
        # "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/",
    ]

    docs = [WebBaseLoader(url).load() for url in urls]
    # print("DOCS")
    # print(docs)
    docs_list = [item for sublist in docs for item in sublist]
    # print("List")
    # print(docs)
    print("Docs length")
    print(f"Size of docs (number of sublists): {len(docs)}")
    print(f"Size of docs (number of sublists): {len(docs_list)}")

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=250, chunk_overlap=0
    )
    doc_splits = text_splitter.split_documents(docs_list)

    # Add to vectorDB
    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name="rag-chroma",
        embedding=OpenAIEmbeddings(),
    )
    retriever = vectorstore.as_retriever()

    return retriever

def create_index():
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.vectorstores import Chroma
    from langchain_openai import OpenAIEmbeddings
    import os
    from pathlib import Path

    # Get the current directory
    current_dir = Path(__file__).parent
    data_dir = current_dir / "data"
    
    # List all PDF files in the data directory
    pdf_files = list(data_dir.glob("*.pdf"))
    pdf_files = pdf_files[:2]
    
    docs = []
    for pdf_file in pdf_files:
        loader = PyPDFLoader(str(pdf_file))
        docs.extend(loader.load())
    
    print("Docs length")
    print(f"Number of documents loaded: {len(docs)}")

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=250, chunk_overlap=0
    )
    doc_splits = text_splitter.split_documents(docs)

    # Add to vectorDB
    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name="rag-chroma",
        embedding=OpenAIEmbeddings(),
    )
    retriever = vectorstore.as_retriever()

    return retriever

# LLMS: Retrieval Grader -------------------------------------------------------------------------------------

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI


# Data model
class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""

    binary_score: str = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )

def create_grader():
    # LLM with function call
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)
    structured_llm_grader = llm.with_structured_output(GradeDocuments)

    # Prompt
    system = """You are a grader assessing relevance of a retrieved document to a user question. \n
        If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant. \n
        Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
    grade_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),
        ]
    )

    retrieval_grader = grade_prompt | structured_llm_grader
    
    return retrieval_grader


# RAG CHAIN  -----------------------------------------------------------------------------------------------------
def create_chain():
    ### Generate

    from langchain import hub
    from langchain_core.output_parsers import StrOutputParser

    # Prompt
    prompt = hub.pull("rlm/rag-prompt")

    # LLM
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)


    # Post-processing
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)


    # Chain
    rag_chain = prompt | llm | StrOutputParser()

    return rag_chain


# Re Writer  -----------------------------------------------------------------------------------------------------
def create_rewriter():
    from langchain_core.output_parsers import StrOutputParser

    # LLM
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)

    # Prompt
    system = """You a question re-writer that converts an input question to a better version that is optimized \n
        for web search. Look at the input and try to reason about the underlying semantic intent / meaning."""
    re_write_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            (
                "human",
                "Here is the initial question: \n\n {question} \n Formulate an improved question.",
            ),
        ]
    )

    question_rewriter = re_write_prompt | llm | StrOutputParser()
    return question_rewriter



# Search Tool  ----------------------------------------------------------------------------------------------------
def create_search_tool():
    ### Search
    from langchain_community.tools.tavily_search import TavilySearchResults

    web_search_tool = TavilySearchResults(k=3)  
    return web_search_tool



# Graph State ---------------------------------------------------------------------------------------------------
# Define Graph State

from typing import List

from typing_extensions import TypedDict


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


# Util functions
from langchain.schema import Document


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
from langgraph.graph import END, StateGraph, START

def build_graph():
    """Build and compile the LangGraph."""
    # Define checkpoint configuration - we need to use a properly configured checkpointer
    # Use LocalStateCheckpointer instead of MemorySaver, which seems to be giving errors
    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    
    # Create graph
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
    
    # Compile graph with checkpoint configuration
    # config = {"configurable": {"thread_id": "default_thread", "checkpoint_id": "default"}}
    config = {"configurable": {"thread_id": 2}}
    app = workflow.compile(checkpointer=memory)
    
    return app, config, memory

def stream_graph_updates(graph, user_input: str, config: dict[str, dict[str, str]]):
    # print("1")
    # return 
    # The graph expects 'question' as input key, not 'messages'
    for event in graph.stream({"question": user_input}, config=config):  # Changed input key to 'question'
        # print("EVENT")
        # print(event)
        print("--------------")
        for value in event.values():
            # print("VALUE")
            # print(value)
            print("--------------")
            # Access the generation using the correct key
            print("Assistant:", value.get("generation", "No generation yet."))  # Changed to access generation from value


if __name__ == "__main__":
    print("RAG System Ready (CRAG demo). Type your question or 'exit' to quit.")
    # config = {"configurable": {"thread_id": "2"}}
    app, config, memory = build_graph()
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            stream_graph_updates(app, user_input, config)
            # print(user_input)
        except:
            # fallback if input() is not available
            user_input = "What do you know about LangGraph?"
            print("User: " + user_input)
            stream_graph_updates(app, user_input, config)
            # print(user_input)
            break
