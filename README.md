# MultiAgent

This repository explores an **AutoGen-style multi-agent roadmap** and a practical, reproducible way to orchestrate agents locally.

---

## AutoGen Multi‑Agent Roadmap (Detailed)

> This section is restored from the previously detailed roadmap content (commit `b36b5c6c9bf470509d9763f992507d2eeb628f72`) and then extended with the current project stack and conventions.

### 1) Define the vision & constraints

- **Goal**: a multi-agent workflow that can take a requirement, design a solution, generate code, test it, and iterate.
- **Constraints**:
  - Prefer **local-first** execution.
  - Preserve **traceability**: every decision and artifact should be saved.
  - Support multiple “roles” (architect, backend, frontend, QA, product).

### 2) Identify core agent roles

A typical baseline team:

- **Orchestrator / Manager**: assigns tasks, enforces process
- **Product / Requirements**: clarifies goals, user stories, acceptance criteria
- **Architect**: produces high-level architecture, interfaces, data model
- **Backend engineer**: implements APIs/services
- **Frontend engineer**: implements UI and integration
- **QA / Tester**: test plans, automated tests, bug reports
- **Reviewer**: code review, security checks, style checks

### 3) Define communication & protocols

- Use **structured prompts** and **explicit deliverables** for each agent.
- Maintain a consistent format:
  - Inputs
  - Assumptions
  - Plan
  - Outputs (files created/updated)
  - Next steps

### 4) Decide on orchestration model

Options:

- **Sequential**: one agent after another (simple, predictable)
- **Parallel**: independent tasks run concurrently (fast)
- **Hybrid**: parallel creation + sequential integration + review

Recommended:

- Architect + Product in parallel → Backend + Frontend in parallel → QA + Review → Iterate.

### 5) Add memory & state

- **Short-term memory**: keep context for current run
- **Long-term memory**: store decisions, architecture notes, constraints, and known issues
- Persist:
  - prompts
  - agent outputs
  - intermediate design docs
  - test results

### 6) Tooling integration

Agents become powerful when they can “act”:

- Repo/file operations
- Test execution
- Linting/formatters
- API calls
- DB migrations

### 7) Guardrails & quality gates

- Validate requirements coverage against acceptance criteria
- Enforce security & privacy rules
- Run unit/integration tests
- Add static analysis gates
- Review diffs before merge

### 8) Iteration loop

- Detect failures → gather evidence → propose fixes → implement → retest
- Save artifacts each iteration so progress is auditable.

### 9) Scaling the system

- Add new specialized agents (DevOps, Data, Security)
- Add “budget/time” constraints
- Add task routing based on domain heuristics

---

## Project Stack (Current)

This project is intentionally **polyglot**:

- **Orchestration**: **Python** (multi-agent controller / workflow runner)
- **Backend**: **.NET (C#)**
- **Frontend**: **Vue 3**
- **Database**: **PostgreSQL**
- **LLM**: **Fully local** via **Ollama** using **`llama3.1`**

### Orchestration vs generated code

- The **agents and orchestration logic live in Python** (e.g., running conversations, routing tasks, saving artifacts).
- The **generated application code** produced by agents is **.NET/C# for backend** and **Vue 3 for frontend**.

This separation keeps the workflow flexible (Python) while targeting a production-friendly stack (.NET/Vue/Postgres).

---

## Local LLM (Ollama)

To run fully offline/local:

1. Install Ollama: https://ollama.com/
2. Pull the model:
   
   ```bash
   ollama pull llama3.1
   ```

3. Ensure your orchestrator points to Ollama’s local endpoint and uses `llama3.1`.

---

## Outputs & Artifact Structure

All agent artifacts and generated deliverables are stored under `outputs/`.

```
outputs/
  design/
  backend/
  frontend/
  qa/
  chat_history/
```

Guidance:

- `outputs/design`: architecture notes, diagrams (textual), ADRs, API contracts
- `outputs/backend`: generated C#/.NET code snippets, API drafts, migration scripts
- `outputs/frontend`: Vue 3 components, pages, state management drafts
- `outputs/qa`: test plans, test cases, bug reports, automation scripts
- `outputs/chat_history`: raw agent conversations per run (for traceability)

---

## Roadmap Next Steps

- Add a minimal Python orchestrator that:
  - runs a multi-agent conversation locally (Ollama)
  - writes artifacts into `outputs/`
  - supports iterative loops (design → implement → test → fix)
- Add skeleton .NET backend + Vue 3 frontend + Postgres compose/dev config.
