# QA Agents — Severity Rubrics by Artifact Type

The scoring weights (+1 / +5 / +10) are constant across all rubrics. Only the *definitions* of low / some / critical impact change per domain. Use the closest-fit rubric, then let the user tweak in 30 seconds.

When in doubt about severity, the Finder should err toward the lower bucket — the Auditor's asymmetric penalty already incentivizes against inflation.

---

## Code (default for `.py`, `.js`, `.ts`, `.go`, `.rs`, `.java`, etc.)

| Severity | Examples |
|---|---|
| **Critical (+10)** | Security vulnerabilities (injection, auth bypass, secret leakage), data loss or corruption, crashes on common inputs, infinite loops, race conditions in production paths, broken core functionality, deployment-blocking bugs |
| **Some (+5)** | Logic errors that produce wrong outputs on valid inputs, missing error handling that could fail in production, performance cliffs (O(n²) where O(n) is expected), edge cases that fail silently, incorrect API contracts |
| **Low (+1)** | Style issues, minor inefficiencies, naming inconsistencies, dead code, missing comments on non-obvious logic, formatting, weak typing where it doesn't cause bugs |

**Ground truth source:** test results, runtime behavior, language/framework specs.

---

## Document / strategy doc (default for `.md`, `.docx` outside the vault's structured folders)

| Severity | Examples |
|---|---|
| **Critical (+10)** | Factual errors that change the conclusion, math errors in financials/projections, an unsupported core claim, a missing risk that materially shifts the recommendation, internally contradictory positions |
| **Some (+5)** | Weak assumption that the conclusion rests on, missing key context for the audience, overclaim that's defensible only with caveats not stated, missing customer/stakeholder perspective, ambiguity that could be misread |
| **Low (+1)** | Typos, awkward phrasing, formatting inconsistency, redundancy, weak transitions, citation style |

**Ground truth source:** the user's actual knowledge of the domain, source documents, prior decisions.

---

## PR-FAQ / Working Backwards doc

This rubric uses Amazon's Working Backwards framework as ground truth. A good PR-FAQ answers a specific customer pain with a specific solution and specific success metrics.

| Severity | Examples |
|---|---|
| **Critical (+10)** | Customer pain isn't real or isn't validated, financials don't add up or hide assumptions, no clear "why now," success metrics aren't measurable or aren't tied to customer outcomes, the press release wouldn't actually excite the target customer |
| **Some (+5)** | Vague or unfalsifiable success metric, missing FAQ that an exec would obviously ask, weak differentiation from existing solutions, hand-waved scaling story, customer quote feels manufactured |
| **Low (+1)** | Tone issues, redundancy across press release and FAQ, formatting, headline weakness, minor narrative gaps |

**Ground truth source:** the user's actual customer knowledge, comparable Amazon-style docs, prior validated metrics.

---

## 6-pager / OP doc

| Severity | Examples |
|---|---|
| **Critical (+10)** | Recommendation isn't supported by the data presented, math errors in the financial section, missing material risk, the "why us / why now" question isn't answered, internally inconsistent claims across sections |
| **Some (+5)** | Weak headline narrative (the first paragraph doesn't carry the doc), data tables that don't match prose claims, missing alternative considered, assumption that's load-bearing but not flagged, FAQs that dodge the hard questions |
| **Low (+1)** | Section ordering, redundancy, tone, formatting |

**Ground truth source:** the user's actual data, prior doc reviews, comparable approved docs.

---

## Investment / deal memo

| Severity | Examples |
|---|---|
| **Critical (+10)** | Missing material risk (regulatory, key-person, customer concentration, technology risk), overstated returns or understated downside, fundamental thesis flaw, missing diligence on a topic that would change the decision, valuation math errors |
| **Some (+5)** | Unaddressed counterfactual (what if the market grows slower?), optimistic operational assumption, weak diligence on a moderate-impact topic, comparable selection bias, capital structure complexity not surfaced |
| **Low (+1)** | Minor data gap, citation, formatting, narrative tightening |

**Ground truth source:** Wasson Enterprise's Partnership Charter, prior deal post-mortems, public comparables.

---

## Contract / legal doc

This rubric assumes the Finder is reading from a business-impact angle, not a pure legal-precision angle. For pure legal review, use the `legal:contract-review` skill.

| Severity | Examples |
|---|---|
| **Critical (+10)** | Undisclosed exposure (unlimited liability, broad indemnity, unbounded reps), conflicting clauses, missing material protection (no IP assignment where required, no termination right), one-sided remedy structure |
| **Some (+5)** | Ambiguity that could cost money under reasonable interpretation, unfavorable but survivable terms, missing standard protection that the org's playbook calls for, unclear notice/cure mechanics |
| **Low (+1)** | Drafting issues, citation/cross-reference errors, defined-term inconsistency, formatting |

**Ground truth source:** the org's contract playbook, prior signed agreements, the relevant legal-risk rubric.

---

## Spreadsheet / financial model

| Severity | Examples |
|---|---|
| **Critical (+10)** | Formula errors that change the headline number, broken cell references, hard-coded values in summary cells (should be formulas), unit mismatches (mixing $K and $M), circular references that aren't intentional, missing assumption that drives the result |
| **Some (+5)** | Logic errors with bounded impact, missing edge case (zero, negative, large input), sensitivity ignored on a load-bearing input, inconsistent assumption applied across tabs, sign errors in non-headline cells |
| **Low (+1)** | Formatting, naming, layout, missing labels, color-coding inconsistency |

**Ground truth source:** the source data, recalculation, the user's mental model of the result.

---

## Decision / argument

This rubric works on prose arguments — recommendations, position papers, decision docs, "should we X" memos.

| Severity | Examples |
|---|---|
| **Critical (+10)** | Missing failure mode that would kill the decision if it occurred, hidden assumption that's load-bearing and wrong, second-order effect that flips the ROI calculation, false dichotomy that excludes the actually-best option, missing reversibility analysis on an irreversible decision |
| **Some (+5)** | Unaddressed counterargument that a smart skeptic would raise, weak analogy that the conclusion rests on, missing precedent (this has been tried before), unstated dependency on another decision |
| **Low (+1)** | Minor logic gap, weak transition between argument steps, framing issues, redundancy |

**Ground truth source:** prior decisions, base rates, the user's actual experience with similar decisions.

---

## Custom / Other

If the artifact doesn't fit any of the above, define a rubric in four lines with the user before spawning the Finder:

```
Critical (+10): <what would make this artifact fail catastrophically?>
Some (+5):     <what would significantly weaken it but is recoverable?>
Low (+1):      <what is minor polish or taste?>
Ground truth:  <what will the Referee use? user expertise, source data, comparable docs, prior decision, etc.>
```

The mechanism doesn't care about the domain — it cares that the rubric is sharp enough that the Finder can score honestly, the Auditor can challenge specific claims, and the Referee has something concrete to anchor its rulings on.

---

## A note on scoring inflation

The single biggest failure mode of this skill is the Finder padding low-severity findings to inflate its score. Three guards:

1. The Finder is told the Auditor will challenge weak findings — every false-positive low becomes an Auditor disproof, which the Auditor will likely win.
2. The rubrics above are written so "low" is a deliberate residual category, not a default.
3. The Phase 1 human checkpoint lets the user delete obvious padding before it pollutes Phase 2.

If a Finder report has more than ~30% of its score in low-impact findings, ask the user whether to re-run with a tightened rubric.
