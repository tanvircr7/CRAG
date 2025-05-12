# LangGraph PDF Processing Application

A Streamlit-based application that implements Corrective RAG (Retrieval-Augmented Generation) for processing and querying PDF documents using LangGraph.

## Features

- 📁 PDF Document Upload (up to 2 files)
- 🔍 Intelligent Query Processing
- 🌐 Web Search Integration
- 💡 Context-Aware Response Generation
- 📊 Document Relevance Grading
- 💬 Interactive Chat History

## Prerequisites

- Python 3.11
- OpenAI API Key
- Required Python packages (see `requirements.txt`)
- SQLite needs to be > 3.35

## Installation

1. Clone the repository:
git clone [repository-url]
cd [repository-name]

2. Install dependencies:
docker compose up --build

## Usage

1. Run the Streamlit application:
streamlit run app.py

2. Open your web browser and navigate to the provided localhost URL

3. Upload PDF files (maximum 2)

4. Enter your OpenAI API key and Tavily API key

5. Process PDFs and start querying!

## Application Structure

### Main Components

- **PDF Upload Section**: Handles document upload and management
- **Query Interface**: Process user prompts and generate responses
- **Workflow Visualization**: Shows processing stages 

### Processing Pipeline

1. **Retrieve**: Extract relevant documents from the knowledge base
2. **Query Processing**: Analyze and understand user queries
3. **Relevance Check**: Grade document relevance to query
4. **Web Search**: Search external sources when needed
5. **Generate**: Create final response

## Workflow

The application uses LangGraph to create a processing pipeline:

    workflow = StateGraph(GraphState)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("generate", generate)
    workflow.add_node("transform_query", transform_query)
    workflow.add_node("web_search_node", web_search)

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `TAVILY_API_KEY`: Your Tavily API key

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Based on the [Corrective RAG paper](https://arxiv.org/abs/2401.15884)
- Implementation inspired by [RAG Implementation Guide](https://github.com/tanvircr7/CRAG)
