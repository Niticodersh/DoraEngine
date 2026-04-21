# DoraEngine

> Premium Autonomous AI Research Agent with Graph RAG and Multi-step Reasoning

DoraEngine is an advanced AI-powered research assistant that autonomously researches topics, verifies information across multiple sources, and provides comprehensive answers with citations. Built with modern AI technologies including Graph RAG, LangGraph orchestration, and a beautiful dark glass-morphism UI.

![DoraEngine Demo](https://via.placeholder.com/800x400/1a1a2e/ffffff?text=DoraEngine+Demo)

## ✨ Features

- **Autonomous Research**: Multi-agent pipeline that searches, scrapes, and analyzes information
- **Graph RAG**: Knowledge graph construction for better information connectivity
- **Multi-step Reasoning**: Structured reasoning process with confidence scoring
- **Source Verification**: Cross-references information across multiple web sources
- **Beautiful UI**: Dark glass-morphism design with Perplexity-level aesthetics
- **Follow-up Questions**: LLM-generated contextual follow-up questions
- **PDF Export**: Export research results to PDF reports
- **Docker Support**: Containerized deployment for easy setup

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   QueryAgent    │ -> │   SearchAgent   │ -> │  ScraperAgent   │
│                 │    │                 │    │                 │
│ Understands     │    │ Searches web    │    │ Extracts content│
│ intent          │    │ for sources     │    │ from pages      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      |
                                                      v
    --------------------------------------------------
    |
    v        
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  GraphBuilder   │ -> │    GraphRAG     │ -> │ RankingAgent    │
│                 │    │                 │    │                 │
│ Builds knowledge│    │ Connects related│    │ Prioritizes     │
│ graph           │    │ information     │    │ insights        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      |
                                                      v
    --------------------------------------------------
    |
    v    
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ ReasoningAgent  │ -> │  AnswerAgent    │ -> │   Final Answer  │
│                 │    │                 │    │                 │
│ Thinks through  │    │ Writes answer   │    │ With citations  │
│ the problem     │    │ with citations  │    │ and confidence  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+ (for frontend)
- [Groq API Key](https://console.groq.com/) (required)
- MongoDB Database (required for backend auth and history)
- [Tavily API Key](https://tavily.com/) (optional, improves search quality)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/doraengine.git
   cd doraengine
   ```

2. **Set up environment**
   ```bash
   # Copy environment template
   cp .env.example .env

   # Edit .env and add your API keys and MongoDB configuration
   # GROQ_API_KEY=your_groq_api_key_here
   # AUTH_SECRET_KEY=your_auth_secret_key
   # MONGODB_URI=your_mongodb_uri
   # MONGODB_DB_NAME=doraengine
   # TAVILY_API_KEY=your_tavily_api_key_here
   ```

## 🏃 Running the Application

DoraEngine supports two architectures: our new, production-ready decoupled setup (React + FastAPI) and our original monolithic Streamlit application.

### Option 1: Decoupled Architecture (Recommended)

Our new architecture features a React/Vite frontend and a FastAPI backend with MongoDB for authentication, plans, user API keys, and chat history.

1. **Start the Backend API**
   ```bash
   # Create and activate virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run the FastAPI server
   python -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the Frontend** (in a new terminal)
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Access the Application**
   - Frontend Client: `http://localhost:5173`
   - Backend API Docs: `http://localhost:8000/docs`

### Option 2: Streamlit Application (Original)

If you prefer the original, lightweight Streamlit-only setup:

1. **Set up Python environment and run**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   
   streamlit run app.py
   ```

2. **Access the Application**
   - Navigate to `http://localhost:8501`

## 🐳 Docker Deployment

We provide a comprehensive Docker Compose configuration to easily spin up all services simultaneously.

### Using Docker Compose (Recommended)

The provided `docker-compose.yml` will orchestrate the FastAPI backend, the Vite frontend, and the Streamlit app.

```bash
# Build and run all services
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

Once running, the services will be available at:
- **Frontend App**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`
- **Streamlit App**: `http://localhost:8501`

### Running Individual Services using Docker Compose

If you only want to run specific services, you can specify them:

```bash
# Run only the new decoupled architecture
docker-compose up backend frontend

# Run only the Streamlit app
docker-compose up streamlit
```

## 📁 Project Structure

```
doraengine/
├── app.py                 # Main Streamlit application
├── api/                   # FastAPI backend for decoupled frontend
├── frontend/              # React application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker container definition
├── docker-compose.yml    # Docker Compose configuration
├── .env.example         # Environment variables template
├── styles/
│   └── theme.css        # Custom CSS styling
├── agents/               # AI agent implementations
│   ├── answer_agent.py
│   ├── query_agent.py
│   ├── search_agent.py
│   ├── scraper_agent.py
│   ├── graph_builder.py
│   ├── graph_rag.py
│   ├── ranking_agent.py
│   └── reasoning_agent.py
├── pipeline/
│   └── orchestrator.py   # LangGraph pipeline orchestration
├── utils/
│   ├── llm_client.py     # Groq LLM client
│   ├── embedder.py       # Text embeddings
│   ├── chunker.py        # Text chunking utilities
│   ├── graph_viz.py      # Graph visualization
│   └── pdf_export.py     # PDF report generation
└── lib/                  # Static assets
    ├── bindings/
    └── tom-select/
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq API key for LLM access | Yes |
| `TAVILY_API_KEY` | Tavily API key for enhanced search | No |

### Customization

- **UI Styling**: Modify `styles/theme.css`
- **Agent Behavior**: Edit files in `agents/` directory
- **Pipeline Flow**: Modify `pipeline/orchestrator.py`

## 🔧 Development

### Setting up Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # If available

# Run tests
python -m pytest

# Run with auto-reload
streamlit run app.py --server.headless=true
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints to new functions
- Write tests for new features
- Update documentation as needed

## 📊 Performance

- **Response Time**: Typically 30-90 seconds for comprehensive research
- **Source Coverage**: Searches across 10-20+ web sources
- **Confidence Scoring**: AI-powered confidence assessment
- **Graph Size**: Up to 100+ nodes for complex topics

## 🔒 Security

- API keys are stored locally in `.env` file
- No data is sent to external servers except for LLM and search APIs
- All processing happens locally or through trusted APIs

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Groq** for fast LLM inference
- **LangGraph** for agent orchestration
- **Streamlit** for the web framework
- **Sentence Transformers** for embeddings
- **NetworkX** for graph operations

---

**Built with ❤️ using cutting-edge AI technologies**
