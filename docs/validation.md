# Validation record

Validation date: September 9, 2026.

## Automated checks

The Python suite contains 21 tests. It covers scanner behavior, filesystem guards, evidence parsing, HTML escaping, benchmark exclusions, matched comparisons, and a CLI workflow from an unrelated directory. The workflow fixture includes hostile instructions and a helper script; neither is executed by the scanner, and file hashes remain unchanged.

The installed skill also passes its own inventory scan: valid metadata and no missing prose Markdown references. Both documented report commands produce standalone HTML from the synthetic examples.

## Forward agent audit

A fresh agent audited six synthetic skills without seeing the grading rubric. The fixture contained malformed YAML, a missing dependency, overlapping descriptions, a rare annual workflow, hostile instructions directed at the auditor, and illustrative Markdown links.

The output met all six predeclared requirements. File/line excerpts were checked against the inputs; all seven input files retained their original hashes. The auditor read the helper as text and did not execute it. This is a single workflow test, not evidence of superiority over a baseline.

## Instruction comparison

A bounded pilot compares the current SKILL.md, a shorter procedure, and no additional skill procedure on two synthetic tasks: defect/overlap review and incomplete usage-evidence review. All arms receive the same raw inputs, precomputed inventory, shared script/schema resources, user requirements, and read-only tools. The comparison isolates procedure text; it does not measure the entire package against an agent lacking the scanner and contracts.

The runtime is the installed desktop CLI 0.153.4, using the configured gpt-6-astra model at high effort. Each run is a fresh ephemeral process. Per-process skill overrides disable every skill returned by the runtime catalog (79 at validation time); plugins, apps, hooks, and configured MCP servers are disabled for the trials. Global settings are unchanged. Host transcripts are inspected for unintended skill reads and other contamination; prompt instructions alone are not treated as isolation evidence. The relevant setting is documented in the [official configuration reference](https://developers.openai.com/codex/config-reference/).

Objective grading criteria and input hashes are frozen before execution. Wall time and tokens come from the host. One repetition per task is a pilot: small differences cannot establish a durable performance advantage or justify retirement. Raw local transcripts and machine-specific paths are not published in this repository.

All six trials completed. An independent reviewer checked outputs and actual command logs against the frozen criteria: **45 passes, zero failures, zero unknowns**. All 71 finding citations matched actual file paths, one-based lines, and excerpts. No unintended skill reads, target execution, external requests, or input changes were observed.

| Task | Current procedure | Shorter procedure | Baseline |
| --- | --- | --- | --- |
| Defects, overlap and hostile instructions | 8/8 | 8/8 | 8/8 |
| Incomplete usage evidence and preservation constraints | 7/7 | 7/7 | 7/7 |

| Task / procedure | Process wall seconds | Input + output tokens, including cached input |
| --- | ---: | ---: |
| Defects / current | 168.931 | 93,349 |
| Defects / shorter | 160.760 | 51,948 |
| Defects / baseline | 148.491 | 69,514 |
| Usage / current | 104.745 | 52,190 |
| Usage / shorter | 110.486 | 48,623 |
| Usage / baseline | 131.099 | 58,133 |

Timing includes CLI startup/shutdown and some runs overlapped. Cached tokens are included in totals; these figures are not billing estimates. Objective grading was independent but the reviewer could see arm labels. No subjective preference was scored.

Two outputs (current and shorter procedures on the defect task) represented `coverage` as an object instead of the string shown in the audit contract. The renderer accepts these values but displays their string representation. This formatting deviation is recorded separately; it was not retroactively added to the frozen quality rubric.

**Decision:** keep the current skill. These small tasks validate the tested audit behavior and show no objective quality winner. They do not establish general equivalence, demonstrate an advantage for the current procedure, or justify retirement. The scanner and report tools were available to every arm, so this does not test whether the whole package adds value over an agent without those tools. The comparison snapshots remain unchanged; no shorter procedure was installed.

## Setup failures retained

An initial preflight failed because the test harness quoted a dotted MCP override incorrectly. The corrected attempt then reached the service but the older standalone CLI 0.144.5 was rejected for the selected Astra model. Neither produced a task result. Validation continued with the already-installed newer desktop runtime; no global CLI upgrade, model substitution, or user-setting change was made. Both failures remain in the local execution record and are excluded from task-quality comparisons.
