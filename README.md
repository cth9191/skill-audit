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

## Use with an agent

```text
Use $skill-audit to review my installed skills. Prioritize broken references,
conflicting instructions, and overlapping triggers. Give me the top three
candidates with evidence. Do not change anything yet.
```

```text
Review skill usage over the last 60 days using the local logs I authorize you
to inspect. Separate actual launches from file reads and ordinary mentions.
Explain any retention gaps before recommending retirement.
```

```text
Fix the verified issues in these named skills. Back up originals, update their
callers, and verify the resulting files. Preserve my existing workflows.
```

```text
Evaluate this skill against a simplified version and a no-skill baseline on
two supplied tasks. Use isolated runs and report inconclusive comparisons honestly.
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
