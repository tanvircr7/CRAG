from pathlib import Path
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

def get_project_root() -> Path:
    """Get the project root directory in a platform-agnostic way."""
    current_file = Path(__file__)  # Gets the path of the current file (retriever.py)
    # Go up twice: components -> src -> project_root
    project_root = current_file.parent.parent.parent
    return project_root

def create_index():
    """Create document index from PDF files in the data directory."""
    # Get paths
    project_root = get_project_root()
    data_dir = project_root / "data"
    
    # Verify data directory exists
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found at {data_dir}")
    
    # List all PDF files
    pdf_files = list(data_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {data_dir}")
    
    # Take first two PDFs (as in original code)
    if len(pdf_files) > 1:
        pdf_files = pdf_files[:2]
    
    # Load documents
    docs = []
    for pdf_file in pdf_files:
        try:
            loader = PyPDFLoader(str(pdf_file))
            docs.extend(loader.load())
        except Exception as e:
            print(f"Error loading {pdf_file}: {str(e)}")
            continue
    
    if not docs:
        raise ValueError("No documents were successfully loaded")
    
    print(f"Number of documents loaded: {len(docs)}")

    # Process documents
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=250, 
        chunk_overlap=0
    )
    doc_splits = text_splitter.split_documents(docs)

    # Create and return vectorstore
    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name="rag-chroma",
        embedding=OpenAIEmbeddings(),
    )
    
    return vectorstore.as_retriever()


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
