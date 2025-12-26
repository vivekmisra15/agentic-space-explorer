# Key Principles: Tool Registry & Execution Runtime

This document captures the core design principles behind the **tool registry** and **execution runtime** used by the AnalystAgent.  
These principles are framework-agnostic and apply to agentic systems built from first principles.

---

## 1. Separate *Planning* from *Execution*

The LLM is used strictly as a **planner**, not an executor.

- The LLM decides *what* analysis steps to perform
- Python code decides *how* those steps are executed
- All numerical computation and plotting are deterministic

This separation prevents hallucinations, improves debuggability, and makes runs reproducible.

> **Rule of thumb:**  
> If the output must be correct, it should not be computed by the LLM.

---

## 2. Tools Are Deterministic, Side-Effecting Units

Each tool in the registry:

- Has a single, well-defined responsibility
- Is deterministic given its inputs
- Produces observable side effects (tables, plots, files)

Tools do **not**:
- Call the LLM
- Inspect or modify global state directly
- Make decisions about control flow

They simply *do work*.

---

## 3. The Tool Registry Is the System’s Capability Boundary

The tool registry defines **everything the agent is allowed to do**.

- The LLM can only choose tools that exist in the registry
- Each tool has a fixed argument schema
- Unsupported behavior is impossible by construction

This acts as a **safety rail**:
- Prevents the planner from inventing actions
- Keeps execution grounded in known capabilities
- Makes the system extensible in a controlled way

Adding a new capability means adding a new tool — nothing else.

---

## 4. Plans Are Data, Not Code

The LLM produces a **plan as structured data (JSON)**.

A plan:
- Is validated before execution
- Can be logged, stored, replayed, or inspected
- Represents *intent*, not implementation

Because plans are data:
- They can be versioned
- They can be debugged independently of execution
- They can be shown to users or developers for transparency

---

## 5. Context Is the Runtime’s Working Memory

The execution runtime maintains an explicit `context` object that holds:

- The base dataset (`df`)
- Named intermediate tables (`context["tables"]`)
- Generated artifacts (`context["artifacts"]`)

Context is:
- Local to a single run
- Mutable during execution
- Explicitly passed to every tool

This avoids hidden state and makes tool dependencies obvious.

---

## 6. Shared State Is for Stable, Cross-Agent Artifacts Only

The global shared state is **not** a scratchpad.

It stores only:
- Paths to generated artifacts (plans, reports, plots)
- Stable outputs needed by downstream agents
- Execution metadata and logs

Intermediate data lives in `context`, not in shared state.

> **If another agent or the UI needs it, it belongs in state.  
> If it’s just part of execution, it belongs in context.**

---

## 7. Execution Is Sequential and Observable

Plans are executed step-by-step, in order.

For each step:
- `plan.step.start` is logged
- The tool is executed
- `plan.step.end` is logged

This provides:
- A complete execution trace
- Clear failure localization
- The ability to replay or resume runs in the future

---

## 8. Failure Is a First-Class Outcome

The runtime assumes:
- Plans may be invalid
- Tools may fail
- Inputs may be missing

Therefore:
- Plans are validated before execution
- Unknown tools are rejected early
- Errors are surfaced with context-rich logs

A failed run is still a *useful* run if it explains why it failed.

---

## 9. This Design Scales Without Becoming a Framework

Although this resembles agent frameworks, it deliberately avoids:
- Hidden abstractions
- Implicit control flow
- Magical state mutation

Every moving part is visible:
- What the LLM decided
- What tools ran
- What artifacts were produced
- What state changed

This makes the system:
- Easy to reason about
- Easy to extend
- Easy to port to frameworks like ADK later

---

## 10. Mental Model Summary

- **LLM** = planner (decides *what to do*)
- **Tool Registry** = allowed capabilities
- **Runtime** = executor (does the work)
- **Context** = working memory
- **Shared State** = durable contract
- **Logs** = execution truth

If you can explain a run using only these concepts, the system is well-designed.
