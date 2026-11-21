---
title: Requirements engineering basics
kb: B
category: requirements
licence: Original team notes (general guidance)
---
# Requirements engineering basics

## Why requirements matter
Unclear or changing requirements are a leading cause of software project problems. Good requirements are shared, testable, and prioritised.

## Types
- **Functional requirements:** what the system does ("The system shall let a user reset a password").
- **Non-functional requirements:** how well it does it (performance, security, usability, reliability, maintainability, portability).
- **Constraints:** fixed limits such as budget, technology, law, or deadline.
- **Assumptions and dependencies:** things believed true or relied upon.

## Qualities of a good requirement
Clear (one interpretation), testable (you can check it), necessary, consistent with others, feasible, and traceable to a goal. Avoid vague words such as "fast", "user-friendly", or "etc."; use measurable statements ("search results appear within 2 seconds for 95% of requests").

## User stories and acceptance criteria
Format: "As a [role], I want [capability] so that [benefit]." Add acceptance criteria in the form Given/When/Then so the team can verify when the story is done.

## Prioritisation
Use MoSCoW (Must, Should, Could, Won't) or value versus effort. Ask what the first release truly needs.

## Software Requirements Specification (SRS) structure
1. Introduction: purpose, scope, definitions, users.
2. Overall description: product perspective, functions, environment, constraints, assumptions.
3. Functional requirements grouped by module with identifiers.
4. Non-functional requirements.
5. Interface requirements.
6. Use cases or user stories.
7. Acceptance criteria and traceability.

## Use cases
Describe an actor, a goal, a main flow, alternative flows, preconditions, and postconditions. Use them to find missing requirements.

## Managing change
Give every requirement an identifier, keep a change log, and assess the impact of a change on design, cost, and schedule before accepting it.
