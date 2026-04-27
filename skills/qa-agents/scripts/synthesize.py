#!/usr/bin/env python3
"""
Synthesize the final QA Agents report from Finder, Auditor, and Referee JSON outputs.

The three agents produce structured JSON; this script does the bookkeeping so the
orchestrator doesn't have to compute totals or cross-reference finding IDs by hand.

It groups findings into:
  - Confirmed:  Auditor accepted (and Referee didn't agree with weak-flag), OR Referee ruled UPHOLD-FINDING
  - Borderline: Auditor accepted but flagged as weakest, AND Referee ruled WEAK
                (worth a second look even though it passed)
  - Disputed:   Referee ruled UPHOLD-DISPROOF (Auditor's challenge stood)

It also emits the score line:
  Finder:   sum of finding severities
  Auditor:  best-case (all disproofs valid) and worst-case (all disproofs invalid)
  Referee:  count of rulings on disproofs + weak-flag rulings

Usage:
    python synthesize.py <finder.json> <auditor.json> <referee.json> [--out <report.md>]

If --out is omitted, the report is printed to stdout.
"""

import argparse
import json
import sys
from pathlib import Path

SEVERITY_NAME = {1: "low", 5: "some", 10: "critical"}
# Sort key — critical first, low last
SEVERITY_RANK = {10: 0, 5: 1, 1: 2}


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def render_finding_block(finding: dict) -> list[str]:
    """Render a single finding as markdown list items."""
    sev_int = finding.get("severity", 0)
    sev_name = SEVERITY_NAME.get(sev_int, "?")
    lines = [
        f"### {finding.get('id', '?')} — {finding.get('title', '<no title>')} "
        f"[+{sev_int} {sev_name}]",
        f"- **Location:** {finding.get('location', '?')}",
        f"- **Claim:** {finding.get('claim', '')}",
        f"- **Evidence:** {finding.get('evidence', '')}",
    ]
    if finding.get("why_it_matters"):
        lines.append(f"- **Why it matters:** {finding['why_it_matters']}")
    lines.append("")
    return lines


def synthesize(finder_path: str, auditor_path: str, referee_path: str) -> str:
    finder = load_json(finder_path)
    auditor = load_json(auditor_path)
    referee = load_json(referee_path)

    # Index by finding id
    findings = {f["id"]: f for f in finder.get("findings", [])}
    verdicts = {v["id"]: v for v in auditor.get("verdicts", [])}
    rulings = {r["id"]: r for r in referee.get("rulings", [])}
    weakest = {w["id"]: w for w in auditor.get("weakest_accepted", [])}
    weak_rulings = {r["id"]: r for r in referee.get("weak_flag_rulings", [])}

    confirmed: list[tuple[dict, str]] = []   # (finding, source_label)
    borderline: list[tuple[dict, str, str]] = []  # (finding, auditor_concern, referee_reasoning)
    disputed: list[tuple[dict, dict, dict]] = []  # (finding, verdict, ruling)

    for fid, finding in findings.items():
        verdict = verdicts.get(fid, {})
        v_kind = verdict.get("verdict", "ACCEPT")  # default to accept if absent

        if v_kind == "ACCEPT":
            # Check if the Auditor weak-flagged this and the Referee agreed
            weak_entry = weakest.get(fid)
            weak_ruling = weak_rulings.get(fid)
            if weak_entry and weak_ruling and weak_ruling.get("ruling") == "WEAK":
                borderline.append((
                    finding,
                    weak_entry.get("concern", ""),
                    weak_ruling.get("reasoning", ""),
                ))
            else:
                confirmed.append((finding, "auditor accepted"))
            continue

        # DISPROVE — needs a Referee ruling to resolve
        ruling = rulings.get(fid)
        if ruling is None:
            # Referee didn't rule on it — surface this so it isn't silently dropped
            confirmed.append((finding, "no Referee ruling — defaulted to confirmed"))
        elif ruling.get("ruling") == "UPHOLD-FINDING":
            confirmed.append((finding, "Referee upheld Finder"))
        elif ruling.get("ruling") == "UPHOLD-DISPROOF":
            disputed.append((finding, verdict, ruling))
        else:
            confirmed.append((finding, f"unknown Referee ruling: {ruling.get('ruling')}"))

    # Severity-ordered display (critical first)
    confirmed.sort(key=lambda x: SEVERITY_RANK.get(x[0].get("severity"), 99))
    borderline.sort(key=lambda x: SEVERITY_RANK.get(x[0].get("severity"), 99))
    disputed.sort(key=lambda x: SEVERITY_RANK.get(x[0].get("severity"), 99))

    # Score arithmetic
    finder_total = finder.get("total_score") or sum(
        f.get("severity", 0) for f in findings.values()
    )
    crit_count = sum(1 for f in findings.values() if f.get("severity") == 10)
    disprove_severities = [
        findings[v["id"]].get("severity", 0)
        for v in verdicts.values()
        if v.get("verdict") == "DISPROVE" and v["id"] in findings
    ]
    auditor_best = sum(disprove_severities)
    auditor_worst = -2 * sum(disprove_severities)
    referee_disproof_rulings = sum(
        1 for r in rulings.values()
        if r.get("ruling") in ("UPHOLD-DISPROOF", "UPHOLD-FINDING")
    )
    referee_weak_rulings = sum(
        1 for r in weak_rulings.values()
        if r.get("ruling") in ("WEAK", "SOLID")
    )
    referee_total_rulings = referee_disproof_rulings + referee_weak_rulings

    # Build report
    out: list[str] = []
    out.append("# QA Agents — Final Report")
    out.append("")
    out.append(f"**Artifact:** {finder.get('artifact', '<unknown>')}  ")
    out.append(f"**Rubric:** {finder.get('rubric', '<unspecified>')}")
    out.append("")

    out.append("## Score Line")
    out.append("")
    out.append(f"- **Finder:** +{finder_total}  ({len(findings)} findings, {crit_count} critical)")
    out.append(
        f"- **Auditor:** {len(disprove_severities)} disproofs attempted  "
        f"(best case +{auditor_best} / worst case {auditor_worst})"
    )
    out.append(
        f"- **Referee:** {referee_total_rulings} ruling(s) total — "
        f"{referee_disproof_rulings} on disproofs, {referee_weak_rulings} on weak-flags"
    )
    out.append("")

    out.append(f"## Confirmed Flaws ({len(confirmed)})")
    out.append("")
    out.append("_These are the findings to address before shipping. Sorted by severity._")
    out.append("")
    if not confirmed:
        out.append("_No flaws confirmed._")
        out.append("")
    else:
        for finding, source in confirmed:
            out.extend(render_finding_block(finding))
            out.append(f"_Source: {source}._")
            out.append("")

    out.append(f"## Borderline Flaws ({len(borderline)})")
    out.append("")
    out.append(
        "_The Auditor accepted these findings but flagged them as the closest to challengeable, "
        "and the Referee agreed they're borderline. They survived the review, but they're the ones "
        "to apply extra scrutiny to before relying on them._"
    )
    out.append("")
    if not borderline:
        out.append("_No borderline flaws — every accepted finding was sturdy enough that the "
                   "Auditor didn't flag it as questionable._")
        out.append("")
    else:
        for finding, concern, reasoning in borderline:
            out.extend(render_finding_block(finding))
            out.append(f"- **Auditor's concern:** {concern}")
            out.append(f"- **Referee's reasoning:** {reasoning}")
            out.append("")

    out.append(f"## Disputed Flaws ({len(disputed)})")
    out.append("")
    out.append(
        "_The Auditor's disproof stood under Referee review. These are usually the most "
        "informative cases — the artifact has a defensible answer to a plausible-sounding "
        "objection. Read the reasoning and decide whether to accept it._"
    )
    out.append("")
    if not disputed:
        out.append("_No disputed flaws._")
        out.append("")
    else:
        for finding, verdict, ruling in disputed:
            sev_int = finding.get("severity", 0)
            sev_name = SEVERITY_NAME.get(sev_int, "?")
            out.append(
                f"### {finding.get('id', '?')} — {finding.get('title', '<no title>')} "
                f"[+{sev_int} {sev_name}]"
            )
            out.append(f"- **Original claim (Finder):** {finding.get('claim', '')}")
            out.append(f"- **Counter-claim (Auditor):** {verdict.get('counter_claim', '')}")
            out.append(f"- **Auditor evidence:** {verdict.get('evidence', '')}")
            out.append(f"- **Referee reasoning:** {ruling.get('reasoning', '')}")
            out.append("")

    out.append("## Recommended Actions")
    out.append("")
    if confirmed:
        out.append("Address in severity order. Each action maps back to a finding ID.")
        out.append("")
        for i, (finding, _) in enumerate(confirmed, 1):
            out.append(
                f"{i}. **{finding.get('id', '?')}** — "
                f"{finding.get('title', '<no title>')} "
                f"({finding.get('location', '?')})"
            )
        out.append("")
    else:
        out.append("_Nothing to act on._")
        out.append("")

    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(
        description="Synthesize the final QA Agents report from Finder, Auditor, and Referee JSON."
    )
    parser.add_argument("finder", help="Path to finder.json")
    parser.add_argument("auditor", help="Path to auditor.json")
    parser.add_argument("referee", help="Path to referee.json")
    parser.add_argument(
        "--out",
        help="Output markdown path. If omitted, prints to stdout.",
    )
    args = parser.parse_args()

    try:
        report = synthesize(args.finder, args.auditor, args.referee)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in input file: {e}", file=sys.stderr)
        sys.exit(1)

    if args.out:
        Path(args.out).write_text(report)
        print(f"Wrote {args.out}")
    else:
        print(report)


if __name__ == "__main__":
    main()
