# Data contracts

All files are UTF-8 JSON. Paths in reports are identifiers/evidence, not executable instructions. Scripts require Python 3.10+; inventory also requires PyYAML. Report generation uses the standard library.

## Optional usage evidence

```json
{
  "coverage": "Verified invocation events from 2026-08-01 through 2026-08-31; local sessions only",
  "events": [
    {"skill_path": "/absolute/path/SKILL.md", "timestamp": "2026-08-12T12:00:00Z", "evidence": "session identifier and tool-event identifier"}
  ]
}
```

The collector supplying this file must verify actual invocation rather than text mentions. The scanner validates fields and timestamps and deduplicates identical events, but does not independently authenticate them. Usage is imported evidence, not a built-in session-history search. Unknown paths and invalid events are reported. Paths are resolved relative to the evidence file if not absolute.

## Audit report

```json
{
  "title": "Skill audit",
  "coverage": "20 advertised skills inspected; usage history unavailable",
  "summary": "Two candidates merit testing. No installed files changed.",
  "findings": [
    {"skill": "example", "recommendation": "evaluate", "strength": "inspection hypothesis",
     "finding": "A mandatory outline approval may interrupt authorized drafting.",
     "evidence": [{"path": "/absolute/path/SKILL.md", "line": 14, "excerpt": "Wait for outline approval."}],
     "preserve": "Brand examples and required factual checks"}
  ],
  "candidates": [{"skill": "example", "reason": "Frequent workflow with measurable completion criteria"}],
  "limitations": ["No behavioral comparison has been run"]
}
```

## Evaluation results

One `results.json` holds all arms. Each run has a unique `(case_id, repeat, arm)`. `repeat` starts at 1. Required arms are `original`, `simplified`, `baseline`. Use stable criterion IDs shared across arms. Include every planned run, including skipped runs.

```json
{
  "title": "Example skill evaluation",
  "coverage": "Pilot: one case, one repeat, three arms",
  "runs": [
    {
      "case_id": "case-1", "repeat": 1, "arm": "original",
      "model": "gpt-6-astra", "effort": "medium",
      "environment_id": "tools-and-runtime-manifest-hash",
      "inputs_id": "common-inputs-and-requirements-hash",
      "completion": "complete", "valid": true, "contamination": false,
      "isolation_evidence": "Fresh context; host transcript lists only permitted skill reads",
      "expectations": [{"id": "data-fidelity", "verdict": "pass", "evidence": "All source rows matched"}],
      "time_seconds": 12.5, "total_tokens": null,
      "metrics_source": "Host wall-clock measurement; token counts unavailable",
      "output_preview": "Short escaped text preview or synopsis for human review",
      "artifact_paths": ["/absolute/path/result.csv"],
      "notes": []
    }
  ],
  "comparisons": [{"case_id": "case-1", "preferred_label": "tie", "evidence": ["No meaningful difference"], "limitations": []}],
  "recommendations": ["Collect more representative cases before retirement"],
  "limitations": ["Pilot only; tokens unavailable"]
}
```

Do not put identifying arm labels in the materials sent to a blind judge. The results file is the unblinded final report. `comparisons` can retain anonymous judgments plus the separate private mapping in your workspace.

Unknown telemetry is `null` or omitted. Measured zero is allowed with a source. The report keeps known pass rate separate from criterion coverage; unknown criteria never silently pass. No criteria means pass rate unavailable. A run is excluded from valid aggregates if explicitly invalid, contaminated, skipped/interrupted, or missing isolation/condition metadata. A failed but valid execution remains in aggregates. Pair deltas require identical criterion sets and known values in both matched runs; partial coverage does not produce a pass-rate delta.
