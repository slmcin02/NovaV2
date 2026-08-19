# Nova Defensive Security Program

## Purpose

Nova's security program is a public-benefit, defense-first effort to turn AI-assisted security analysis into verified fixes, stronger tests, and reusable defensive workflows.

The program is intentionally measured by **remediation quality**, not raw vulnerability counts.

## Operating principles

1. **Authorization first.** Work only on code and environments owned by the researcher or explicitly authorized by the maintainer/operator.
2. **Human validation before escalation.** AI-generated findings are hypotheses until reproduced and reviewed.
3. **Fixes over findings.** Every confirmed issue should produce a patch, regression test, mitigation, or documented reason why a fix cannot yet land.
4. **No maintainer spam.** Deduplicate and reject weak findings before contacting an upstream project.
5. **Coordinated disclosure.** Respect each project's security policy and disclosure process.
6. **Public benefit.** Publish non-sensitive tooling, testing patterns, lessons, and aggregate metrics when disclosure permits.

## Initial 90-day program

### Phase 1 — establish the testbed and evidence standard

- Publish a responsible disclosure policy and authorization boundaries.
- Threat-model Nova's public and private components.
- Establish an evidence ledger for every candidate finding.
- Baseline dependency, secret, configuration, and secure-code checks.
- Add reproducible test environments for security validation.

### Phase 2 — validate and remediate

For each candidate issue:

- record source and affected commit;
- state the authorization basis;
- reproduce in an isolated environment;
- document expected vs. observed behavior;
- classify confidence and impact conservatively;
- develop a patch and regression test;
- re-run validation after the fix;
- record whether the issue was fixed, rejected, duplicate, or deferred.

### Phase 3 — support open-source maintainers

Once the internal workflow has demonstrated a low false-positive rate, use it only with projects whose maintainers explicitly invite or permit security research.

The contribution target is high-signal upstream work: test coverage, secure defaults, fuzzing harnesses, dependency/supply-chain hardening, variant analysis of already-public vulnerabilities, and patches submitted through the maintainer's established process.

## Evidence ledger

Each entry should contain:

- finding ID;
- repository and commit;
- authorization/scope reference;
- discovery method;
- reproduction environment;
- evidence summary;
- confidence and severity rationale;
- false-positive checks;
- patch reference;
- regression-test reference;
- disclosure/upstream reference when applicable;
- final disposition;
- date closed.

Sensitive exploit mechanics, credentials, private targets, and third-party data must never be placed in the public ledger.

## Success metrics

The program will track:

- confirmed findings / reviewed candidates;
- false-positive rate;
- median time from confirmation to patch;
- percentage of confirmed findings with regression tests;
- patches merged or accepted upstream;
- repeat bug classes eliminated through invariant/property tests;
- maintainer burden avoided through deduplication and pre-validation;
- reusable defensive tooling or documentation released publicly.

## Target outputs

Within 90 days, the program aims to produce:

- a complete threat model for the Nova testbed;
- a reproducible validation and patch-evidence format;
- at least three fully documented internal security remediations or hardening improvements;
- at least one reusable defensive testing workflow released publicly;
- good-faith upstream security or hardening contributions where maintainers explicitly permit them;
- a public retrospective describing methods, false positives, patches, and lessons without exposing unpatched vulnerabilities.

## Long-term direction

The long-term goal is a small, disciplined remediation pipeline that can help under-resourced maintainers turn noisy AI-generated security hypotheses into evidence-backed patches and tests.

Any expansion into penetration testing, exploit validation, or other higher-risk workflows must remain separately authorized, bounded, and subject to the controls required by the model provider and the target owner.
