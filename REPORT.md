# Design Report

## Architecture

The system is a three-phase pipeline: **discover → record → replay**.

In the discovery phase, an agent loop drives a real browser (Playwright) against the target application. Each step follows an observe → decide → act cycle. In production this decision is made by an LLM (Claude); in this submission it uses a scripted mock that drives the real browser with real Playwright interactions. The LLM boundary is a clean seam — swapping in the live agent requires only replacing the mock script lookup with an Anthropic API call, as shown in agent/agent_loop.py.

After a successful run, the agent emits a typed, versioned Capability artifact. The replay engine then executes that artifact deterministically — no LLM in the loop — using stable element targeting and explicit error handling.

Key decisions:
- **Playwright over screenshot-based control**: accessibility tree + DOM gives more stable targeting for web surfaces. Screenshot + coordinate approach is documented as the fallback for desktop/legacy surfaces.
- **Flask mock app styled as legacy UI**: no test IDs, table-based layout, server-rendered — intentionally hostile to automation, matching the real environment described in the brief.
- **Single process architecture**: simpler, easier to run, easier to debug. A queue-based worker model is the obvious next step for production scale.

## Artifact Schema

The Capability schema (artifact/schema.py) is the core contract. Key design decisions:

- **Typed inputs and outputs**: every capability declares what it needs (InputParam) and what it returns (OutputField). This makes it callable by an AI agent like a typed function.
- **Locator with fallbacks**: each step stores a primary locator strategy plus a fallback list. This handles the reality that legacy apps have no stable test IDs — we chain from most-specific to most-robust (CSS → name → text → label).
- **Versioned**: artifacts carry a version string. Drift detection compares the current app state against the recorded checkpoint; a mismatch bumps the artifact to draft status.
- **Tenant ID**: every artifact is scoped to a tenant, enabling per-tenant overrides while sharing a base recording.
- **Status lifecycle**: DRAFT → APPROVED → DEPRECATED. Unattended replay is gated on APPROVED status.

The checkpoint field on each step is the key correctness mechanism: after every action, replay asserts that the expected text appears on the page before proceeding. This is how we distinguish "the click worked" from "the click appeared to work."

## Determinism and Error Handling

Replay is deterministic because it follows the recorded step sequence exactly, using the same locator strategies, with no model making decisions. Randomness is eliminated by: fixed step order, stable locators, explicit waits, and checkpoint assertions.

Runtime errors are classified into three categories (replay/error_handler.py):

- **Business outcomes**: "member not found", "account is locked", "permission denied" — these are legitimate results the caller needs, not failures. They are returned as structured outcomes, not exceptions.
- **Recoverable conditions**: timeouts, slow loads, session expiry — the replay waits and retries before escalating.
- **Hard failures**: unexpected page state, missing element after fallbacks exhausted — replay stops, takes a screenshot, and returns a structured error with step ID, expected state, and observed state.

This three-way taxonomy is the most important design decision in the replay engine. Conflating business outcomes with failures is the most common mistake in automation systems.

## Heterogeneity and Multi-Tenant

**Surface abstraction**: the seam between "how we perceive and act on a surface" and "the recorded flow" is the Locator model. Web (DOM/accessibility tree via Playwright), legacy web (same, with more aggressive fallback chains and iframe handling), and desktop (accessibility tree via pywinauto or similar, same Locator schema) all map to the same artifact format. The replay engine dispatches to a surface-specific driver based on a surface_type field on the Capability. Only the web driver is implemented; desktop is designed but stubbed.

**Multi-tenant reuse**: artifacts carry a tenant_id and a base_capability_id. A base recording for vendor product V is stored once. Per-tenant overrides (different URLs, different field names, different confirmation dialogs) are stored as a delta — a list of step-level overrides keyed by step_id. Replay merges base + delta before executing. Drift is detected by comparing checkpoint text against the live page; a mismatch flags the artifact for re-recording. This avoids rebuilding from scratch for each of hundreds of tenants running the same vendor product.

## Escalation and Handoff

Escalation triggers on three conditions: the agent explicitly signals it cannot proceed, the replay hits a hard failure, or the stuck detector fires (same action or same URL repeated N times in a row).

When escalation triggers, the system: pauses the browser session (does not close it), serializes the intervention request to evidence/escalations/ with full context (goal, step, reason, URL, screenshot), and returns control. The operator console (escalation/operator_console.py) lists pending interventions, shows context, and lets a human operator mark the intervention resolved with a note describing what they did manually.

The control-transfer model: automation holds the Playwright browser instance. On escalation, the instance is paused (navigation stopped, no further actions). In a production system, the session would be exposed via a remote debugging port (Chrome DevTools Protocol) or a WebRTC stream, letting the operator take over the exact live session. The operator signals done via the console; the automation resumes from the next step. Human actions during the handoff are logged to the intervention record for audit.

The current implementation mocks the operator UI but the handoff mechanism — pause, serialize context, expose session ID, resume — is real and well-defined.

## Safety

**Allowlist**: every action is checked against config/policy.yaml before execution. Permitted domains, routes, and action types are explicit. Anything outside the allowlist is blocked before Playwright executes it.

**Risky action classification**: form submissions on sensitive routes (account creation, transfers) are flagged as risky. The current policy requires a confirmation step in the UI before proceeding. In production, irreversible actions (wire transfers, account closure) would require an out-of-band approval signal from a human operator before replay proceeds.

**PII redaction**: all logs pass through guardrails/redactor.py before being written. Passwords are redacted at log time (never written). SSNs, card numbers, and tokens are pattern-matched and replaced. Artifacts never store raw credentials — the login step records the locator and param_ref, not the value.

**Limits**: the allowlist is file-based and reloaded per run — not cryptographically enforced. A production system would sign the policy and verify it at runtime. The redactor uses regex patterns, which can be evaded by unusual formatting.

## Cuts

**What was cut and why**:
- Live LLM integration: requires API credits. The mock drives the real browser with real Playwright — all non-LLM components are fully real. Swapping in the live agent is a one-function change.
- Real-time operator console: a WebRTC or CDP-based co-browsing UI is out of scope. The handoff model and data contract are real; the UI is a CLI stub.
- Desktop surface driver: designed, not implemented. The Locator schema supports it; a pywinauto or UIA-based driver would plug in at the executor level.
- Multi-tenant delta storage: the schema supports tenant_id and the design is described above, but the merge logic is not implemented.
- Artifact approval gating: status lifecycle is in the schema; the gate (block unattended replay of DRAFT artifacts) is not enforced in the executor.

**What I would build next**:
1. Live LLM integration with the Anthropic API
2. CDP-based session sharing for the operator handoff
3. Per-tenant override delta and drift detection
4. Artifact approval workflow with confidence scoring
5. Multi-run stability signal (replay N times, report flakiness rate)
