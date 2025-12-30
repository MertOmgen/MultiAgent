# Senior Developer Guidelines: Using Agents as Auxiliary Tools

**Repository:** `MertOmgen/MultiAgent`  
**Audience:** Senior developers and reviewers  
**Purpose:** Make AI agents (including GitHub Copilot in VSCode) *reliable auxiliary tools*—not authority—by enforcing engineering standards, predictable workflows, and verifiable outputs.

---

## 1) Core Principles (Non‑Negotiables)

1. **Agents assist; humans decide.** Treat agent output as a draft that must be reviewed, tested, and validated.
2. **Prefer small, reversible changes.** Request incremental diffs over large rewrites.
3. **Evidence over vibes.** Require agents to back performance, memory, and correctness claims with measurements, profiling, or references.
4. **No hidden work.** Agents must state assumptions and constraints (runtime, framework, OS, thread model, etc.).
5. **Make it observable.** Add or improve logging, metrics, tracing, and tests when touching non-trivial behavior.
6. **Match project conventions.** Follow existing style, architecture, naming, error handling, and dependency rules.

---

## 2) Standard Agent Workflow

Use this workflow when asking an agent to help with code changes.

### A. Context & Constraints
Provide:
- Goal and acceptance criteria (what “done” means)
- Target modules/files
- Performance/SLO expectations
- Environment constraints (runtime, versions, deployment patterns)
- Non-goals (what should not change)

### B. Ask for a Plan First
Require:
- Proposed approach
- Impacted components
- Risk analysis and rollback plan
- Test strategy

### C. Request a Minimal Diff
Ask the agent to:
- Keep changes scoped
- Avoid style-only churn
- Split refactors from behavior changes

### D. Verification Checklist
Agent should propose:
- Unit/integration tests
- Benchmarks or profiling steps (when performance is mentioned)
- Memory/GC checks (when allocations or long-running processes are involved)

---

## 3) Focus Area: Memory Leaks

### What to look for
- Unbounded growth in collections/caches
- Event/listener subscriptions not removed
- Timers/schedulers not disposed
- Async tasks/promises capturing large closures
- Thread-locals or static references holding objects
- Resource handles not closed (files, sockets, DB connections)

### Agent instructions
- Identify ownership and lifecycle: *who allocates, who frees, when?*
- Suggest using scoped lifetimes / RAII / `using` / `defer` patterns where applicable
- Add tests or harnesses for long-running behavior (soak tests)
- Recommend tools for leak detection appropriate to the stack (heap snapshots, profilers)

### Expected outputs
- A concise leak hypothesis
- The code paths responsible
- A remediation diff that enforces deterministic cleanup
- A validation plan (repro + measurement)

---

## 4) Focus Area: Caching

### Goals
- Improve latency/throughput while protecting correctness.

### Design checklist
- **Cache key correctness:** include all inputs that affect output (locale, auth scope, feature flags, versioning)
- **Invalidation strategy:** TTL, event-driven invalidation, versioned keys
- **Size bounds:** LRU/SLRU, max entries, max memory
- **Concurrency:** stampede protection (single-flight), lock granularity
- **Observability:** hit rate, eviction count, load time
- **Safety:** avoid caching failures unless explicitly desired

### Agent instructions
- Propose cache policy and justify it
- Ensure bounded growth and clear invalidation
- Avoid global mutable caches unless necessary and documented

---

## 5) Focus Area: Design Patterns & Architecture

### Use patterns intentionally
- Prefer **composition over inheritance**
- Enforce **SOLID** where it improves maintainability (not dogmatically)
- Use **Strategy** for algorithm variability, **Factory** for construction complexity, **Adapter** for integration boundaries
- Use **Decorator** to add cross-cutting behavior without editing cores
- Use **Observer/Event Bus** carefully (avoid implicit coupling)

### Agent instructions
- Explain why a pattern fits and what it replaces
- Avoid introducing frameworks/dependencies without strong justification
- Preserve existing layering (UI ↔ service ↔ domain ↔ persistence)

---

## 6) Focus Area: Parallel Programming

### Common pitfalls
- Data races and non-atomic updates
- Deadlocks due to lock ordering
- Over-parallelization (context switching > work)
- False sharing and contention hot spots
- Work stealing + unbounded queues

### Agent instructions
- Prefer safe primitives (thread-safe collections, structured concurrency)
- Minimize shared mutable state; use immutability/message passing
- Document lock ordering and critical sections
- Ensure cancellation/timeouts are honored
- Provide a benchmark and a correctness test

### Review checklist
- Are there deterministic tests for concurrency issues?
- Are error paths and cancellation safe?
- Are resources correctly joined/awaited?

---

## 7) Focus Area: Code Smells

Ask agents to flag and propose fixes for:
- God objects / large classes
- Deep nesting / complex conditionals
- Primitive obsession / poor domain modeling
- Feature envy / leaky abstractions
- Duplicated logic and inconsistent behavior
- Hidden coupling via globals/singletons
- Overly clever code that reduces readability

### Agent instructions
- Provide refactor steps that do not change behavior
- Suggest targeted abstractions with clear names
- Keep public APIs stable unless explicitly asked

---

## 8) Focus Area: Performance Bottlenecks

### Performance methodology
- **Measure first.** No optimization without a baseline.
- Establish:
  - Hot path identification (profiling)
  - Throughput/latency metrics
  - Allocation rate/GC pressure
  - I/O wait vs CPU bound

### High-yield areas
- N+1 queries / chatty network calls
- Excessive object allocations / string concatenations
- Inefficient data structures (O(n²) where n grows)
- Excess logging in hot paths
- Unnecessary serialization/deserialization

### Agent instructions
- Produce a “before/after” plan with metrics
- Recommend algorithmic improvements before micro-optimizations
- Keep optimizations readable; encapsulate complexity

---

## 9) Focus Area: Readability & Maintainability Improvements

### Code style expectations
- Prefer clear names over comments
- Keep functions small and single-purpose
- Use guard clauses to reduce nesting
- Avoid “magic numbers”; use constants/config
- Make error handling explicit and consistent

### Documentation expectations
- Document *why* a decision was made (tradeoffs), not obvious *what*
- Update READMEs and inline docs when behavior changes

### Agent instructions
- Propose improvements that reduce cognitive load
- Avoid churn: do not reformat unrelated code

---

## 10) Testing & Quality Gates

When an agent proposes changes, require:
- Relevant unit tests
- Integration tests for boundary behavior
- Regression tests for fixed bugs
- Benchmarks for performance-sensitive changes
- Linters/static analysis recommendations (where applicable)

Minimal acceptance checklist:
- Builds/CI pass
- Tests added/updated
- No new warnings
- Clear commit message and PR description

---

## 11) How GitHub Copilot in VSCode Must Follow These Instructions

### Operating mode
Copilot should:
- Generate **small, reviewable** code blocks
- Prefer **existing patterns** in this repository
- Avoid introducing new dependencies unless requested
- Include test suggestions with code changes
- Add comments only when they capture non-obvious intent/tradeoffs

### Prompting rules for Copilot (recommended)
When asking Copilot to implement changes, include:
- *"Follow `instructions.md` in the repo. Keep diffs minimal. Add/adjust tests."*
- Acceptance criteria and constraints
- Performance/memory considerations if relevant

### Copilot response expectations
Copilot output should include:
- A brief plan
- The modified files list
- Any risks and how to validate them
- Commands to run tests/formatters/benchmarks

### Review discipline
- Treat Copilot suggestions as untrusted until verified.
- Require it to point to the exact code and explain changes.
- Reject large refactors without an explicit request.

---

## 12) Quick PR Review Checklist (Paste into PRs)

- [ ] Scope is minimal; no unrelated churn
- [ ] Memory/resource lifecycle is correct (no leaks)
- [ ] Caching is bounded and has invalidation strategy
- [ ] Concurrency is safe (no races/deadlocks), cancellation handled
- [ ] Design follows repository patterns and SOLID where useful
- [ ] Code smells reduced; complexity not increased
- [ ] Performance claims backed by measurements
- [ ] Readability improved (naming, structure, docs)
- [ ] Tests added/updated and pass
- [ ] Observability updated if behavior changed

---

## 13) Suggested .vscode Alignment (Optional)

If you add workspace instructions or prompts, ensure they reference this file rather than duplicating guidance.

Example snippet to include in team docs:
> “Copilot must follow the rules in `instructions.md`. Prefer minimal diffs, measurable improvements, and add tests. No new dependencies without approval.”
