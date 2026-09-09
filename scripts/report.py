#!/usr/bin/env python3
"""Standalone, escaped audit/benchmark reports. No network or model calls."""
import argparse
from collections import defaultdict
import html
import json
import math
from pathlib import Path
import statistics

ARMS = ("original", "simplified", "baseline")


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def stats(values):
    clean = [v for v in values if number(v)]
    return {"n": len(clean), "mean": statistics.mean(clean) if clean else None,
            "stddev": statistics.stdev(clean) if len(clean) > 1 else None,
            "min": min(clean) if clean else None, "max": max(clean) if clean else None}


def signed_stats(values):
    clean = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)]
    return {"n": len(clean), "mean": statistics.mean(clean) if clean else None,
            "stddev": statistics.stdev(clean) if len(clean) > 1 else None}


def summarize(data):
    runs = data.get("runs")
    if not isinstance(runs, list):
        raise ValueError("results must contain a runs array")
    seen, normalized, warnings = set(), [], []
    for raw in runs:
        if not isinstance(raw, dict):
            raise ValueError("each run must be an object")
        run = dict(raw)
        if not isinstance(run.get("case_id"), str) or not run["case_id"] or type(run.get("repeat")) is not int or run["repeat"] < 1 or run.get("arm") not in ARMS:
            raise ValueError("run needs case_id, positive integer repeat, and original/simplified/baseline arm")
        key = (run["case_id"], run["repeat"], run["arm"])
        if key in seen:
            raise ValueError(f"duplicate run identity: {key}")
        seen.add(key)
        expectations = run.get("expectations", [])
        if not isinstance(expectations, list):
            raise ValueError("expectations must be an array")
        ids = set()
        for expectation in expectations:
            if not isinstance(expectation, dict) or not isinstance(expectation.get("id"), str) or not expectation["id"] or expectation["id"] in ids or expectation.get("verdict") not in ("pass", "fail", "unknown") or not isinstance(expectation.get("evidence"), str) or not expectation["evidence"].strip():
                raise ValueError(f"invalid or duplicate criterion in {key}")
            ids.add(expectation["id"])
        passed = sum(e["verdict"] == "pass" for e in expectations)
        known = sum(e["verdict"] != "unknown" for e in expectations)
        run["pass_rate"] = passed / known if known else None
        run["criterion_coverage"] = known / len(expectations) if expectations else None
        run["unknown_criteria"] = len(expectations) - known
        excluded = []
        if run.get("valid") is not True:
            excluded.append("not established as valid")
        if run.get("contamination") is not False:
            excluded.append("contamination present or not checked")
        if run.get("completion") not in ("complete", "partial", "failed", "skipped", "interrupted"):
            raise ValueError(f"invalid completion state in {key}")
        if run["completion"] in ("skipped", "interrupted"):
            excluded.append(run["completion"])
        for field in ("model", "effort", "environment_id", "inputs_id", "isolation_evidence"):
            if not isinstance(run.get(field), str) or not run[field].strip():
                excluded.append(f"missing {field}")
        for metric in ("time_seconds", "total_tokens"):
            value = run.get(metric)
            if value is not None and not number(value):
                raise ValueError(f"invalid {metric} in {key}")
            if value is not None and (not isinstance(run.get("metrics_source"), str) or not run["metrics_source"].strip()):
                warnings.append(f"{key}: {metric} ignored because metrics_source is missing")
                value = None
            run[metric] = value
        run["exclusions"] = excluded
        run["included"] = not excluded
        normalized.append(run)
    aggregates = {}
    for arm in ARMS:
        all_runs = [r for r in normalized if r["arm"] == arm]
        valid = [r for r in all_runs if r["included"]]
        aggregates[arm] = {"runs": len(all_runs), "valid_runs": len(valid), "excluded_runs": len(all_runs) - len(valid),
                           "completion_states": {s: sum(r["completion"] == s for r in valid) for s in ("complete", "partial", "failed")},
                           **{m: stats([r[m] for r in valid]) for m in ("pass_rate", "criterion_coverage", "time_seconds", "total_tokens")}}
    indexed = {(r["case_id"], r["repeat"], r["arm"]): r for r in normalized}
    deltas = {}
    for arm in ("original", "simplified"):
        values = defaultdict(list)
        pairs = 0
        for trial in [r for r in normalized if r["arm"] == arm and r["included"]]:
            base = indexed.get((trial["case_id"], trial["repeat"], "baseline"))
            if not base or not base["included"]:
                continue
            if any(trial[k] != base[k] for k in ("model", "effort", "environment_id", "inputs_id")):
                warnings.append(f"{trial['case_id']} repeat {trial['repeat']} {arm}: condition mismatch; no paired delta")
                continue
            if {e["id"] for e in trial.get("expectations", [])} != {e["id"] for e in base.get("expectations", [])}:
                warnings.append(f"{trial['case_id']} repeat {trial['repeat']} {arm}: criteria differ; no paired delta")
                continue
            pairs += 1
            for metric in ("pass_rate", "time_seconds", "total_tokens"):
                if metric == "pass_rate" and (trial["criterion_coverage"] != 1 or base["criterion_coverage"] != 1):
                    continue
                if trial[metric] is not None and base[metric] is not None:
                    values[metric].append(trial[metric] - base[metric])
        deltas[f"{arm}_minus_baseline"] = {"matched_pairs": pairs, **{m: signed_stats(values[m]) for m in ("pass_rate", "time_seconds", "total_tokens")}}
    missing = []
    for case_id, repeat in sorted({(r["case_id"], r["repeat"]) for r in normalized}):
        for arm in ARMS:
            if (case_id, repeat, arm) not in indexed:
                missing.append({"case_id": case_id, "repeat": repeat, "arm": arm})
    if missing:
        warnings.append("Some cases lack comparison arms. Per-condition summaries include different case sets and must not be interpreted as skill uplift.")
    for name, delta in deltas.items():
        if delta["matched_pairs"] == 0:
            warnings.append(f"{name}: no valid matched pairs; no comparative conclusion is available.")
    return {"arms": aggregates, "paired_deltas": deltas, "runs": normalized, "missing_runs": missing, "warnings": warnings,
            "note": "Descriptive results, not significance tests. Known-criterion pass rates must be read with criterion coverage. No automatic retirement verdict."}


def esc(value):
    return html.escape(str(value), quote=True)


def listing(values):
    return "<ul>" + "".join("<li>" + esc(v) + "</li>" for v in values) + "</ul>"


def detail(value):
    return "<pre>" + esc(json.dumps(value, ensure_ascii=False, indent=2)) + "</pre>"


def fmt(value, percent=False):
    if value is None:
        return "Unavailable"
    return f"{value * 100:.1f}%" if percent else f"{value:,.2f}"


def shell(title, body):
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>""" + esc(title) + """</title><style>
:root{color-scheme:light dark}body{font:16px/1.6 system-ui,sans-serif;max-width:1100px;margin:36px auto;padding:0 24px;background:#101619;color:#e3ecee}h1{font-size:34px;line-height:1.2}h2{margin-top:34px}h3{margin:0 0 12px}p{max-width:90ch}.eyebrow{color:#88d6c2;font-size:12px;letter-spacing:2px;text-transform:uppercase}section,details{border:1px solid #35464c;border-radius:10px;padding:20px;margin:16px 0}summary{cursor:pointer;font-weight:600}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #35464c}th{color:#88d6c2}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 ui-monospace,monospace}small,.muted{color:#b1c0c5}code{overflow-wrap:anywhere}li{margin:7px 0}button{font:inherit} @media print{body{background:white;color:black}section,details{break-inside:avoid}th{color:black}}
</style></head><body><div class="eyebrow">Skill Audit · local review</div><h1>""" + esc(title) + "</h1>" + body + "<p class='muted'>Generated locally. Embedded text is escaped; no scripts, remote assets, or tracking.</p></body></html>"


def action_plan_html(plan):
    groups = (("fix_now", "Fix now"), ("review_retirement", "Review for retirement"),
              ("test_next", "Test next"), ("test_later", "Test later"), ("keep", "Keep / preserve"))
    if not isinstance(plan, dict) or set(plan) - {key for key, _ in groups}:
        raise ValueError("action_plan must be an object with recognized group keys")
    body = "<h2>What to do next</h2><p class='muted'>Recommendations for your next decision. See the findings for evidence and coverage limits.</p>"
    for key, label in groups:
        entries = plan.get(key, [])
        if not isinstance(entries, list):
            raise ValueError(f"action_plan.{key} must be an array")
        body += "<section><h3>" + label + "</h3>"
        if not entries:
            body += "<p class='muted'>No recommendations in this group.</p>"
        for entry in entries:
            if not isinstance(entry, dict) or any(not isinstance(entry.get(field), str) or not entry[field].strip() for field in ("skill", "reason")):
                raise ValueError("action_plan entries need nonempty skill and reason strings")
            body += "<p><strong>" + esc(entry["skill"]) + "</strong> — " + esc(entry["reason"]) + "</p>"
            for field, title in (("task", "Representative task"), ("success_criteria", "Success criteria"), ("prerequisite", "Revisit when")):
                if field in entry:
                    if not isinstance(entry[field], str):
                        raise ValueError(f"action_plan entry {field} must be a string")
                    body += "<p><strong>" + title + ":</strong> " + esc(entry[field]) + "</p>"
        body += "</section>"
    return body


def audit_html(data):
    body = "<p>" + esc(data.get("summary", "")) + "</p><p class='muted'>Coverage: " + esc(data.get("coverage", "Not specified")) + "</p>"
    if "action_plan" in data:
        body += action_plan_html(data["action_plan"])
    body += "<h2>Findings</h2>"
    for finding in data.get("findings", []):
        body += "<section><h3>" + esc(finding.get("skill", "Unnamed skill")) + "</h3><p><strong>" + esc(finding.get("recommendation", "insufficient evidence")) + "</strong> · " + esc(finding.get("strength", "not specified")) + "</p><p>" + esc(finding.get("finding", "")) + "</p>"
        for evidence in finding.get("evidence", []):
            body += "<p><code>" + esc(evidence.get("path", "")) + ":" + esc(evidence.get("line", "?")) + "</code></p><pre>" + esc(evidence.get("excerpt", "")) + "</pre>"
        body += "<p><strong>Preserve:</strong> " + esc(finding.get("preserve", "Not specified")) + "</p></section>"
    if "action_plan" not in data:
        body += "<h2>Evaluation candidates</h2>" + listing(str(c.get("skill", "")) + ": " + str(c.get("reason", "")) for c in data.get("candidates", []))
    body += "<h2>Limitations</h2>" + listing(data.get("limitations", []))
    return shell(data.get("title", "Skill audit"), body)


def benchmark_html(data, summary):
    body = "<p>" + esc(data.get("coverage", "Coverage not specified")) + "</p><p>" + esc(summary["note"]) + "</p>"
    body += "<h2>Matched differences from baseline</h2><p class='muted'>Only matching case/repeat, model, effort, environment, inputs and criteria contribute. Positive time/token differences mean more consumption. These differences do not by themselves establish better quality.</p><div class='scroll'><table><tr><th>Comparison</th><th>Matched pairs</th><th>Pass-rate difference</th><th>Time difference (seconds)</th><th>Token difference</th></tr>"
    for name, delta in summary["paired_deltas"].items():
        body += "<tr><td>" + esc(name.replace('_', ' ')) + "</td><td>" + str(delta["matched_pairs"]) + "</td>"
        for metric in ("pass_rate", "time_seconds", "total_tokens"):
            stat = delta[metric]
            display = "Unavailable" if stat["mean"] is None else (f"{stat['mean'] * 100:+.1f} percentage points" if metric == "pass_rate" else f"{stat['mean']:+,.2f}")
            body += "<td>" + display + "<br><small>n=" + str(stat["n"]) + "</small></td>"
        body += "</tr>"
    body += "</table></div>"
    if summary["warnings"]:
        body += "<section><strong>Comparison limits</strong>" + listing(summary["warnings"]) + "</section>"
    body += "<h2>Per-condition summaries (unpaired)</h2><p class='muted'>Descriptive totals for each condition. These may cover different tasks and must not be used to estimate improvement; use the matched differences above.</p><div class='scroll'><table><tr><th>Condition</th><th>Valid / recorded runs</th><th>Known pass rate</th><th>Criterion coverage</th><th>Time (seconds)</th><th>Measured tokens</th></tr>"
    for arm, result in summary["arms"].items():
        body += "<tr><td>" + esc(arm) + "</td><td>" + f"{result['valid_runs']} / {result['runs']}" + "</td>"
        for metric in ("pass_rate", "criterion_coverage", "time_seconds", "total_tokens"):
            stat = result[metric]
            body += "<td>" + fmt(stat["mean"], metric in ("pass_rate", "criterion_coverage")) + "<br><small>n=" + str(stat["n"]) + "</small></td>"
        body += "</tr>"
    body += "</table></div>"
    body += "<h2>Run details and output previews</h2>"
    for run in summary["runs"]:
        label = f"{run['case_id']} · repeat {run['repeat']} · {run['arm']} · {run['completion']}"
        body += "<details><summary>" + esc(label) + "</summary>"
        if run["exclusions"]:
            body += "<p>Excluded from valid aggregates:</p>" + listing(run["exclusions"])
        body += "<pre>" + esc(run.get("output_preview", "No embedded preview; inspect artifact files directly.")) + "</pre><p>Artifacts:</p>" + listing(run.get("artifact_paths", []))
        body += detail({"expectations": run.get("expectations", []), "notes": run.get("notes", []), "metrics_source": run.get("metrics_source"), "isolation_evidence": run.get("isolation_evidence")}) + "</details>"
    body += "<h2>Comparisons</h2>" + detail(data.get("comparisons", []))
    body += "<h2>Recommendations</h2>" + listing(data.get("recommendations", []))
    body += "<h2>Coverage and limitations</h2>" + listing(data.get("limitations", []) + summary["warnings"])
    if summary["missing_runs"]:
        body += "<p>Missing comparison arms:</p>" + detail(summary["missing_runs"])
    return shell(data.get("title", "Skill evaluation"), body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("audit", "benchmark"))
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.suffix.lower() != ".html":
        parser.error("--out must be an .html file")
    summary_path = args.out.with_suffix(".summary.json")
    if args.input.resolve() in (args.out.resolve(), summary_path.resolve()):
        parser.error("output must not overwrite input")
    data = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        parser.error("input must be a JSON object")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.mode == "benchmark":
        summary = summarize(data)
        rendered = benchmark_html(data, summary)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    else:
        rendered = audit_html(data)
    args.out.write_text(rendered, encoding="utf-8")
    print(str(args.out.resolve()))


if __name__ == "__main__":
    main()
