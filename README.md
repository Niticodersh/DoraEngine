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
│ ReasoningAgent  │ -> │  AnswerAgent    │ -> │   Final Answer   │
│                 │    │                 │    │                 │
│ Thinks through  │    │ Writes answer   │    │ With citations   │
│ the problem     │    │ with citations  │    │ and confidence   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [Groq API Key](https://console.groq.com/) (required)
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

   # Edit .env and add your API keys
   # GROQ_API_KEY=your_groq_api_key_here
   # TAVILY_API_KEY=your_tavily_api_key_here
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **Open your browser**
   - Navigate to `http://localhost:8501`
   - Start researching!

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d --build

# Stop
docker-compose down
```

### Using Docker Directly

```bash
# Build image
docker build -t doraengine .

# Run container
docker run -p 8501:8501 --env-file .env -v $(pwd):/app doraengine
```

## 📁 Project Structure

```
doraengine/
├── app.py                 # Main Streamlit application
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

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/doraengine/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/doraengine/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/doraengine/wiki)

---

**Built with ❤️ using cutting-edge AI technologies**