---
name: rag-knowledge-base
description: Retrieval-Augmented Generation (RAG) on local files (PDFs, Markdown, Docs, Spreadsheets) with embeddings and vector search.
---

# Retrieval-Augmented Generation (RAG) Skill

Enables conversational question-answering over local documents, proprietary PDFs, codebase documentation, and knowledge archives.

## RAG Pipeline Architecture

```mermaid
graph TD
    Docs[Local PDFs / Markdown / CSV] --> Chunk[Text Chunking & Overlap]
    Chunk --> Embed[Local Embeddings Model]
    Embed --> VectorDB[(Vector DB / Chroma / FAISS)]
    UserQuery[User Query] --> EmbedQuery[Embed Query]
    EmbedQuery --> Search[Top-K Semantic Similarity Search]
    Search --> Context[Inject Relevant Chunks into Prompt]
    Context --> LLM[Generate Grounded Answer]
```

## Recommended Tech Stack
* **Vector Store**: `chromadb` or `faiss-cpu`.
* **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (fast, lightweight, runs 100% locally).
* **Chunking Strategy**: 500-token chunks with 50-token overlap to maintain semantic continuity across boundaries.
