# Selected projects

## Personal Twin (this project)

A generic, provider-agnostic RAG backend. It starts as a "personal twin" that answers
questions about me from a folder of documents, but the pipeline is built to ingest any
corpus — a company knowledge base, product docs, anything. LLMs and embedders are
switchable by config (Ollama locally, Anthropic or OpenAI in the cloud), the vector store
is pluggable (Chroma by default, pgvector optional), and every answer is grounded with
verified citations. It ships with evaluations, tracing, tests, and CI.

## Deep Research Agent

A local-first agentic research assistant built on LangGraph. It plans search queries,
fetches and de-duplicates sources, reflects on gaps in a loop under a hard iteration
budget, and streams back a cited markdown report. It showcases the engineering *around* an
agent: provider independence, schema'd tools, structured step events over SSE, an eval
harness, and Docker/CI hygiene.

## Atlas Enterprise Knowledge Assistant

An always-current, human-in-the-loop RAG system for enterprise knowledge. It uses a
uv monorepo layout, pgvector retrieval, role-based provider switching, and a pluggable
document-source registry so new connectors (S3, Confluence) drop in without touching the
retrieval or agent code.

## What ties them together

Each project is deliberately built to be production-grade rather than a demo: typed
config, explicit failure handling, observability, evaluations, and documentation that lets
someone else run the thing without me in the room.
