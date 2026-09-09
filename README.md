# Skill Audit

Find which AI agent skills need repair, which overlap, and which are worth testing before you keep, simplify, or retire them.

Skill Audit combines an agent-readable workflow with a read-only Python inventory and standalone HTML reports. It is designed for Codex; the filesystem scanner can also inspect Claude Code and other installations that use `SKILL.md` files.

## What it does

| Stage | Work | Result |
| --- | --- | --- |
| Audit | Inventory skill files; inspect headers, local links, exact duplicates, overlapping descriptions, and instruction signals | Evidence with paths and line numbers, plus a short ranked review list |
| Usage review, when authorized | Import verified invocation evidence and account for its coverage | Observed activity, with unknowns and limitations preserved |
| Evaluate | Compare original instructions, a simplified version, and a no-skill baseline in isolated trials | Outcome criteria, artifacts, measured telemetry, and inconclusive results where evidence is insufficient |
| Apply, when requested | Back up originals, make authorized repairs or retirements, update callers, and recheck the library | Reviewable changes and a restoration record |

The scripts collect signals and render evidence. The agent performs contextual review, designs comparisons, and applies authorized changes. There is no automatic delete button, universal quality score, or claim that a newer model makes skills unnecessary.

## Install

Clone this repository into an empty `skill-audit` folder under a skill directory your agent loads. For a default Codex installation:

```bash
git clone https://github.com/cth9191/skill-audit.git ~/.codex/skills/skill-audit
python -m pip install -r ~/.codex/skills/skill-audit/requirements.txt
```

PowerShell:

```powershell
git clone https://github.com/cth9191/skill-audit.git "$env:USERPROFILE/.codex/skills/skill-audit"
python -m pip install -r "$env:USERPROFILE/.codex/skills/skill-audit/requirements.txt"
```

If you use a custom `CODEX_HOME`, install under its `skills` directory. If the destination already exists, preserve it and update deliberately rather than cloning over it. Python 3.10+ is required; the inventory needs PyYAML, while report generation uses only the standard library. A private repository requires GitHub access to clone.

## First time? Start here

After installing the skill, paste this into your agent:

```text
Use $skill-audit for a first-pass audit of my installed skill library.
Scan the available library and inspect the flagged issues in context.
Generate an HTML report that separates verified fixes, retirement decisions
for me to review, skills worth testing next, and lower-priority tests for later.
For each proposed test, explain the question it would answer and suggest a
representative task. Include strengths worth keeping and disclose scan gaps.
Do not change skills, inspect conversation history, or run benchmarks yet.
```

This basic run produces an inventory and an evidence-backed HTML report. It scans the discovered library and reviews relevant flags; it does not execute every skill or prove that every unflagged skill is healthy. Tell the agent if you also want a Claude Code installation or another skill directory included. The report should state what it could and could not inspect.

| Report group | What belongs here | Your next decision |
| --- | --- | --- |
| Fix now | Verified defects such as a missing required helper or malformed metadata | Select the repairs you want applied |
| Review for retirement | Skills with a concrete relevance or duplication concern | Confirm whether you still need the workflow |
| Test next | A consequential uncertainty that representative tasks can resolve | Choose a small batch, normally at most three skills |
| Test later | Lower-priority questions, or tests awaiting a fixture or repaired dependency | Revisit when the stated condition changes |
| Keep / preserve | Useful knowledge, scripts, examples, and constraints found during review | Retain them when simplifying or consolidating |

Empty groups are fine. “Test next” means testing would inform a decision, not that the skill is proven defective. Missing usage evidence, skill age, and file size alone do not establish that a skill should be retired.

Start with the report, then test selectively. Testing 100 skills on two tasks in three conditions requires 600 runs before repeats; a basic audit should not silently launch that work. A skill for an abandoned project may need only your relevance decision, while a frequently used skill with uncertain value may deserve a comparison.

See [examples/audit.json](examples/audit.json) for the synthetic report structure. The Python scripts generate the inventory and HTML; the agent performs the contextual review and chooses recommendations.

## Follow up on the report

Choose names from your report and replace the brackets below. These are separate next steps, not a sequence that must all run.

```text
Use $skill-audit to test only [skill names] from the Test next group.
Use two representative tasks per skill and compare the current procedure,
a simpler version, and a baseline. Start with a small isolated pilot.
Report outcomes and limitations; do not change the installed skills yet.
```

```text
Apply only the verified repairs for [skill names] from the report.
Back up originals, preserve the listed constraints, and verify the changes.
```

```text
Retire only [skill names] from the report; I no longer need those workflows.
Back up the installed copies, update affected callers, and verify the result.
```

For an optional usage review:

```text
Review skill usage over the last 60 days using the local logs I authorize you
to inspect. Separate actual launches from file reads and ordinary mentions.
Explain any retention gaps before recommending retirement.
```

Usage-log collection is agent-assisted work, **not a bundled Codex/Claude transcript parser**. The included importer accepts verified invocation events in the [documented format](references/data-contracts.md). File reads may be maintenance; catalog mentions are not use; missing logs do not establish that a skill was never used.

## Run the scripts directly

Run these commands from the repository root. Choose an output directory outside every scanned skill directory.

```bash
python scripts/inventory.py --root /path/to/skills --out /path/to/local-audit/inventory.json
python scripts/inventory.py --root /path/to/skills --usage /path/to/usage.json --out /path/to/local-audit/with-usage.json
python scripts/report.py audit examples/audit.json --out /path/to/local-audit/audit.html
python scripts/report.py benchmark examples/results.json --out /path/to/local-audit/benchmark.html
```

Repeat `--root` to scan multiple locations. With no roots, the scanner uses `$CODEX_HOME/skills` (or `~/.codex/skills`) and `~/.agents/skills`. Include `~/.claude/skills` explicitly for Claude Code. Use `--catalog catalog.json` for a JSON array of advertised `SKILL.md` paths; `--include-plugins` adds the Codex plugin cache, which can contain inactive versions.

The inventory JSON is scanner output. An audit report JSON adds reviewed findings and recommendations; they are different formats. The benchmark example contains **synthetic demonstration data**, not measured performance results.

## How decisions are made

1. Establish what is actually installed or advertised. Files on disk alone do not establish which version is active.
2. Inspect signals in context. Shared vocabulary may represent useful specialists; a mandatory approval can be appropriate; a long skill can contain valuable domain knowledge.
3. Repair concrete failures first. Follow referenced files to their actual installation, check call arguments, and preserve output and credential locations.
4. Use authorized usage evidence to select review candidates, not to prove obsolescence.
5. Where inspection cannot answer whether instructions help, compare meaningful task outcomes under matched conditions. Keep unknown telemetry unknown and retain failed runs in the record.
6. Apply only the requested decisions, back up before editing, update dependencies, and verify the resulting installation.

See [SKILL.md](SKILL.md), the [evaluation protocol](references/evaluation.md), and [data contracts](references/data-contracts.md).

## Limits and privacy

- The inventory reads skill text. It does not execute target scripts, contact their services, read conversation history by default, or modify installed skills.
- Duplicate hashes and lexical similarity are leads for review, not verdicts. Approval and fixed-step language are inspection signals, not defects by themselves.
- Link detection covers prose Markdown links. Fenced examples are skipped, conventional URL placeholders are labeled unresolved, and arbitrary code paths or indirect dependencies require contextual inspection.
- Symlink/junction directories and common dependency/cache folders are skipped. Supply a resolved target explicitly when needed. Unknown catalog paths and read/parse errors remain visible.
- Fresh agent conversations alone do not prove isolation. If a baseline can load the target skill, report an inconclusive comparison or prepare a test plan for an isolated environment.
- Reports can contain local paths and excerpts. Review them before sharing. Keep raw transcripts, credentials, private outputs, and retirement archives outside this repository.

## Development

```bash
python -m unittest discover -s tests -v
```

Tests cover read-only inventory behavior, path and output guards, malformed metadata, duplicate and usage handling, example-link filtering, HTML escaping, missing metrics, invalid/contaminated runs, and matched comparisons. They do not establish that any particular skill improves task performance.

The CLI workflow test also runs from an unrelated working directory with hostile fixture text, an executable helper, malformed YAML, and incomplete usage evidence. It checks the resulting inventory and verifies that the inputs remain unchanged.

See the [validation record](docs/validation.md) for the scope and limits of the live agent trials.

## License and attribution

Apache License 2.0; see [LICENSE.txt](LICENSE.txt). Evaluation role instructions are adapted from Anthropic’s skill-creator. [ATTRIBUTION.md](ATTRIBUTION.md) records the upstream revision and changes. The inventory and reporting implementation is newly written; it does not depend on the Claude CLI.
