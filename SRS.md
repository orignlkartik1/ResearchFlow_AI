# Software Requirements Specification (SRS)
## ResearchFlow AI

**Document Version:** 1.0  
**Date:** 2026-07-09  
**Project:** ResearchFlow AI - Academic Research Assistant  
**Author:** orignlkartik1

---

## 1. Introduction

### 1.1 Purpose
ResearchFlow AI is a multi-agent academic research assistant designed to help researchers analyze seminal papers, discover recent citing papers, and identify promising future research directions. This document outlines the functional and non-functional requirements, system architecture, and future enhancements for the project.

### 1.2 Scope
The system provides:
- Automated analysis of academic papers using AI agents
- Discovery of papers that cite or extend a given seminal paper
- Synthesis of research trends and gaps
- Integration with Google ADK for agent orchestration
- Telegram bot interface for user interaction (future)

### 1.3 Definitions, Acronyms, and Abbreviations
- **ADK**: Agent Development Kit (Google)
- **API**: Application Programming Interface
- **SRS**: Software Requirements Specification
- **AI Agent**: Autonomous system that can perceive, reason, and act
- **Seminal Paper**: Foundational academic publication in a research field

---

## 2. Overall Description

### 2.1 Product Perspective
ResearchFlow AI operates as:
1. A standalone academic research tool powered by Google ADK agents
2. A future integration point for Telegram bot messaging
3. A multi-agent coordination system with specialized sub-agents

### 2.2 Product Features
1. **Academic Coordinator Agent** - Orchestrates the complete research workflow
2. **Web Research Sub-Agent** - Discovers citing and related papers
3. **Future Research Sub-Agent** - Identifies gaps and emerging research areas
4. **Paper Analysis** - Extracts metadata, keywords, innovations, and references
5. **Telegram Bot Interface** - Basic bot skeleton for user interaction

### 2.3 User Classes and Characteristics
- **Researchers**: Need to understand literature trends and gaps
- **Students**: Seeking context for their thesis or dissertation
- **Academics**: Exploring citation networks and research evolution
- **Tech-Savvy Users**: Comfortable with CLI and environment setup

### 2.4 Operating Environment
- **OS**: Platform-independent (Python 3.14+)
- **Runtime**: Python virtual environment with `uv` package manager
- **External Services**: Google ADK, Google Search, Telegram API
- **Hardware**: Standard laptop/server with internet connectivity

### 2.5 Design and Implementation Constraints
- Python 3.14+ required
- Dependency on Google ADK libraries
- Telegram Bot Token required for bot functionality
- Google ADK credentials for Gemini/Search integration

---

## 3. Specific Requirements

### 3.1 Functional Requirements

#### 3.1.1 Paper Analysis
- **Req F1.1**: System shall accept academic papers (PDF, metadata, or URLs)
- **Req F1.2**: System shall extract paper title, authors, abstract, and summary
- **Req F1.3**: System shall identify key keywords and innovations from papers
- **Req F1.4**: System shall extract and list paper references

#### 3.1.2 Web Research
- **Req F2.1**: System shall search for papers citing the seminal paper
- **Req F2.2**: System shall search across multiple years (current + previous)
- **Req F2.3**: System shall verify and validate search results
- **Req F2.4**: System shall group and categorize citing papers

#### 3.1.3 Future Research Synthesis
- **Req F3.1**: System shall identify research gaps from paper context
- **Req F3.2**: System shall generate at least 10 future research suggestions
- **Req F3.3**: System shall include rationale and novelty scores for suggestions
- **Req F3.4**: System shall synthesize trends from recent citing papers

#### 3.1.4 User Interface
- **Req F4.1**: Telegram bot shall register `/start` command
- **Req F4.2**: Telegram bot shall accept research queries
- **Req F4.3**: System shall present findings clearly to users
- **Req F4.4**: Bot shall handle errors gracefully with informative messages

#### 3.1.5 Agent Orchestration
- **Req F5.1**: Coordinator agent shall manage workflow execution
- **Req F5.2**: Sub-agents shall operate independently but coordinate through coordinator
- **Req F5.3**: System shall handle agent failures and retries
- **Req F5.4**: System shall log all agent activities for debugging

### 3.2 Non-Functional Requirements

#### 3.2.1 Performance
- **Req NF1.1**: Paper analysis shall complete within 30 seconds
- **Req NF1.2**: Web research shall return results within 60 seconds
- **Req NF1.3**: System shall handle concurrent requests from multiple users

#### 3.2.2 Reliability
- **Req NF2.1**: System uptime goal: 99% during business hours
- **Req NF2.2**: System shall gracefully handle API failures
- **Req NF2.3**: System shall implement retry logic for transient failures

#### 3.2.3 Scalability
- **Req NF3.1**: System shall support concurrent research workflows
- **Req NF3.2**: Database/storage shall scale for large paper collections
- **Req NF3.3**: Agent system shall distribute workload efficiently

#### 3.2.4 Security
- **Req NF4.1**: Bot tokens and API keys shall be stored as environment variables
- **Req NF4.2**: System shall not expose credentials in logs or error messages
- **Req NF4.3**: API calls shall use HTTPS for encryption

#### 3.2.5 Usability
- **Req NF5.1**: CLI interface shall be intuitive and well-documented
- **Req NF5.2**: Error messages shall be clear and actionable
- **Req NF5.3**: README shall provide setup and usage examples

#### 3.2.6 Maintainability
- **Req NF6.1**: Code shall follow PEP 8 standards
- **Req NF6.2**: Agents shall be modular and independently testable
- **Req NF6.3**: Project shall include comprehensive documentation

---

## 4. System Architecture

### 4.1 High-Level Architecture
```
┌─────────────────────────────────────┐
│   User Interface Layer              │
│   ├─ Telegram Bot                   │
│   └─ CLI Interface                  │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Agent Orchestration Layer         │
│   ├─ Academic Coordinator Agent     │
│   └─ Workflow Management            │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Agent Services Layer              │
│   ├─ Web Research Sub-Agent         │
│   ├─ New Research Sub-Agent         │
│   └─ Paper Analysis Tools           │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   External Services Layer           │
│   ├─ Google ADK / Gemini            │
│   ├─ Google Search API              │
│   ├─ Telegram Bot API               │
│   └─ Academic Databases             │
└─────────────────────────────────────┘
```

### 4.2 Component Description

| Component | Purpose | Technologies |
|-----------|---------|---------------|
| **Coordinator Agent** | Orchestrates workflow | Google ADK Agents |
| **Web Research Agent** | Finds citing papers | Google Search API |
| **New Research Agent** | Synthesizes gaps | Gemini LLM |
| **Telegram Bot** | User interaction | Aiogram 3.29.0+ |
| **Paper Analyzer** | Metadata extraction | Python, LLM parsing |

---

## 5. Data Requirements

### 5.1 Input Data
- Academic paper (PDF, URL, or metadata)
- User research query or topic

### 5.2 Output Data
- Extracted paper metadata
- List of citing papers with metadata
- Future research suggestions with rationale
- Summary report

### 5.3 Data Storage
- Configuration: Environment variables
- Logs: File-based or console output
- Cache: Optional in-memory results (future)

---

## 6. Interface Requirements

### 6.1 User Interfaces

#### 6.1.1 Telegram Bot Interface
```
User: /start
Bot: Welcome to ResearchFlow AI! Send me a paper or topic to analyze.

User: [Paper PDF or reference]
Bot: Analyzing paper... (workflow executes)
Bot: [Results with findings and suggestions]
```

#### 6.1.2 CLI Interface
```bash
python -m my_agent.bot                    # Start Telegram bot
# Or use ADK CLI for direct agent invocation
```

### 6.2 System Interfaces
- **Google ADK Interface**: Agent registration and tool binding
- **Google Search API**: Paper discovery queries
- **Gemini API**: NLU and synthesis
- **Telegram Bot API**: Message polling and responses

---

## 7. Future Enhancements

### 7.1 Telegram Bot Integration
- **F-TG-01**: Deep integration of Telegram bot with academic coordinator
  - Route user messages from Telegram → Coordinator Agent
  - Stream research results back to user in chat
  - Support multi-turn conversations for refined queries
  
- **F-TG-02**: Advanced Telegram features
  - Document uploads (PDF analysis)
  - Inline search capabilities
  - Result caching and history
  - User preferences and saved searches

- **F-TG-03**: Telegram group support
  - Collaborative research sessions
  - Shared research findings
  - Team-based research projects

### 7.2 AI Agents Stack Enhancement
- **F-AI-01**: Core AI-Agents Stack Integration
  - Implement ReAct (Reasoning + Acting) pattern across all agents
  - Add Chain-of-Thought prompting for better reasoning
  - Integrate memory systems for agent context retention
  
- **F-AI-02**: Advanced Agent Capabilities
  - Multi-hop reasoning for complex research queries
  - Self-reflection and error correction in agents
  - Tool use optimization and learning from past interactions
  
- **F-AI-03**: Agent Specialization
  - Methodology agent (research method analysis)
  - Data agent (dataset and benchmark discovery)
  - Comparison agent (comparative analysis of papers)
  - Citation network agent (graph analysis of paper relationships)
  
- **F-AI-04**: Agent Communication & Collaboration
  - Agent-to-agent message passing
  - Consensus mechanisms for conflicting suggestions
  - Hierarchical agent supervision and quality control

### 7.3 Research Features
- **F-RES-01**: Citation network visualization
  - Graph database integration
  - Interactive citation network explorer
  - Trend identification across networks

- **F-RES-02**: Enhanced paper analysis
  - Table and figure extraction
  - Research methodology parsing
  - Dataset and code repository discovery

- **F-RES-03**: Collaborative features
  - Shared research projects
  - Team annotations and comments
  - Export and report generation

### 7.4 System Improvements
- **F-SYS-01**: Database backend (PostgreSQL/MongoDB)
- **F-SYS-02**: Web interface and dashboard
- **F-SYS-03**: Advanced caching and performance optimization
- **F-SYS-04**: Monitoring, logging, and analytics

---

## 8. Acceptance Criteria

### 8.1 Core Functionality
- [ ] Paper analysis extracts all required metadata
- [ ] Web research agent returns at least 10 relevant citing papers
- [ ] New research agent generates meaningful suggestions with rationale
- [ ] Coordinator successfully orchestrates full workflow
- [ ] Telegram bot responds to `/start` command

### 8.2 Quality Criteria
- [ ] All code follows PEP 8 standards
- [ ] Functions include docstrings
- [ ] System handles errors gracefully
- [ ] README includes setup and usage instructions
- [ ] Response times meet performance requirements

### 8.3 Documentation
- [ ] SRS document is complete and up-to-date
- [ ] README links to SRS for detailed understanding
- [ ] Code comments explain complex logic
- [ ] Contribution guidelines are documented

---

## 9. Glossary

| Term | Definition |
|------|-----------|
| **Agent** | Autonomous system that perceives environment and takes actions |
| **Coordinator** | Master agent orchestrating workflow and sub-agents |
| **Sub-Agent** | Specialized agent focused on specific tasks |
| **Tool** | Callable function or API integration available to agents |
| **Workflow** | Sequence of steps executed by coordinator |
| **Seminal Paper** | Foundational publication in a research area |

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-09 | orignlkartik1 | Initial SRS document creation |

---

## 11. Appendices

### A. Environment Variables
```
BOT_TOKEN=your_telegram_bot_token
GOOGLE_ADK_CREDENTIALS=path/to/credentials.json
```

### B. Technology Stack
- **Language**: Python 3.14+
- **Agent Framework**: Google ADK
- **Bot Framework**: Aiogram 3.29.0+
- **Package Manager**: uv
- **LLM**: Google Gemini

### C. References
- Google ADK Documentation
- Telegram Bot API Documentation
- Aiogram Documentation
- Python PEP 8 Style Guide

