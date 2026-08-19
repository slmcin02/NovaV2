# Security Policy

Nova is built around human control, explicit authorization, and preservation of evidence. Security work around this repository should follow the same principles.

## Scope

This public repository contains Nova's public architecture, roadmap, documentation, and selected non-sensitive materials. Proprietary implementation, credentials, private infrastructure, vendor integrations, and operational secrets are intentionally excluded.

Only test systems, code, accounts, or environments that you own or are explicitly authorized to assess. Do not treat the existence of this repository as authorization to test unrelated infrastructure, third-party services, vendors, users, or accounts.

## Reporting a security issue

Please report suspected security issues privately to **stephen@commandnova.com** with `SECURITY` in the subject line.

A useful report should include:

- the affected file, commit, component, or documented surface;
- a concise description of the issue and likely impact;
- minimal reproduction steps sufficient to validate the issue;
- relevant logs or evidence with credentials, personal data, and secrets removed;
- a proposed mitigation or patch, if available.

Please do not publish exploit details before remediation and coordinated disclosure are complete.

## Research boundaries

The project welcomes good-faith defensive work that helps find, validate, remediate, and prevent vulnerabilities. That includes secure code review, threat modeling, dependency and supply-chain hardening, fuzzing in isolated environments, regression-test development, patch validation, and security documentation.

The project does not authorize:

- access to systems or data without explicit permission;
- credential theft, phishing, social engineering, or persistence;
- destructive testing or denial-of-service activity;
- testing third-party providers or downstream users through Nova;
- collection or publication of secrets or personal data;
- weaponization or public release of exploit details before a fix is available.

For any active testing beyond ordinary use of public materials, obtain written authorization defining the target, scope, time window, and permitted methods first.

## Disclosure principles

The preferred remediation loop is:

1. establish authorization and scope;
2. reproduce the issue in an isolated or controlled environment;
3. validate impact and remove false positives;
4. develop a minimal patch and regression test;
5. verify the remediation;
6. coordinate disclosure after affected users can reasonably update.

The goal is not to maximize the number of findings. The goal is to land verified fixes that reduce real risk.
