# Software Requirements Specification (SRS)
## ResearchFlow AI

**Document Version:** 2.0  
**Date:** 2026-07-12  
**Project:** ResearchFlow AI - Academic Research Assistant  
**Author:** orignlkartik1

---

## 1. Introduction

### 1.1 Purpose
ResearchFlow AI is a multi-agent academic research assistant designed to help researchers analyze seminal papers, discover recent citing papers, and identify promising future research directions. The system integrates Google ADK agents with a FastAPI backend and Telegram bot interface to provide a complete research workflow experience.

### 1.2 Scope
The system provides:
- Automated analysis of academic papers using AI agents
- Discovery of papers that cite or extend a given seminal paper using web search
- Synthesis of research trends and gaps using advanced reasoning
- Integration with Google ADK (gemini-2.5-flash model) for agent orchestration
- FastAPI REST backend for agent communication
- Telegram bot interface for user interaction via python-telegram-bot
- Session-based conversation management with in-memory storage

### 1.3 Definitions, Acronyms, and Abbreviations
- **ADK**: Agent Development Kit (Google)
- **API**: Application Programming Interface
- **SRS**: Software Requirements Specification
- **AI Agent**: Autonomous system that can perceive, reason, and act
- **Seminal Paper**: Foundational academic publication in a research field
- **FastAPI**: Modern Python web framework for building APIs
- **Telegram Bot API**: Interface for creating Telegram bots

---

## 2. Overall Description

### 2.1 Product Perspective
ResearchFlow AI operates as:
1. A multi-agent system powered by Google ADK (gemini-2.5-flash)
2. A FastAPI REST backend for managing chat sessions and agent runs
3. A Telegram bot frontend using python-telegram-bot for user interaction
4. A coordinated workflow system with specialized sub-agents

### 2.2 Product Features
1. **Academic Coordinator Agent** - Orchestrates the complete research workflow using gemini-2.5-flash
2. **Academic Web Research Sub-Agent** - Discovers citing and related papers using Google Search
3. **Academic New Research Sub-Agent** - Identifies gaps and emerging research areas with synthesis capabilities
4. **Paper Analysis** - Extracts metadata, keywords, innovations, and references from papers
5. **FastAPI Backend** - REST endpoint `/chat` for processing research queries with session management
6. **Telegram Bot Interface** - `/start` command and message handling with HTTP client integration
7. **Session Management** - In-memory session service for maintaining conversation context across requests

### 2.3 User Classes and Characteristics
- **Researchers**: Need to understand literature trends and gaps
- **Students**: Seeking context for their thesis or dissertation
- **Academics**: Exploring citation networks and research evolution
- **Telegram Users**: Prefer conversational interface for research queries

### 2.4 Operating Environment
- **OS**: Platform-independent (Python 3.14+)
- **Runtime**: Python virtual environment with `uv` package manager
- **Framework**: FastAPI with Uvicorn ASGI server
- **Bot Framework**: python-telegram-bot (22.8+) with async support
- **External Services**: Google ADK with gemini-2.5-flash, Google Search, Telegram Bot API
- **Hardware**: Standard laptop/server with internet connectivity

### 2.5 Design and Implementation Constraints
- Python 3.14+ required
- Dependency on Google ADK 2.3.0 and gemini-2.5-flash model
- Telegram Bot Token required for bot functionality
- Google API Key required for ADK and Search integration
- FastAPI backend must run on localhost:8000 (configurable)
- Telegram bot connects via HTTP client to backend
- In-memory session storage (not persistent across restarts)

---

## 3. Specific Requirements

### 3.1 Functional Requirements

#### 3.1.1 Paper Analysis
- **Req F1.1**: System shall accept academic papers via user query or PDF reference
- **Req F1.2**: System shall extract paper title, authors, abstract, and summary
- **Req F1.3**: System shall identify key keywords and innovations from papers
- **Req F1.4**: System shall extract and list paper references

#### 3.1.2 Web Research
- **Req F2.1**: System shall search for papers citing the seminal paper using Google Search
- **Req F2.2**: System shall search across current year and previous year
- **Req F2.3**: System shall identify at least 10 distinct citing papers per year (minimum 20 total)
- **Req F2.4**: System shall verify and validate search results for relevance
- **Req F2.5**: System shall present results grouped by publication year

#### 3.1.3 Future Research Synthesis
- **Req F3.1**: System shall identify research gaps from paper context and recent citing papers
- **Req F3.2**: System shall generate at least 10 future research suggestions
- **Req F3.3**: System shall include title, rationale, and novelty assessment for each suggestion
- **Req F3.4**: System shall synthesize trends from recent citing papers with diversity across utility, unexpectedness, and popularity
- **Req F3.5**: System shall optionally identify relevant authors aligned with proposed research areas

#### 3.1.4 FastAPI Backend
- **Req F4.1**: System shall expose POST endpoint `/chat` accepting `user_id` and `message`
- **Req F4.2**: System shall create sessions per user on first message
- **Req F4.3**: System shall maintain conversation context across multiple messages
- **Req F4.4**: System shall return structured JSON response with research findings
- **Req F4.5**: System shall handle concurrent requests from multiple users

#### 3.1.5 Telegram Bot Interface
- **Req F5.1**: Telegram bot shall register `/start` command and reply with greeting
- **Req F5.2**: Telegram bot shall accept user messages and forward to backend
- **Req F5.3**: Telegram bot shall receive research findings and display to user
- **Req F5.4**: Bot shall handle errors gracefully with informative messages
- **Req F5.5**: Bot shall use async HTTP client for non-blocking backend calls

#### 3.1.6 Agent Orchestration
- **Req F6.1**: Coordinator agent shall manage workflow execution using gemini-2.5-flash
- **Req F6.2**: Sub-agents shall operate independently and be composable via AgentTool
- **Req F6.3**: System shall handle agent failures and provide error messages
- **Req F6.4**: System shall log all agent activities for debugging

### 3.2 Non-Functional Requirements

#### 3.2.1 Performance
- **Req NF1.1**: Paper analysis shall complete within 30 seconds
- **Req NF1.2**: Web research shall return results within 60 seconds
- **Req NF1.3**: System shall handle concurrent requests from multiple users
- **Req NF1.4**: Backend API response time shall be under 2 seconds for simple queries

#### 3.2.2 Reliability
- **Req NF2.1**: System uptime goal: 99% during operational hours
- **Req NF2.2**: System shall gracefully handle API failures (Google Search, ADK timeout)
- **Req NF2.3**: System shall implement retry logic for transient failures
- **Req NF2.4**: Telegram bot shall reconnect automatically on connection loss

#### 3.2.3 Scalability
- **Req NF3.1**: System shall support concurrent research workflows (multiple users)
- **Req NF3.2**: In-memory session storage shall support at least 100 concurrent sessions
- **Req NF3.3**: Agent system shall distribute workload across coordinator and sub-agents

#### 3.2.4 Security
- **Req NF4.1**: Bot tokens and API keys shall be stored as environment variables (`.env`)
- **Req NF4.2**: System shall not expose credentials in logs or error messages
- **Req NF4.3**: API calls shall use HTTPS for encryption
- **Req NF4.4**: Sensitive environment variables: `TELEGRAM_TOKEN`, `GOOGLE_API_KEY`

#### 3.2.5 Usability
- **Req NF5.1**: Telegram interface shall be intuitive and require minimal setup
- **Req NF5.2**: Error messages shall be clear and actionable
- **Req NF5.3**: README shall provide setup, usage, and API documentation

#### 3.2.6 Maintainability
- **Req NF6.1**: Code shall follow PEP 8 standards
- **Req NF6.2**: Agents and backend components shall be modular and independently testable
- **Req NF6.3**: Project shall include comprehensive documentation and docstrings

---

## 4. System Architecture

### 4.1 High-Level Architecture
```
┌────────────────────────────────────────┐
│   User Interface Layer                 │
│   ├─ Telegram Bot (telegram.py)        │
│   └─ Async Message Handler             │
└──────────────┬─────────────────────────┘
               │ HTTP (httpx client)
┌──────────────▼─────────────────────────┐
│   FastAPI Backend Layer                │
│   ├─ FastAPI App (main.py)             │
│   ├─ Chat Endpoint (/chat)             │
│   └─ ADK Runner Management             │
└──────────────┬─────────────────────────┘
               │
┌──────────────▼─────────────────────────┐
│   Agent Orchestration Layer            │
│   ├─ Academic Coordinator Agent        │
│   ├─ Runner (ADK Runner)               │
│   ├─ Session Service (InMemory)        │
│   └─ Workflow Management               │
└──────────────┬─────────────────────────┘
               │
┌──────────────▼─────────────────────────┐
│   Agent Services Layer                 │
│   ├─ Web Research Sub-Agent            │
│   ├─ New Research Sub-Agent            │
│   ├─ Google Search Tool                │
│   └─ Agent Tool Composition             │
└──────────────┬─────────────────────────┘
               │
┌──────────────▼─────────────────────────┐
│   External Services Layer              │
│   ├─ Google ADK / Gemini 2.5-Flash    │
│   ├─ Google Search API                 │
│   ├─ Telegram Bot API                  │
│   └─ Academic Paper Sources            │
└────────────────────────────────────────┘
```

### 4.2 Component Description

| Component | Purpose | Technologies | Location |
|-----------|---------|---------------|----------|
| **Coordinator Agent** | Orchestrates workflow | Google ADK, gemini-2.5-flash | `my_agent/agent.py` |
| **Web Research Agent** | Finds citing papers | Google ADK, Google Search | `my_agent/sub_agents/academic_webresearch/` |
| **New Research Agent** | Synthesizes gaps | Google ADK, gemini-2.5-flash | `my_agent/sub_agents/academic_newresearch/` |
| **FastAPI Backend** | REST API & session management | FastAPI, Uvicorn | `my_agent/backend/main.py` |
| **ADK Runner** | Manages agent execution | Google ADK Runner | `my_agent/backend/adk_runner.py` |
| **Telegram Bot** | User interaction interface | python-telegram-bot | `my_agent/backend/telegram.py` |
| **Session Service** | Conversation state | InMemorySessionService | `my_agent/backend/adk_runner.py` |

### 4.3 Data Flow

```
User (Telegram) 
  ↓ message
Telegram Bot Handler
  ↓ HTTP POST /chat
FastAPI Backend (/chat endpoint)
  ↓ create/get session
ADK Runner (adk_runner.py)
  ↓ ask_agent(user_id, message)
Coordinator Agent (agent.py)
  ├─ Parse user query
  ├─ Call academic_websearch_agent via AgentTool
  │  └─ Google Search Tool
  └─ Call academic_newresearch_agent via AgentTool
  ↓ response
FastAPI Backend
  ↓ JSON response
Telegram Bot
  ↓ reply_text
User (Telegram)
```

---

## 5. Data Requirements

### 5.1 Input Data
- User research query (text message via Telegram)
- Academic paper reference (title, authors, or PDF metadata)
- Seminal paper identifier for web search

### 5.2 Output Data
- Extracted paper metadata and summary
- List of citing papers with metadata (title, authors, year, source, link)
- Future research suggestions with rationale
- Summary report with findings

### 5.3 Data Storage
- **Configuration**: Environment variables (`.env` in `my_agent/backend/`)
- **Sessions**: In-memory session service (InMemorySessionService)
- **Logs**: Console output (async logging in ADK Runner)
- **Cache**: Session-based cache in memory

---

## 6. Interface Requirements

### 6.1 User Interfaces

#### 6.1.1 Telegram Bot Interface
```
User: /start
Bot: Hello! I am ResearchFlow AI.

User: Analyze the paper "Attention is All You Need" by Vaswani et al.
Bot: [Coordinator analyzes paper and runs web/new research agents]
Bot: [Returns findings with citing papers and future research directions]
```

#### 6.1.2 Backend API Interface
```
POST /chat
Content-Type: application/json

Request:
{
  "user_id": "123456789",
  "message": "Analyze the paper on Transformers and find recent citing papers"
}

Response:
{
  "response": "Based on your query, I found recent papers... Future research directions include..."
}
```

### 6.2 System Interfaces
- **Google ADK Interface**: Agent registration, tool binding, model deployment
- **Google Search API**: Web search queries via google_search tool
- **Gemini 2.5-Flash**: LLM for agent reasoning and synthesis
- **Telegram Bot API**: Message polling and response delivery via python-telegram-bot
- **FastAPI**: HTTP REST interface for backend

---

## 7. Technology Stack

### 7.1 Core Technologies
- **Language**: Python 3.14+
- **Agent Framework**: Google ADK 2.3.0 with gemini-2.5-flash
- **Web Framework**: FastAPI 0.139.0
- **ASGI Server**: Uvicorn 0.51.0
- **Bot Framework**: python-telegram-bot 22.8+
- **HTTP Client**: httpx 0.28.1 (async)
- **Package Manager**: uv
- **Environment**: python-dotenv 1.2.2

### 7.2 Dependencies
See `pyproject.toml` for full dependency list with version constraints.

---

## 8. Future Enhancements

### 8.1 Telegram Bot Integration
- **F-TG-01**: Multi-turn conversation refinement
  - Support conversation history and context refinement
  - Allow users to ask follow-up questions on research findings
  - Implement conversation reset via `/reset` command
  
- **F-TG-02**: Advanced Telegram features
  - Document uploads (PDF analysis)
  - Inline search capabilities
  - Result caching and history
  - User preferences and saved searches

- **F-TG-03**: Telegram group support
  - Collaborative research sessions
  - Shared research findings
  - Team-based research projects

### 8.2 AI Agents Stack Enhancement
- **F-AI-01**: Core AI-Agents Stack Improvement
  - Implement ReAct (Reasoning + Acting) pattern
  - Add Chain-of-Thought prompting
  - Integrate agent memory systems for context retention
  
- **F-AI-02**: Advanced Agent Capabilities
  - Multi-hop reasoning for complex research queries
  - Self-reflection and error correction
  - Tool use optimization and learning
  
- **F-AI-03**: Agent Specialization
  - Methodology agent (research method analysis)
  - Data agent (dataset and benchmark discovery)
  - Comparison agent (comparative paper analysis)
  - Citation network agent (graph analysis)
  
- **F-AI-04**: Agent Communication
  - Enhanced agent-to-agent message passing
  - Consensus mechanisms for conflicting suggestions
  - Hierarchical agent supervision

### 8.3 Backend Enhancements
- **F-BE-01**: Database persistence
  - Replace in-memory sessions with PostgreSQL/MongoDB
  - Persistent session history
  - User preference storage
  
- **F-BE-02**: Caching and performance
  - Redis cache for search results
  - Query result memoization
  - Session state optimization

- **F-BE-03**: Monitoring and analytics
  - Request logging and metrics
  - Agent performance tracking
  - Error rate monitoring

### 8.4 Research Features
- **F-RES-01**: Citation network visualization
  - Interactive graph explorer
  - Trend identification across networks
  - Citation path analysis

- **F-RES-02**: Enhanced paper analysis
  - Table and figure extraction
  - Research methodology parsing
  - Dataset and code repository discovery

- **F-RES-03**: Collaborative features
  - Shared research projects
  - Team annotations and comments
  - Export and report generation

### 8.5 Frontend Enhancements
- **F-FRONT-01**: Web dashboard
  - User-friendly interface for research exploration
  - Real-time research progress tracking
  - Interactive result visualization

- **F-FRONT-02**: Advanced UI features
  - Search history and saved queries
  - Export to various formats (PDF, JSON, etc.)
  - Collaboration tools

---

## 9. Acceptance Criteria

### 9.1 Core Functionality
- [ ] Paper analysis extracts all required metadata
- [ ] Web research agent identifies 10+ papers per year when available
- [ ] New research agent generates 10+ meaningful suggestions with rationale
- [ ] Coordinator successfully orchestrates full workflow
- [ ] Telegram bot responds to `/start` command
- [ ] FastAPI backend `/chat` endpoint processes requests correctly
- [ ] Session management maintains context across multiple messages

### 9.2 Quality Criteria
- [ ] All code follows PEP 8 standards
- [ ] Functions include comprehensive docstrings
- [ ] System handles errors gracefully with informative messages
- [ ] README includes setup, usage, and API documentation
- [ ] Response times meet performance requirements
- [ ] Code is modular and easily testable

### 9.3 Documentation
- [ ] SRS document is complete and up-to-date
- [ ] README links to SRS for detailed specifications
- [ ] API documentation included in README
- [ ] Code comments explain complex logic
- [ ] Contribution guidelines are documented
- [ ] Setup instructions include environment variables

---

## 10. Glossary

| Term | Definition |
|------|-----------|
| **Agent** | Autonomous system that perceives environment and takes actions |
| **Coordinator** | Master agent orchestrating workflow and sub-agents |
| **Sub-Agent** | Specialized agent focused on specific tasks |
| **Tool** | Callable function or API integration available to agents |
| **Workflow** | Sequence of steps executed by coordinator |
| **Seminal Paper** | Foundational publication in a research area |
| **Session** | User conversation context maintained in memory or database |
| **ADK Runner** | Google ADK component managing agent execution |
| **AgentTool** | Wrapper enabling sub-agent composition in coordinator |

---

## 11. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-09 | orignlkartik1 | Initial SRS document creation |
| 2.0 | 2026-07-12 | orignlkartik1 | Updated with backend implementation, FastAPI, session management, and current architecture |

---

## 12. Appendices

### A. Environment Variables
```
# Google API Configuration
GOOGLE_API_KEY=your_google_adk_api_key

# Telegram Bot Configuration
TELEGRAM_TOKEN=your_telegram_bot_token

# Backend Configuration (optional)
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
```

### B. Running the System

#### Start FastAPI Backend
```bash
python -m uvicorn my_agent.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Start Telegram Bot
```bash
python -m my_agent.backend.telegram
```

#### Run with Google ADK CLI (alternative)
```bash
adk run --agent my_agent.agent:root_agent
```

### C. API Documentation

#### POST /chat
Processes user research queries through the ADK agent system.

**Request:**
```json
{
  "user_id": "string (unique user identifier)",
  "message": "string (user research query)"
}
```

**Response:**
```json
{
  "response": "string (agent response with research findings)"
}
```

**Status Codes:**
- 200: Success
- 400: Invalid request
- 500: Server error

### D. Technology Stack
- **Language**: Python 3.14+
- **Agent Framework**: Google ADK 2.3.0
- **LLM Model**: Gemini 2.5-Flash
- **Web Framework**: FastAPI 0.139.0
- **Bot Framework**: python-telegram-bot 22.8+
- **Package Manager**: uv

### E. References
- [Google ADK Documentation](https://ai.google.dev/)
- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)
- [Python PEP 8 Style Guide](https://pep8.org/)
