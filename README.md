# QA Agents

Adversarial three-agent review for any artifact — code, documents, deal memos, contracts, financial models, decisions. A Claude Code / Cowork plugin.

## What it does

Spawns three subagents in isolated contexts:

- **Finder** produces severity-scored findings (`+1` low / `+5` some / `+10` critical).
- **Auditor** adversarially challenges each finding. Gains `+severity` for valid disproofs, loses `2×severity` for false ones. Also flags the 1–3 weakest accepted findings as borderline.
- **Referee** judges disputed findings against ground truth, plus rules whether the Auditor's borderline flags are fair (`+1` per correct ruling, `-1` per wrong).

The scoring asymmetry is what makes it work. The Auditor pays double for false disproofs, so it can't profitably rubber-stamp by attacking everything. When the Finder is high-quality and the Auditor has nothing to challenge, the borderline-flag mechanism keeps the Referee engaged — every run produces both a confirmed-flaws list and a "second-look" list.

It's the Bar Raiser mechanism applied to AI.

## Install

1. Download [`dist/qa-agents.plugin`](dist/qa-agents.plugin) (or grab it from [Releases](../../releases))
2. Drop the file into Cowork's plugin manager
3. Restart your session

## Use

After installing, just say:

- `QA this code` + a path
- `Adversarial review of [doc]`
- `Stress test my PR-FAQ`
- `Red team this deal memo`
- `What could go wrong with this decision?`

The skill auto-detects the artifact type and picks a rubric. Eight presets ship in [`skills/qa-agents/references/rubrics.md`](skills/qa-agents/references/rubrics.md):

- Code (default for `.py`, `.js`, `.ts`, `.go`, etc.)
- Document / strategy doc
- PR-FAQ / Working Backwards
- 6-pager / OP doc
- Investment / deal memo
- Contract / legal doc
- Spreadsheet / financial model
- Decision / argument

If your artifact doesn't fit, the skill walks you through defining a custom rubric in 30 seconds.

## What you get

After the three agents run (autonomous by default — no human checkpoints), you get one synthesized report with:

- **Confirmed flaws** — sorted by severity, with citations.
- **Borderline flaws** — Auditor's weakest-accepted findings the Referee agreed are worth a second look.
- **Disputed flaws** — cases where the Auditor's challenge stood under Referee review.
- **Score line** — Finder total, Auditor disproof attempts, Referee rulings.

The raw JSON for each agent is saved alongside for transparency.

## Running interactively

The default is autonomous. If you want to inspect each phase before the next agent spawns, say `let me review between phases` or `go slow` in your initial request. Useful for debugging the skill itself or for high-stakes reviews where you want to prune the Finder's output.

## How the synthesis script works

`skills/qa-agents/scripts/synthesize.py` takes the three JSON outputs and produces the final markdown report. It's bundled so the orchestrator doesn't have to do score arithmetic by hand.

```bash
python3 scripts/synthesize.py finder.json auditor.json referee.json --out final-report.md
```

## Origin

Generalized from a code-review prompt I wrote. The underlying mechanism — adversarial verification with severity-asymmetric scoring and a referee with implicit ground-truth pressure — isn't domain-specific, so the skill ships with rubrics for everything from contracts to PR-FAQs.

## License

MIT. See [LICENSE](LICENSE).
