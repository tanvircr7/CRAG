import streamlit as st
from pathlib import Path
import os

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

def create_data_folder():
    """Create a data folder if it doesn't exist"""
    data_folder = Path("data")
    if not data_folder.exists():
        data_folder.mkdir(parents=True)
    return data_folder

def save_uploaded_file(uploaded_file, data_folder):
    """Save the uploaded PDF file to the data folder"""
    if uploaded_file is not None:
        file_path = data_folder / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    return False

def main():
    # Initialize session state
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""

    # Create three columns with specific ratios
    col1, sep1, col2, sep2, col3 = st.columns([1, 0.2, 4, 0.2, 1])
    
    # Part 1: PDF Upload Section (Left)
    with col1:
        settings_expander = st.expander("📁 Upload & Settings", expanded=True)
        with settings_expander:
            data_folder = create_data_folder()
            
            # Display current uploaded files
            if st.session_state.uploaded_files:
                st.write("uploaded files:")
                for idx, file_name in enumerate(st.session_state.uploaded_files, 1):
                    col_file, col_remove = st.columns([3, 1])
                    with col_file:
                        if len(file_name) < 10:
                            st.text(f"{idx}. {file_name}")
                        else:
                            st.text(f"{idx}. {file_name[:10]}..")
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
            
            if files_uploaded and api_key_provided:
                if st.button("Process PDFs"):
                    with st.spinner("Processing..."):
                        # Add your processing logic here
                        pass
            else:
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
        
        if st.button("Submit"):
            # Add your prompt processing logic here
            st.markdown("### Reply")
            st.write("Your response will appear here...")

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
