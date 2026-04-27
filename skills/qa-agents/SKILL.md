---
name: qa-agents
description: >
  Adversarial three-agent review of any artifact — code, documents, PR-FAQs, 6-pagers, deal
  memos, contracts, financial models, or decisions. Spawns a Finder (severity-scored findings,
  +1/+5/+10), an Auditor (adversarially challenges each finding; +severity for valid disproofs,
  −2×severity for false ones), and a Referee (judges disagreements against ground truth, +1/−1).
  Pauses for human review between phases. Trigger when the user says "QA this", "adversarial
  review", "stress test this", "red team this", "find bugs", "find issues", "challenge this",
  "audit this", "bar-raise this", or is about to ship a PR-FAQ, 6-pager, deal memo, contract,
  model, or code change and wants pressure-tested feedback tougher than a normal review.
compatibility: >
  Requires subagents (Task tool) to spawn the Finder, Auditor, and Referee in independent
  contexts. Without subagents the adversarial-isolation premise collapses and this skill
  should not be used.
version: 0.4.0
---

# QA Agents — Adversarial Three-Agent Review

This skill applies an adversarial verification pattern to any artifact. The mechanism is independent of domain: it works on code, documents, financial models, contracts, deal memos, decisions, or anything else that can be examined for flaws.

The three agents and their incentives:

| Agent | Job | Scoring |
|---|---|---|
| **Finder** | List every flaw it can identify, scored by severity | +1 low impact, +5 some impact, +10 critical impact. Total = sum of finding scores. |
| **Auditor** | Try to disprove each finding | +(severity) for a valid disproof, −2×(severity) for a false disproof. Total = net of disproofs. |
| **Referee** | Judge each disagreement between Finder and Auditor against ground truth | +1 per correct judgment, −1 per wrong judgment. Total = net of judgments. |

The scoring is what makes this work. The Finder is rewarded for impact-weighted thoroughness; the Auditor pays double for false disproofs, so it can't rubber-stamp; the Referee believes the user has ground truth and will grade it, which keeps it careful.

This is the **Bar Raiser mechanism applied to AI** — adversarial pressure between independent agents surfaces flaws that a single agent (no matter how good the prompt) consistently misses.

---

## Operating mode

**Default: autonomous.** Run all three phases end-to-end without stopping for human review. The user gets one synthesized report at the end with all three agents' work attached for transparency. This is the production path — the value is in the final report, not in shepherding three checkpoints.

**Interactive mode (opt-in):** if the user explicitly asks to review between phases, or if you're debugging the skill itself, pause after each phase and present the intermediate output. The user can prune findings, redirect the Auditor, etc. Trigger this mode only when the user says something like "let me review between phases", "go slow", or "show me the Finder before the Auditor runs."

The autonomous default is what makes this skill scalable. A user shouldn't have to babysit three subagents to get a good review.

---

## Phase 0 — Scope the review

Before spawning any agents, gather four things from the user. Ask them in one consolidated message; don't drip them out one at a time.

1. **Artifact** — file path, pasted content, or a clear pointer (e.g., "the PR-FAQ at Projects/Foo/PRFAQ.md"). If multiple files, list them.
2. **Artifact type** — code, document/strategy doc, PR-FAQ, 6-pager, investment/deal memo, contract, financial model/spreadsheet, decision/argument, or other. This drives the rubric.
3. **Rubric** — load the matching rubric from `references/rubrics.md`. Show the user the severity definitions and ask if they want to tweak. If the artifact type is "other", help them define one in 30 seconds: what counts as low/some/critical impact?
4. **Ground-truth source** — what will the Referee be told the ground truth is? The most honest framing is: "the user has the actual correct ground truth and will score the Referee's calls." Even when this isn't literally true, framing it this way makes the Referee careful. If the user has explicit ground truth (test results, expert review, prior decision), tell the Referee to use that.

Default values are fine for many runs. If the user says "QA this code" with a path, you can auto-select the code rubric and confirm in one line: "Using the code rubric (low/some/critical = +1/+5/+10). Anything to tweak before I spawn the Finder?"

---

## Phase 1 — Finder

Spawn a fresh Task subagent (subagent_type: `general-purpose`, or a code-aware agent for code). It needs a clean context — never reuse a session that has already seen the artifact through another lens, because that anchors the Finder on prior reasoning and quietly weakens the mechanism.

**Prompt the Finder with:**

- The artifact (full content, or a path with read instructions)
- The rubric, including severity definitions
- The scoring rule, verbatim: "You will be scored as follows: +1 for each finding with low impact, +5 for some impact, +10 for critical impact. The user wants high recall — list everything you can defend, but be honest about severity. Inflating severity is penalized in the next phase."
- A reminder that an Auditor will adversarially challenge its findings, so weak findings will cost it points later
- The output format (JSON, see below)

**Required output format from the Finder (single JSON object):**

```json
{
  "artifact": "<path or short description>",
  "rubric": "<rubric name, e.g., code, document, prfaq>",
  "total_score": 0,
  "findings": [
    {
      "id": "F1",
      "title": "Short descriptive title",
      "severity": 10,
      "location": "file.py:42 | §3.2 | cell B14 | page 3",
      "claim": "One-sentence statement of the flaw.",
      "evidence": "Quote, specific reference, or reproducible step.",
      "why_it_matters": "Impact in 1-2 sentences."
    }
  ]
}
```

`severity` is the integer 1, 5, or 10. `total_score` is the sum across findings. JSON keeps the data structured so the synthesis script can consume it later.

**After Finder returns:**

1. Save the JSON to `outputs/qa-agents-<artifact-name>/finder.json`.
2. In autonomous mode (default): proceed directly to Phase 2.
3. In interactive mode (only if explicitly requested): render a brief summary, ask the user if anything is obviously off, apply edits, then proceed.

The pruning role belongs to the Auditor — that's what its scoring asymmetry exists to enforce. The human checkpoint exists for debugging the skill, not for ordinary runs.

---

## Phase 2 — Auditor

Spawn a fresh Task subagent in an isolated context — separate from the Finder. The Auditor should see the Finder's *report* but not its reasoning trail; that asymmetry is what produces independent challenge rather than agreement.

**Prompt the Auditor with:**

- The artifact (same as the Finder received)
- The Finder's findings JSON
- The rubric (so it understands severity)
- The scoring rule, verbatim: "For each finding, you can either ACCEPT it or DISPROVE it. If you disprove a finding and you are correct, you gain +(severity) points. If you disprove a finding and you are WRONG, you lose -2×(severity) points. Accepting a finding costs you nothing. Therefore: only disprove findings you can defend rigorously. The Referee will judge your disproofs against ground truth."
- The weakest-flag instruction, verbatim: "After deciding ACCEPT/DISPROVE on every finding, identify up to 3 of the ACCEPTED findings that you came closest to disproving. These are findings you considered challenging but couldn't profitably attack under the asymmetric scoring. Surface them as `weakest_accepted` with your specific concern. This is honest critical thinking, not strategic gaming — the Referee will rule whether your concerns are fair. Skipping this step or padding it with random IDs is itself adversarial pressure the Referee can detect."
- The output format (JSON, see below)

**Required output format from the Auditor (single JSON object):**

```json
{
  "verdicts": [
    {"id": "F1", "verdict": "ACCEPT"},
    {
      "id": "F2",
      "verdict": "DISPROVE",
      "counter_claim": "One-sentence rebuttal.",
      "evidence": "Specific evidence the Finder was wrong.",
      "confidence": 8
    }
  ],
  "weakest_accepted": [
    {
      "id": "F5",
      "concern": "One-sentence statement of why this accepted finding is the closest to challengeable — what reservation made you almost disprove it?"
    }
  ]
}
```

Every finding ID from the Finder must appear in `verdicts` with a verdict. `confidence` (1-10) and the counter-claim/evidence fields apply only to DISPROVE.

`weakest_accepted` should contain 0–3 entries. Zero is fine if every accepted finding was clearly defensible. Otherwise list 1–3 with one-sentence concerns. Don't pad — if you only have one real concern, list one.

The point of `weakest_accepted` is to keep the Auditor critically engaged even when the Finder is high-quality enough that disproofs aren't profitable. Without it, a strong Finder would let the Auditor rubber-stamp the whole report and the Referee would have nothing to do. With it, the user always gets a signal about which "passed" findings are most worth a second look.

**After Auditor returns:**

1. Save to `outputs/qa-agents-<artifact-name>/auditor.json`.
2. Proceed to Phase 3.

A zero-DISPROVE outcome is a real outcome, not a failure — it means the Finder's findings were sturdy enough that the Auditor couldn't profitably challenge any of them under the asymmetric scoring (-2× for false disproofs vs. +severity for valid ones). The Referee still has work in this case: it rules on the Auditor's `weakest_accepted` flags. Skip Phase 3 only if the Auditor produced zero disproofs AND zero weakest-flags (rare — only on tiny artifacts).

---

## Phase 3 — Referee

Spawn a third fresh Task subagent in an isolated context.

**Prompt the Referee with:**

- The artifact
- Both the Finder JSON and the Auditor JSON
- The rubric
- The scoring rule, verbatim: "The user has the actual correct ground truth and will grade your judgments. You have two jobs. (1) For each finding the Auditor DISPROVED, rule whether the disproof is valid: UPHOLD-DISPROOF (Auditor was right) or UPHOLD-FINDING (Auditor was wrong). (2) For each finding in the Auditor's weakest_accepted list, rule whether the Auditor's concern is fair: WEAK (the finding is borderline and merits extra scrutiny from the user) or SOLID (the Auditor was over-cautious; the finding stands without need for further review). Each correct ruling earns +1, each incorrect ruling loses -1. Confident wrong answers cost as much as confident right ones."
- The output format (JSON, see below)

The Referee has two arrays to fill: `rulings` (on disproofs) and `weak_flag_rulings` (on weakest-accepted). Either may be empty depending on what the Auditor produced.

**Required output format from the Referee (single JSON object):**

```json
{
  "rulings": [
    {
      "id": "F2",
      "ruling": "UPHOLD-DISPROOF",
      "reasoning": "2-3 sentences explaining why."
    }
  ],
  "weak_flag_rulings": [
    {
      "id": "F5",
      "ruling": "WEAK",
      "reasoning": "2-3 sentences explaining why the Auditor's concern is fair (or why it isn't)."
    }
  ]
}
```

`ruling` in `rulings` is `UPHOLD-DISPROOF` (Auditor was right, Finder was wrong) or `UPHOLD-FINDING` (Auditor was wrong, Finder stands). `ruling` in `weak_flag_rulings` is `WEAK` (Auditor's concern is fair — finding is borderline) or `SOLID` (Auditor was over-cautious — finding doesn't need extra scrutiny).

**After Referee returns:**

1. Save to `outputs/qa-agents-<artifact-name>/referee.json`.
2. Proceed to Phase 4.

---

## Phase 4 — Synthesis

Run the bundled script to produce the final report:

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/qa-agents/scripts/synthesize.py \
  outputs/qa-agents-<artifact-name>/finder.json \
  outputs/qa-agents-<artifact-name>/auditor.json \
  outputs/qa-agents-<artifact-name>/referee.json \
  --out outputs/qa-agents-<artifact-name>/final-report.md
```

The script does the work that's mechanical and easy to get wrong by hand: cross-referencing finding IDs across the three reports, computing score totals, and grouping findings into:

- **Confirmed flaws** — Auditor accepted (and either Referee ruled SOLID, or no weak-flag was raised on it), OR Referee ruled UPHOLD-FINDING. Sorted by severity.
- **Borderline flaws** — Auditor accepted but flagged as weakest, AND Referee ruled WEAK. These are the findings most worth a second look even though they passed.
- **Disputed flaws** — Referee ruled UPHOLD-DISPROOF. The Auditor's challenge stood.
- **Score line** — Finder total, Auditor disproofs attempted, Referee rulings (across both arrays).

After the script runs, present the report to the user as the primary deliverable. The Finder/Auditor/Referee JSONs in the same `outputs/` folder are appendices — not noise to drop on the user, but available if they want to inspect the raw debate. Mention the JSON paths once at the bottom of your reply for transparency, but lead with the synthesized report.

If the user asked for an interactive run, they've already seen the intermediate outputs and don't need them re-summarized. Just present the final report.

If the script isn't available for some reason, do the synthesis by hand using the same grouping rules. The script just removes the arithmetic.

---

## Operating rules

- **Three isolated Task subagents.** The adversarial value comes from each agent reasoning independently. Sequential phases in one chat collapse the mechanism into a single perspective wearing different hats — that's the failure mode to avoid.
- **Two human checkpoints — after the Finder and at the end.** A third checkpoint between Auditor and Referee is worth adding for high-stakes runs (contracts, large investments).
- **Don't fix the artifact during review.** This skill produces a report. Mixing review with fixing is how you end up with both a half-baked review and a half-baked fix.
- **Scope big artifacts before spawning.** Three agents on a 200-page document or a 50k-line codebase produce shallow output. Have the user pick a section first.
- **Cite locations precisely.** File:line for code, section/heading for docs, cell address for spreadsheets, page for PDFs. The user has to be able to act on findings without re-reading the artifact to find them.

---

## Why this works (and where it doesn't)

This is a debate-with-judge pattern. It outperforms single-agent review because:

1. **The Finder's incentive is impact-weighted recall.** Severity scoring stops it from padding with trivia.
2. **The Auditor's penalty is asymmetric.** −2× for false disproofs > +1× for valid ones, so the Auditor only challenges what it can defend.
3. **The Referee believes it'll be graded.** That framing produces more careful judgments than "summarize the disagreement."
4. **Three isolated contexts mean none of them is anchored on the others' reasoning.** Sequential phases in one context lose most of this value.

Where it doesn't work:

- **Artifacts the agents can't fully evaluate.** Live systems, real-world experiments, anything requiring tools the agents lack. Use this on artifacts that are evaluable from text.
- **Subjective taste questions.** The mechanism rewards adversarial pressure on factual/logical claims. "Is this prose engaging?" doesn't have a ground truth the Referee can rule on.
- **Tiny artifacts.** A 20-line function or a 1-paragraph claim is overkill for three agents. Just ask for a quick review.

---

## References

- `references/rubrics.md` — preset severity rubrics per artifact type. Read this before Phase 0.
- `scripts/synthesize.py` — Phase 4 synthesis script. Takes finder/auditor/referee JSON, emits the unified final report.

---

## Origin

This skill is a generalization of Mike's [[QA Agents]] prompt (originally written for code), expanded to work across any artifact type. The original three-role structure and scoring asymmetries are preserved verbatim because the mechanism — not the domain — is the value.
