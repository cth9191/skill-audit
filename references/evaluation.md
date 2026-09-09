# Evaluate selected skills

Adapted from Anthropic skill-creator; see ../ATTRIBUTION.md. Use this only for requested behavioral evaluation, not every library scan.

## Prepare a fair comparison

1. Choose a concrete skill and 2–3 representative tasks with supplied or local non-sensitive fixtures. Include a boundary case when it matters. Define required outcomes and subjective criteria before inspecting trial outputs. No test should reward an arbitrary step just because the old skill mandates it.
2. Snapshot the original skill and its relevant resources in the evaluation workspace. Prepare a simplified copy, preserving business requirements, data, examples, safety boundaries and operational invariants. Record hashes and changed instructions. Never edit installed originals to set up a trial.
3. Define three arms: `original`, `simplified`, `baseline`. Give every arm the same user request, input facts, tool capabilities, resources and non-procedural requirements. Baseline omits target procedural instructions. If resources cannot be separated fairly, document a whole-package comparison instead and do not claim to have isolated instruction quality.
4. Record exact model, reasoning effort, tool environment, inputs and resource hashes. Use the user's selected model (Astra if explicitly requested). Never silently substitute another model. Run conditions must match; otherwise label the comparison invalid or exploratory.
5. Keep execution in isolated output folders. Replace external mutations with fixtures or drafts where those still test the capability. Do not run production actions merely to benchmark a skill. Where the test itself needs new permissions or substantial spend, prepare the concrete test plan first and ask only for the missing authorization.

## Execute in Codex

When collaboration tools are available, delegate independent trials to fresh-context agents (`fork_turns="none"` when supported), respecting available concurrency. This skill authorizes bounded parallel trial and review work within the requested evaluation. Do not create user-owned tasks for internal trials. Continue preparing fixtures or reporting while agents work. Set an explicitly requested model override when supported; never invent a model identifier or assume a child inherited settings without evidence.

Give each executor only the task, arm-specific instructions, minimum inputs, common requirements, and its output directory. Do not give it suspected defects, the expected winner, other outputs or comparison history. Ask it to save final artifacts and a record of actual tools/resources used, completion state and uncertainties. Preserve actual host transcripts if available; an executor's self-report alone is weaker evidence.

Fresh conversational context does not guarantee isolation from installed skills, inherited instructions or memories. Inspect the executor's available catalog and actual skill reads. A baseline that loads the target or an equivalent helper is contaminated. If this cannot be prevented with supported runtime configuration, report **inconclusive**; a “do not use this skill” prompt alone is not proof of isolation. Do not change the user's global settings to force isolation. Use a separate configured environment if already available; otherwise stop at the plan and disclose the limitation.

If independent agents are unavailable, use a supported clean-session runner with equivalent controls. Do not substitute sequential trials in one shared conversation and label them independent. There is intentionally no bundled `claude -p` launcher or unverified Codex CLI wrapper.

Use an initial pilot to catch fixture and execution failures. For a decision to retire a skill, test multiple representative cases and repeat runs where results are close or variable. A pilot is an initial signal. Do not expand endlessly after a clear bounded result; report the coverage.

For each run write the format in [data-contracts.md](data-contracts.md). Mark missing telemetry `null`; do not estimate tokens from characters or treat missing metrics as zero. Record wall-clock run time separately from evaluator time. Record interrupted, failed, skipped and contaminated trials; never silently drop them.

## Judge outcomes

Use [grader.md](grader.md) to evaluate objective criteria from actual artifacts. Use deterministic checks when useful, especially file validity, calculations and data fidelity. Preserve the criteria and unknown results across all arms.

For subjective criteria, label outputs A/B (or A/B/C), strip arm-revealing path names and metadata, and use [comparator.md](comparator.md). Keep the private mapping outside the judge's context. Randomize presentation order. Freeze the rubric first; a judge should not invent success criteria after seeing which output is most polished. Human preference is authoritative for personal taste. A model judge supplies evidence and a provisional opinion, not an objective verdict about style.

Use [analyzer.md](analyzer.md) after grading to connect observed failures to specific instructions. Distinguish correlation from demonstrated cause. An assertion passing in every arm may be a useful minimum requirement but does not establish skill value.

## Report

```text
python <skill-dir>/scripts/report.py benchmark <evaluation-dir>/results.json --out <evaluation-dir>/benchmark.html
```

This produces the HTML review plus a JSON summary beside it. Inspect individual outputs as well as metrics. Keep failed runs visible and exclude only explicitly invalid/contaminated comparisons from valid-run aggregates. State exclusions and missing telemetry. Aggregate comparisons use only matched case/repeat pairs with matching model, effort, environment and inputs.

Recommend keeping, simplifying, investigating further or considering retirement. Support each recommendation with the tested task coverage, artifacts and meaningful differences. Low usage alone does not justify retirement. Preserve the originals; apply recommendations only if requested.
