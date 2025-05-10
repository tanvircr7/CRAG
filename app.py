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
    .process-box {
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        background-color: #2D3250;  /* Dark blue-ish */
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: box-shadow 0.3s ease;
    }
    .process-box-websearch {
        background-color: #3352ff;  /* Different shade for web search */
        transition: box-shadow 0.3s ease;
    }
    .process-box-active {
        box-shadow: 0 0 15px rgba(255, 255, 255, 0.5);
        transform: scale(1.02);
    }
    .box-title {
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .box-description {
        font-size: 12px;
        opacity: 0.8;
    }
    .header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 20px;
    }
    .title {
        font-size: 24px;
        font-weight: bold;
        margin: 0;
    }
    .title {
        font-size: 18px;
        font-weight: bold;
        margin: 0;
    }
    .social-links {
        display: flex;
        gap: 10px;
    }
    .social-link {
        display: inline-flex;
        align-items: center;
        padding: 5px 10px;
        border-radius: 4px;
        text-decoration: none;
        color: white;
        font-size: 14px;
        transition: opacity 0.2s;
    }
    .social-link:hover {
        opacity: 0.8;
    }
    .github-link {
        background-color: #333;
    }
    .twitter-link {
        background-color: #1DA1F2;
    }
    </style>
    <script>
        function activateBox(boxClass) {
            document.querySelector(boxClass).classList.add('process-box-active');
        }

        function resetBoxes() {
            document.querySelectorAll('.process-box').forEach(box => {
                box.classList.remove('process-box-active');
            });
        }
    </script>
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
        st.markdown("""
            <div class="header-container">
                <h2 class="title">Corrective RAG </h2>
                <div class="social-links">
                    <text class="smalltext">tanvir</text>
                    <a href="https://github.com/tanvircr7" target="_blank" class="social-link github-link">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="white" ">
                            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                        </svg>
                    </a>
                    <a href="https://twitter.com/@MTH_2583" target="_blank" class="social-link twitter-link">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="white" ">
                            <path d="M24 4.557c-.883.392-1.832.656-2.828.775 1.017-.609 1.798-1.574 2.165-2.724-.951.564-2.005.974-3.127 1.195-.897-.957-2.178-1.555-3.594-1.555-3.179 0-5.515 2.966-4.797 6.045-4.091-.205-7.719-2.165-10.148-5.144-1.29 2.213-.669 5.108 1.523 6.574-.806-.026-1.566-.247-2.229-.616-.054 2.281 1.581 4.415 3.949 4.89-.693.188-1.452.232-2.224.084.626 1.956 2.444 3.379 4.6 3.419-2.07 1.623-4.678 2.348-7.29 2.04 2.179 1.397 4.768 2.212 7.548 2.212 9.142 0 14.307-7.721 13.995-14.646.962-.695 1.797-1.562 2.457-2.549z"/>
                        </svg>
                    </a>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
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
                # st.markdown(f"```\n{chat['response']}\n```")
                st.write(chat['response'])
                st.markdown("---")  # Separator between messages

    # Separator 2
    with sep2:
        st.markdown("<div style='border-left: 2px solid #e6e6e6; height: 100vh;'></div>", unsafe_allow_html=True)

    # Part 3: Worklow Section (Right)
    with col3:
        # Retrieve Box
        st.markdown("""
            <div class="process-box">
                <div class="box-title">📚 Retrieve</div>
                <div class="box-description">Extract relevant documents from the knowledge base</div>
            </div>
        """, unsafe_allow_html=True)

        # Query Box
        st.markdown("""
            <div class="process-box">
                <div class="box-title">❓ Query Processing</div>
                <div class="box-description">Process and understand user query</div>
            </div>
        """, unsafe_allow_html=True)

        # Relevance Box
        st.markdown("""
            <div class="process-box">
                <div class="box-title">🎯 Relevance Check</div>
                <div class="box-description">Grade document relevance to query</div>
            </div>
        """, unsafe_allow_html=True)

        # Web Search Box (Different Color)
        st.markdown("""
            <div class="process-box process-box-websearch">
                <div class="box-title">🌐 Web Search</div>
                <div class="box-description">Search external sources if needed</div>
            </div>
        """, unsafe_allow_html=True)

        # Generate Box
        st.markdown("""
            <div class="process-box">
                <div class="box-title">✨ Generate</div>
                <div class="box-description">Create final response</div>
            </div>
        """, unsafe_allow_html=True)

        # Collapsible Workflow Description
        # Links in expander
        with st.expander("📑 References", expanded=False):
            st.markdown("""
                <div class="custom-link">
                    <div class="link-title">📄 Research Paper</div>
                    <div class="link-description">
                        <a href="https://arxiv.org/abs/2401.15884" target="_blank">
                            Corrective RAG: Leveraging Retrieval-Augmented Generation for Fact Correction
                        </a>
                    </div>
                </div>
                
                <div class="custom-link">
                    <div class="link-title">📚 Implementation Guide</div>
                    <div class="link-description">
                        <a href="https://github.com/tanvircr7/CRAG" target="_blank">
                            RAG Implementation Guide by tanvir
                        </a>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            st.caption("*Click links to open in new tab*")
        
        
if __name__ == "__main__":
    main()
