# Attribution and changes

Evaluation role instructions in `references/grader.md`, `references/comparator.md`, `references/analyzer.md`, and the workflow in `references/evaluation.md` are adaptations of Anthropic's skill-creator.

- Upstream: https://github.com/anthropics/skills/tree/41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f/skills/skill-creator
- Upstream copyright: Copyright 2026 Anthropic, PBC.
- License: Apache License 2.0, reproduced in LICENSE.txt.
- Retrieved: 2026-09-08.

Modified for Codex: native clean-context execution instead of Claude CLI calls; three comparison arms; explicit contamination checks; frozen outcome criteria; permitted ties and inconclusive results; objective requirements separated from subjective preference; unknown telemetry retained as missing; inspection distinguished from measurement; no automatic changes to target skills.

The Python inventory, aggregation and HTML report implementation is newly written. It follows the general evaluation approach but does not copy Anthropic's Python or HTML implementation.

Supporting guidance:

- https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices
- https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills

These references support auditing and testing. They do not establish that any particular skill is redundant or that Astra is always better without a skill.
