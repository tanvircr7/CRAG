import streamlit as st
from pathlib import Path
import os
from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
from src.state.graph_state import (
    GraphState,
    retrieve,
    generate,
    grade_documents,
    transform_query,
    web_search,
    decide_to_generate,
)
from src.utils.environment import setup_environment, set_env_st
from openai import AuthenticationError, OpenAIError

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

def stream_graph_updates(graph, user_input: str, config: dict):
    """Stream graph updates and return the final response"""
    try:
        responses = []
        for event in graph.stream({"question": user_input}, config=config):
            for value in event.values():
                response = value.get("generation", "No generation yet.")
                responses.append(response)
        return responses[-1] if responses else "No response generated."
        
    except AuthenticationError:
        st.error("API key validation failed during processing.")
        raise AuthenticationError("API key validation failed during processing.")
    except Exception as e:
        st.error(f"Error: {str(e)}.")
        raise Exception(f"Error during graph processing: {str(e)}")

# Set page configuration to wide mode
st.set_page_config(layout="wide")

# Custom CSS for styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton button {
        width: 100%;
    }
    .css-1d391kg {
        padding-top: 1rem;
    }
    .upload-section {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        margin-bottom: 1rem;
    }
    .prompt-section {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        height: 100%;
    }
    .history-section {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        height: 100%;
    }
    </style>
""", unsafe_allow_html=True)

def cleanup_data_folder(force=False):
    """
    Remove all existing files from the data folder
    Args:
        force (bool): If True, removes all files without checking session state
    """
    data_folder = Path("data")
    if data_folder.exists():
        try:
            files_removed = []
            for file in data_folder.glob("*"):
                if file.is_file():
                    # If not force, only remove files not in session state
                    if force or file.name not in st.session_state.get('uploaded_files', []):
                        file.unlink()
                        files_removed.append(file.name)
            
            if files_removed:
                print(f"Removed files: {', '.join(files_removed)}")
            return files_removed
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
            return []

def create_data_folder(clean=False):
    """
    Create a data folder if it doesn't exist
    Args:
        clean (bool): If True, cleans existing files (default: False)
    """
    data_folder = Path("data")
    
    # Only create if it doesn't exist
    if not data_folder.exists():
        data_folder.mkdir(parents=True)
        print("Created new data folder")
    
    # Clean up only if explicitly requested
    elif clean:
        removed_files = cleanup_data_folder(force=True)
        if removed_files:
            if 'uploaded_files' in st.session_state:
                st.session_state.uploaded_files = []
            st.warning(f"Cleaned up existing files: {', '.join(removed_files)}")
    
    return data_folder

def save_uploaded_file(uploaded_file, data_folder):
    """Save the uploaded PDF file to the data folder"""
    if uploaded_file is not None:
        try:
            file_path = data_folder / uploaded_file.name
            
            # Check if file already exists
            if file_path.exists():
                file_path.unlink()  # Remove existing file
                print(f"Replaced existing file: {uploaded_file.name}")
            
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            print(f"Saved file: {uploaded_file.name}")
            return True
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            st.error(f"Error saving file: {str(e)}")
            return False
    return False

def main():
    # Initialize session state
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []
        cleanup_data_folder(force=True)
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    if 'graph' not in st.session_state:
        st.session_state.graph = None
    if 'graph_config' not in st.session_state:
        st.session_state.graph_config = None
    if 'memory' not in st.session_state:
        st.session_state.memory = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []



    # Create three columns with specific ratios
    col1, sep1, col2, sep2, col3 = st.columns([1, 0.2, 4, 0.2, 1])
    
    # Part 1: PDF Upload Section (Left)
    with col1:
        settings_expander = st.expander("📁 Upload & Settings", expanded=True)
        with settings_expander:
            data_folder = create_data_folder(clean=False)
            
            # Display current uploaded files
            if st.session_state.uploaded_files:
                st.write("uploaded files:")
                for idx, file_name in enumerate(st.session_state.uploaded_files, 1):
                    col_file, col_remove = st.columns([3, 1])
                    with col_file:
                        if len(file_name) < 15:
                            st.text(f"{idx}. {file_name}")
                        else:
                            st.text(f"{idx}. {file_name[:15]}..")
                    with col_remove:
                        if st.button("❌", key=f"remove_{idx}"):
                            try:
                                os.remove(data_folder / file_name)
                            except:
                                pass
                            st.session_state.uploaded_files.remove(file_name)
                            st.rerun()

            # File uploader
            if len(st.session_state.uploaded_files) < 2:
                uploaded_file = st.file_uploader(
                    "Choose PDF" if not st.session_state.uploaded_files else "Add another PDF",
                    type=['pdf'],
                    key="pdf_uploader"
                )
                
                if uploaded_file is not None:
                    if uploaded_file.name not in st.session_state.uploaded_files:
                        if save_uploaded_file(uploaded_file, data_folder):
                            st.session_state.uploaded_files.append(uploaded_file.name)
                            st.success(f"File {uploaded_file.name} uploaded successfully!")
                            st.rerun()
            else:
                st.warning("Maximum 2 files can be uploaded. Remove existing files to upload new ones.")
            
            # API Key input
            st.session_state.api_key = st.text_input(
                "OpenAI API Key", 
                value=st.session_state.api_key,
                type="password",
                key="api_key_input"
            )
            
            # Process button conditions
            files_uploaded = len(st.session_state.uploaded_files) > 0
            api_key_provided = bool(st.session_state.api_key.strip())
            
            if st.button("Process PDFs"):
                if files_uploaded and api_key_provided:
                    with st.spinner("Processing..."):
                        try:
                            # Set up environment with API key
                            set_env_st("OPENAI_API_KEY", st.session_state.api_key.strip())
                            
                            # Initialize graph
                            st.session_state.graph, st.session_state.graph_config, st.session_state.memory = build_graph()
                            st.success("PDFs processed and graph initialized!")
                        
                        except AuthenticationError as e:
                            st.error("Invalid API Key: Please check your OpenAI API key and try again.")
                            print(f"Authentication Error: {str(e)}")
                            
                        except OpenAIError as e:
                            st.error(f"OpenAI API Error: {str(e)}")
                            print(f"OpenAI Error: {str(e)}")
                            
                        except Exception as e:
                            st.error(f"An unexpected error occurred: {str(e)}")
                            print(f"Unexpected Error: {str(e)}")
                        else:
                            # Show separate messages for each missing item
                            if not files_uploaded:
                                st.info("Please provide: PDF file")
                            if not api_key_provided:
                                st.info("Please provide: OpenAI API key and press Enter")
            else:
                # This shows the instructions on the first load
                # Show separate messages for each missing item
                if not files_uploaded:
                    st.info("Please provide: PDF file")
                if not api_key_provided:
                    st.info("Please provide: OpenAI API key and press Enter")


    # Separator 1
    with sep1:
        st.markdown("<div style='border-left: 2px solid #e6e6e6; height: 100vh;'></div>", unsafe_allow_html=True)

    # Part 2: Prompt Section (Middle)
    with col2:
        st.subheader("Corrective RAG")
        
        # Prompt input
        user_prompt = st.text_area("Enter your prompt", height=150)
        
        if st.button("Submit") and user_prompt:
            if st.session_state.graph is None:
                st.error("Please process PDFs first!")
            else:
                with st.spinner("Generating response..."):
                    response = stream_graph_updates(
                        st.session_state.graph,
                        user_prompt,
                        st.session_state.graph_config
                    )
                    st.markdown("### Reply")
                    st.write(response)
                    
                    # Add to chat history
                    st.session_state.chat_history.append({
                        "prompt": user_prompt,
                        "response": response
                    })

        # Display chat history at bottom in descending order
        st.markdown("### Conversation History")
        for chat in reversed(st.session_state.chat_history):
            with st.container():
                # User prompt
                st.markdown("**You:**")
                st.markdown(f"```\n{chat['prompt']}\n```")
                # Assistant response
                st.markdown("**Assistant:**")
                st.write(chat['response'])
                st.markdown("---")  # Separator between messages

    # Separator 2
    with sep2:
        st.markdown("<div style='border-left: 2px solid #e6e6e6; height: 100vh;'></div>", unsafe_allow_html=True)

    # Part 3: Message History Section (Right)
    with col3:
        with st.expander("View History", expanded=False):
            st.write("Message 1")
            st.write("Message 2")
            st.write("Message 3")

if __name__ == "__main__":
    main()
