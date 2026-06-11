# Architecture

DataPilot-AI is an AI Agent Platform for Data Engineering built with Clean Architecture. Business logic depends on interfaces, while infrastructure implementations such as DeepSeek and ChromaDB remain swappable.

## Clean Architecture

```mermaid
flowchart TB
    Presentation[Presentation Layer<br/>FastAPI + Streamlit]
    Application[Application Layer<br/>RAG, Text2SQL, Review, Warehouse, Agent]
    Domain[Domain Layer<br/>Entities + Ports]
    Infrastructure[Infrastructure Layer<br/>DeepSeek, ChromaDB, Loaders, Embeddings]

    Presentation --> Application
    Application --> Domain
    Infrastructure --> Domain
    Presentation -. dependency injection .-> Infrastructure
```

## Layers

### Presentation Layer

- FastAPI routes expose health, knowledge, chat, agent, Text2SQL, SQL review, warehouse design, and runtime config APIs.
- Pydantic v2 schemas validate all request and response contracts.
- Streamlit pages call only FastAPI APIs through `frontend/services/backend_client.py`.

### Application Layer

- RAG services coordinate ingestion, chunking, retrieval, citation generation, and grounded answering.
- Text2SQL builds prompts, parses LLM JSON, validates generated SQL, and returns optimization hints.
- SQL Review combines deterministic rules with optional LLM explanations.
- Warehouse Design generates layered data warehouse outputs, Hive DDL, metrics, relationships, and recommendations.
- Agent uses LangGraph to classify intent, route workflows, execute specialist nodes, and format responses.

### Domain Layer

- Entities define documents, chunks, metadata, and vector search contracts.
- Ports define `LLMProvider` and `VectorStore`, keeping business logic independent from DeepSeek and ChromaDB.

### Infrastructure Layer

- DeepSeek provider implements async chat, streaming, retry, timeout, health check, and usage tracking.
- ChromaDB adapter implements vector store operations and persists under project-local data paths.
- Document loaders support TXT, Markdown, PDF, and DOCX.
- Embedding provider abstraction enables future OpenAI, Ollama, and local embedding backends.

## System Architecture

```mermaid
flowchart LR
    Browser[Browser] --> Streamlit[Streamlit Frontend]
    Streamlit --> FastAPI[FastAPI Backend]
    FastAPI --> Agent[LangGraph Agent]
    FastAPI --> Knowledge[Knowledge APIs]
    Agent --> RAG[RAG Service]
    Agent --> Text2SQL[Text2SQL Service]
    Agent --> Review[SQL Review Service]
    Agent --> Warehouse[Warehouse Designer]
    RAG --> VectorPort[VectorStore Port]
    RAG --> LLMPort[LLMProvider Port]
    Text2SQL --> LLMPort
    Review --> LLMPort
    Warehouse --> LLMPort
    VectorPort --> Chroma[ChromaDB]
    LLMPort --> DeepSeek[DeepSeek API]
```

## RAG Pipeline

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant Ingest as Document Ingestion
    participant Loader as Document Loader
    participant Chunk as Chunking Service
    participant Embed as Embedding Provider
    participant Store as Vector Store
    participant RAG as RAG Service
    participant LLM as LLM Provider

    U->>API: Upload document
    API->>Ingest: ingest_file
    Ingest->>Loader: load content
    Ingest->>Chunk: split text
    Ingest->>Embed: generate vectors
    Ingest->>Store: add documents
    U->>API: Ask question
    API->>RAG: answer
    RAG->>Embed: embed query
    RAG->>Store: similarity search
    RAG->>LLM: grounded prompt
    LLM-->>RAG: answer
    RAG-->>API: answer + citations
```

## Text2SQL Flow

```mermaid
flowchart TD
    NL[Natural Language Question] --> Schema[Schema Context Parsing]
    Schema --> Prompt[Prompt Builder]
    Prompt --> LLM[LLMProvider]
    LLM --> JSON[Parse JSON Payload]
    JSON --> Validate[SQL Validator]
    Validate --> Result[SQL + Explanation + Validation + Suggestions]
```

## SQL Review Flow

```mermaid
flowchart TD
    SQL[SQL Input] --> Parser[SQL Parser]
    Parser --> Rules[Rule Engine]
    Rules --> Score[Risk Score + Issues]
    Score --> LLM[Optional LLM Explanation]
    LLM --> Review[Review Response]
```

## Warehouse Design Flow

```mermaid
flowchart TD
    Req[Business Requirement] --> Domain[Domain Detection]
    Domain --> Template[Template Design]
    Req --> RAG[Optional RAG Context]
    RAG --> Prompt[Warehouse Prompt]
    Prompt --> LLM[LLM Provider]
    LLM --> Merge[Merge with Template]
    Merge --> DDL[Hive DDL]
    Merge --> Metrics[Metric Definitions]
    Merge --> Flow[ODS to DWD to DWS to ADS]
```

## LangGraph Agent Flow

```mermaid
flowchart TD
    Query[User Query] --> Classify[Intent Classification Node]
    Classify -->|RAG| RAGNode[RAG Node]
    Classify -->|TEXT2SQL| SQLNode[Text2SQL Node]
    Classify -->|SQL_REVIEW| ReviewNode[SQL Review Node]
    Classify -->|WAREHOUSE_DESIGN| WarehouseNode[Warehouse Design Node]
    Classify -->|GENERAL_CHAT| ChatNode[General Chat Node]
    Classify -->|UNKNOWN| UnknownNode[Unknown Node]
    SQLNode -->|TEXT2SQL_SQL_REVIEW| ReviewNode
    RAGNode --> Format[Response Formatter]
    SQLNode --> Format
    ReviewNode --> Format
    WarehouseNode --> Format
    ChatNode --> Format
    UnknownNode --> Format
    Format --> Response[Agent Response]
```

## Frontend/Backend Interaction

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant Client as BackendClient
    participant API as FastAPI
    participant Agent as Agent Graph

    User->>UI: Enter request
    UI->>Client: stream_agent_chat
    Client->>API: POST /api/v1/agent/chat/stream
    API->>Agent: run workflow
    Agent-->>API: metadata, token, result, done
    API-->>Client: SSE events
    Client-->>UI: parsed events
    UI-->>User: response + structured results
```

## Deployment Topology

```mermaid
flowchart LR
    User[User Browser] --> Frontend[frontend<br/>Streamlit:8501]
    Frontend --> Backend[backend<br/>FastAPI:8000]
    Backend --> Chroma[chromadb<br/>HTTP:8001 / Persistent Data]
    Backend --> DeepSeek[DeepSeek API]
    Backend -. optional .-> Ollama[ollama profile<br/>11434]
    Chroma --> Data[(data/chromadb)]
    Backend --> Uploads[(data/uploads)]
    Backend --> Logs[(data/logs)]
```
