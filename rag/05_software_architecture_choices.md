---
title: Software architecture decision guide
kb: B
category: architecture
licence: Original team notes (general guidance; verify against official documentation)
---
# Software architecture decision guide

## Monolith or microservices
- **Monolith:** one deployable application. Simple to build, test, and deploy. Best for small teams and early products.
- **Microservices:** many small services communicating over a network. Allow independent scaling and deployment but add complexity (networking, monitoring, distributed data).
A common recommendation is to start with a well-structured modular monolith and split services only when there is a clear need.

## API style
- **REST:** resource-based endpoints over HTTP; widely understood, easy to cache and document (OpenAPI).
- **GraphQL:** clients request exactly the fields they need; useful with many client types, but adds server complexity.
- **Event-driven / messaging:** services communicate through queues or events; suited to background processing and loose coupling.

## Data storage
- **Relational (for example PostgreSQL):** strong consistency, joins, constraints, mature tooling. A good default for most business applications.
- **Document stores:** flexible schema; useful when data is naturally nested and schema changes often.
- **Key-value and caches (for example Redis):** fast access for sessions, caching, and queues.
- **Vector search:** stores embeddings for semantic search; can live inside PostgreSQL with the pgvector extension for small to medium workloads.
Choose based on data shape, consistency needs, and team experience, not trends.

## Synchronous and asynchronous work
Use background workers for long or unreliable tasks (calling external APIs, generating documents). Return a job identifier to the client, show progress, and retry failures with backoff.

## Authentication and authorisation
Hash passwords with a modern algorithm (argon2 or bcrypt), use short-lived tokens, check ownership on every request, and apply least privilege. Never store secrets in code.

## Scalability basics
Cache repeated results, add indexes for frequent queries, paginate lists, keep services stateless so more copies can run behind a load balancer, and measure before optimising.

## Reliability and observability
Add timeouts and retries to external calls, log with request identifiers, track errors and latency, and keep backups.

## Deployment
Containers (Docker) give repeatable environments. Define services in a compose file for development; use managed services or an orchestrator when scale demands it.

## Recording decisions
For each major choice record the options considered, the reason for the decision, and the trade-offs (an architecture decision record). Revisit when requirements change.
