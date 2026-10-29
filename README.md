# AI Proposal Triage – Design

**Name:** [Your Full Name]
**Reference:** MATACS-TH-2026-02
**Time spent:** [e.g. 1 hour 15 minutes]

## Files

| File | What's in it |
|---|---|
| [WRITEUP.md](WRITEUP.md) | Answers to the five questions, plus how the sample set ranks |
| [diagram/process-flow.png](diagram/process-flow.png) | Flow from upload to ranked output (AI, rules and human steps colour-coded) |
| [PROMPTS.md](PROMPTS.md) | The extraction prompt, exactly as sent |
| [ranking.json](ranking.json) | Expected ranking of proposals A–E |
| [prototype/](prototype/) | Small scripts that run the design (optional part) |

## Design in one paragraph

AI is used for one thing: reading each proposal and pulling out the facts the criteria need, each backed by an exact quote. Code checks those quotes are real, applies the mandatory pass/fail rules, scores with the admin's formulas and ranks. Anything the tool isn't sure about (missing info, unclear wording, text trying to steer the review) is flagged for a person instead of being guessed. A human reviews flags and makes the award.

## Prototype

```
cd prototype
python score.py            # uses sample_extraction.json + criteria.json, writes ../ranking.json
```

`ranking.json` in this repo is the output of that command, not typed by hand.

`extract.py` is the AI step. It needs an API key (copy `.env.example` to `.env`) and the proposal text in `prototype/proposals/A.txt` … `E.txt`. That folder is git-ignored because the brief asks not to copy proposal text into the repo. For the same reason `sample_extraction.json` holds the expected values only, without the evidence quotes.

| File | Role |
|---|---|
| `criteria.json` | What the admin screens would save: mandatory checks, weights, scoring formulas, limits |
| `fields.json` | Field definitions sent to the model (would be generated from the criteria) |
| `prompt_system.txt`, `prompt_user.txt` | The prompt from PROMPTS.md |
| `extract.py` | AI extraction + quote check + keyword scan |
| `score.py` | Deterministic gate, scoring, flags, ranking |

## How I used AI tools

[Edit this so it matches what you actually did.]

I used Claude to talk through the flow, draft the prompt and write the first version of the scoring script. I checked each proposal against the criteria myself and changed the output where I disagreed. One example: [describe a real correction you made, e.g. the draft treated C's "weekly progress reports" as meeting the monitoring requirement; I changed it because the criterion is about monitoring the solar system after install, not reporting during the build.]
