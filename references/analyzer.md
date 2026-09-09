# Analyze observed differences

Adapted from Anthropic `agents/analyzer.md`; see ../ATTRIBUTION.md.

After grading, inspect the condition mapping, outputs, transcripts and exact skill versions. Report which task outcomes changed, which stayed the same, and whether differences persisted across cases or repeats. Surface variable results, common failures, missing evidence and unexpectedly broad activation.

Connect a failure to a skill instruction only when the transcript or a controlled change supports that link. Otherwise label it a hypothesis. Separate useful business knowledge from potentially unnecessary procedures. Describe why a proposed simplification preserves essential requirements.

Do not equate a lower time or token figure with better performance if the output is incomplete. Do not treat characters as tokens, compare unmatched cases as an uplift estimate, or treat a single pilot as broad proof. Ties, contaminated baselines and missing telemetry remain visible.

Recommend an action with scope and evidence: keep, simplify, investigate overlap, evaluate further, or consider retirement. State what remains uncertain. Recommendations do not authorize editing or deleting installed skills.
