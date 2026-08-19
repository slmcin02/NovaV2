# Open Patch Relay

**One-sentence summary:** Build and evaluate a human-validated AI workflow that helps small open-source maintainers turn noisy security findings into reproducible evidence, regression tests, and review-ready patches without increasing maintainer burden.

## Problem

AI can produce more candidate security findings than maintainers can responsibly review. The bottleneck is increasingly validation and remediation: reproducing a candidate, rejecting false positives and duplicates, understanding impact, writing a minimal patch, adding a regression test, and coordinating disclosure. Small open-source projects are especially vulnerable to report overload. A system that merely generates more findings can make this problem worse. Open Patch Relay focuses on the opposite objective: reduce the cost of moving a *small number of high-confidence candidates* through a documented, human-controlled remediation loop.

## Proposal

Open Patch Relay is a 12-week defensive security pilot that will develop and measure a reusable workflow for AI-assisted vulnerability triage and patch verification. The pilot will begin on code and environments owned by the project maintainer. Work involving another project will occur only after confirming that project's security policy and obtaining any authorization required by its maintainers.

The workflow will treat every model-produced finding as an untrusted hypothesis. A candidate will not be escalated to a maintainer until it has passed explicit checks for scope, duplication, reproducibility, impact, and remediation quality.

### Workflow

1. **Scope and threat model**
   - Define assets, trust boundaries, attack surfaces, expected invariants, and out-of-scope behavior.
   - Record the authorization basis for every target.

2. **Candidate generation**
   - Use frontier models and conventional defensive tooling for secure code review, dependency and configuration analysis, specification/invariant testing, and analysis of already-public vulnerability classes.
   - Do not conduct unauthorized testing, credential attacks, destructive testing, or public exploit release.

3. **Human validation**
   - Reproduce candidates in an isolated environment.
   - Check version/commit applicability, expected behavior, duplicate status, preconditions, and realistic impact.
   - Reject weak or non-reproducible candidates before any upstream contact.

4. **Patch and test**
   - Develop a minimal remediation.
   - Add a regression test or invariant/property test where feasible.
   - Verify that the fix closes the issue without creating regressions.

5. **Maintainer handoff and disclosure**
   - Follow the target project's established private security process.
   - Provide concise evidence, patch/test references, and severity rationale.
   - Preserve maintainer control over disclosure and release timing.

6. **Measurement and public learning**
   - Publish non-sensitive aggregate metrics, reusable test harness patterns, evidence schemas, and lessons after disclosure permits.

## Research questions

The pilot will evaluate:

- What percentage of AI-generated security candidates survive human reproduction and false-positive review?
- Which evidence fields most reduce maintainer review time?
- How often can a confirmed finding be paired with a regression test and patch in the same workflow?
- Can specification-based, invariant, property, and variant testing produce higher-signal candidates than unconstrained vulnerability prompting?
- Which failure modes cause AI-assisted security workflows to create the most maintainer noise?

## New data / dataset

The project will produce a small sanitized evaluation dataset describing the lifecycle of security candidates without publishing unpatched exploit mechanics or sensitive target information. Fields will include candidate category, validation disposition, false-positive reason, patch/test status, time-to-resolution, and final disposition.

Where disclosure restrictions apply, records will be aggregated or delayed until a maintainer approves publication.

## Models and resources requested

Requested support:

- **$10,000 in OpenAI API credits or equivalent defensive-security resources** for the 12-week pilot;
- continued Trusted Access for authorized defensive workflows;
- access to Codex Security where OpenAI determines the project is eligible;
- guidance on approved model/product surfaces for the validation and patch-development workflow;
- consideration for relevant Daybreak / open-source maintainer programs if the pilot demonstrates useful results.

The project does not request unrestricted access or authorization to test third-party systems.

## Public benefit and licensing

The project will publish, under a permissive open-source license where original code is produced:

- the candidate-evidence schema;
- defensive triage and patch-validation workflow documentation;
- non-sensitive test harness templates;
- false-positive and deduplication lessons;
- aggregate evaluation results;
- selected patched case studies after coordinated disclosure.

The goal is to help maintainers absorb AI-assisted security work without receiving a flood of low-quality reports.

## Timeline

### Weeks 1–2: foundation
- finalize security policy and scope template;
- create threat model and evidence ledger;
- establish isolated validation environment;
- baseline defensive tooling and model workflow.

### Weeks 3–5: controlled internal evaluation
- generate and review candidate findings on owned code;
- measure false-positive causes;
- require patch + regression-test evidence for confirmed issues;
- refine the evidence schema.

### Weeks 6–8: workflow hardening
- add specification/invariant/property testing;
- add deduplication and historical-public-vulnerability variant checks;
- publish initial non-sensitive tooling and methodology.

### Weeks 9–11: authorized open-source collaboration
- approach maintainers only through established channels and only where research/contribution is permitted;
- submit high-confidence hardening patches, tests, or privately disclosed findings when appropriate;
- measure maintainer review burden and outcomes.

### Week 12: report
- publish a sanitized final report;
- release reusable workflow assets;
- document confirmed findings, rejected candidates, patch outcomes, and lessons;
- propose the next phase based on measured results.

## Success criteria

A successful pilot will demonstrate:

- a documented and reproducible human-validation workflow;
- measurable false-positive filtering before maintainer contact;
- at least three completed internal security remediation/hardening cases with tests;
- at least one reusable defensive testing workflow released publicly;
- upstream contributions where maintainers explicitly permit them;
- a final public report that helps other maintainers adopt safer AI-assisted security practices.

Success is not defined by producing a large number of vulnerabilities. It is defined by verified remediation, low-noise maintainer handoff, and reusable defensive capacity.

## Applicant fit

Stephen McIntosh is a solo technical founder building Nova, a human-controlled persistent AI system. Nova's private implementation provides an owned, bounded environment for defensive validation, while this public repository provides a transparent home for non-sensitive methods and results. The project is deliberately structured to begin with owned code, build evidence before external work, and preserve explicit authorization and maintainer control throughout.
