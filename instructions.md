# MultiAgent – Senior Dev Instructions for Copilot & Agent-Assisted Development

**Repo:** `MertOmgen/MultiAgent`  
**Owner mindset:** Senior developer (you) supervises development, performs commit/PR reviews, uses agents as auxiliary tools.  
**Primary focus:** memory leaks, caching, design patterns, parallel programming, code smells, performance bottlenecks, readability.

---

## 1) Non‑Negotiables (Golden Rules)

1. **Agents assist; you decide.** Treat AI output as a draft; validate with tests and review.
2. **Small, reviewable diffs.** Prefer incremental changes over rewrites.
3. **Evidence-based performance work.** No optimization claims without measurement/profiling.
4. **No hidden side effects.** Agents must declare assumptions, constraints, tradeoffs.
5. **Keep repo conventions.** Naming, folder structure, error handling, logging, dependency policy.
6. **Maintain traceability.** Decisions and artifacts must be reproducible and easy to audit.

---

## 2) How to Use Copilot in VSCode (Behavior Expectations)

When you ask Copilot for changes, Copilot must:

- Propose a **brief plan** first (especially for non-trivial changes).
- Prefer **minimal diffs** (avoid unrelated reformatting/churn).
- Match the existing architecture and patterns.
- Include:
  - error handling strategy
  - edge cases
  - test updates or new tests
- Provide a **validation section**:
  - commands to run
  - what success looks like
  - risks/rollback notes (if relevant)

Copilot must avoid:

- Large refactors without explicit request
- Adding new dependencies without justification and approval
- Introducing global mutable state or “magic” concurrency
- Hardcoding secrets or environment-specific values

**Recommended prompt prefix to Copilot:**
> “Follow `instructions.md`. Keep diffs minimal, add/adjust tests, and explain risks and validation steps.”

---

## 3) PR / Commit Review Checklist (Use on Every PR)

### Correctness & Reliability
- [ ] Input validation and error paths handled
- [ ] Deterministic behavior where needed (idempotency, retries, timeouts)
- [ ] Exceptions/errors mapped consistently (esp. API boundaries)

### Readability
- [ ] Clear naming (domain terms)
- [ ] Functions/classes have single responsibility
- [ ] Guard clauses used to reduce nesting
- [ ] Comments explain *why*, not *what*

### Code Smells
- [ ] No duplicated logic
- [ ] No god classes/methods
- [ ] No hidden coupling via globals/singletons
- [ ] No “clever” code that reduces clarity

### Performance
- [ ] No known N+1 patterns / chatty I/O
- [ ] Hot-path changes have measurements
- [ ] Allocation/GC concerns considered (where applicable)
- [ ] Logging not excessive in hot paths

### Security
- [ ] AuthN/AuthZ correct where applicable
- [ ] Secrets not in code
- [ ] Dependency changes justified

### Tests
- [ ] Happy path test exists
- [ ] Negative/edge test exists
- [ ] Regression test added for bug fixes
- [ ] Flakiness risk considered

---

## 4) Memory Leaks & Resource Management

### General rules
- All resources must have a clear **owner** and **lifecycle**.
- Avoid unbounded growth in memory (collections, caches, queues).
- Subscriptions must be unsubscribed (events/listeners).
- Timers/schedulers must be disposed/stopped.
- Fire-and-forget tasks must be avoided; if used, they must have:
  - error handling/logging
  - cancellation strategy

### Copilot requirements
When you ask about memory leaks, Copilot must output:
1. Leak hypothesis (what holds references and why it grows)
2. Affected code paths
3. Fix approach (lifecycle, cleanup)
4. How to verify (profiler/soak test idea)

---

## 5) Caching Rules (If Introduced or Modified)

Caching is only allowed when:
- there is a real latency/throughput problem, **and**
- correctness and invalidation strategy are defined.

### Cache checklist
- **Key correctness:** includes all inputs that affect output
- **Scope correctness:** tenant/user/security context is respected
- **Bounded size:** max entries / max memory
- **Invalidation:** TTL or event-driven invalidation defined
- **Stampede protection:** single-flight/request coalescing for hot keys
- **Metrics:** hit rate, evictions, load latency

Copilot must describe:
- policy (TTL/eviction/invalidation)
- risks (staleness, stampede)
- how to observe success (metrics)

---

## 6) Design Patterns & Architecture Guidance

Use patterns intentionally:
- Composition over inheritance
- Strategy for variability
- Adapter for external integrations
- Decorator for cross-cutting concerns
- Factory only when construction is complex

Avoid:
- Over-abstraction (interfaces for everything)
- Service locator
- Unjustified framework additions

Copilot must explain:
- why the pattern fits
- what it replaces
- tradeoffs and alternatives

---

## 7) Parallel Programming / Concurrency Rules

Concurrency is allowed only with:
- bounded parallelism
- safe shared state handling
- proper cancellation/timeouts
- deterministic error handling

### Non-negotiable concurrency rules
- No `.Result` / `.Wait()` blocking on async
- No unbounded `WhenAll` over unknown-sized lists
- Use cancellation tokens / abort mechanisms
- Prefer immutability and message passing

Copilot must provide:
- concurrency model summary
- failure/cancellation behavior
- test or validation plan for races/deadlocks

---

## 8) Performance Methodology (Mandatory for “Optimization”)

1. Define the metric: latency/throughput/memory
2. Baseline measurement
3. Identify hotspot (profiling)
4. Apply smallest change
5. Re-measure and compare
6. Document results in PR description

Copilot must not propose “optimizations” without:
- baseline + after measurement plan, or
- a clear, high-confidence algorithmic improvement justification

---

## 9) Readability Standards

- Prefer explicit, boring code
- Avoid deep nesting; use guard clauses
- Remove magic numbers; use constants/config
- Keep files cohesive; split when responsibilities diverge
- Prefer descriptive names over comments

---

## 10) Agent Usage Protocol (Multi-Agent Context)

When using agents (Designer/Backend/Frontend/QA), require each to output:

- Deliverables
- Assumptions
- Risks
- Next steps / handoff notes
- Validation plan

If agents generate artifacts, store them under:
- `outputs/design/`
- `outputs/backend/`
- `outputs/frontend/`
- `outputs/qa/`
- `outputs/chat_history/`

---

## 11) PR Template (Paste into PR Body)

**Goal:**  
**Approach:**  
**Files changed:**  
**Risks:**  
**Validation:** (commands + results)  
**Perf (if relevant):** baseline vs after  
**Notes:** any follow-ups

---
