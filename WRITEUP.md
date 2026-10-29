# Write-up

Short version: AI reads each proposal and pulls out facts with quotes. Everything after that is plain code using the admin's criteria. A person reviews anything flagged and makes the final call.

See the [diagram](diagram/process-flow.png) for the full flow.

## 1. AI vs. rules

**AI does one job:** turning each proposal's free text into structured fields (licence yes/no, price, weeks, warranty years, etc.), each with an exact quote from the document. Every bidder writes differently, so this is where a language model actually helps. Regex would break on the first unusual wording.

**Code does everything else:**
- PDF to text, and a keyword scan for text aimed at reviewers
- Checking every AI quote really exists in the document
- Mandatory pass/fail
- Weighted scoring, using formulas the admin sets (e.g. price: full marks at $208k, zero at the $260k ceiling)
- Ranking, flags and the reason line

Why there: extraction is a reading problem, scoring is a policy decision. Policy should be identical every time and easy to check. A model asked to "score 0–100" drifts between runs and can't explain why it gave 72 and not 75.

## 2. Consistency and explainability

- Scoring is deterministic. Same facts + same criteria version = same score, every time. Ties break on proposal letter so order never flips.
- Scoring bands are fixed by the admin, not relative to the other bids. Adding a sixth proposal doesn't change anyone else's score.
- The AI step runs at temperature 0 with a strict JSON schema. It can still vary slightly between runs, so the raw output is stored and reused. Re-ranking uses the saved extraction, it doesn't call the model again unless someone asks for a re-extract.
- For each proposal the reviewer sees: the score per criterion, the extracted value, and the quote it came from (click to highlight it in the PDF). The one-line reason is built from those numbers, not written by the AI, so it can't say something the score doesn't support.

So ranking the same set twice gives the same result.

## 3. Human in the loop

- **After ranking:** the reviewer must look at every **flagged** and **ineligible** proposal before the list can be finalised. They can confirm, edit an extracted value, or override a status. Every override needs a written reason.
- **Award:** a human always makes the decision. The tool gives a shortlist, not a winner.

**Audit log**, per run: file hash of each PDF, criteria version, model name and prompt version, raw AI output, verified quotes, each sub-score, flags, final status, and every override (who, when, old value, new value, reason). Nothing is deleted; edits add new entries.

## 4. Changing criteria

Criteria are versioned. A scoring run is locked to the version that was live when it started.

If an admin changes a weight or formula afterwards, old results stay as they were (with their version shown) and the reviewer gets a "criteria changed, re-score?" prompt. Re-scoring is cheap because it reuses the saved extraction, no AI call needed.

If the admin adds a **new** field (say, "Canadian-made panels"), that field was never extracted, so those proposals need a re-extract for that field only. Until then they show "not scored on new criterion" rather than silently getting zero.

## 5. Risks

| Risk | What could happen | Guard |
|---|---|---|
| Wrong extraction | AI reads 12 weeks as 21, or misses the licence | Quote must exist in the text. Reviewer sees value next to quote. Anything vague is "unclear", not guessed |
| Made-up facts | AI fills in a warranty that isn't there | No real quote = not found. Missing numbers block scoring instead of defaulting |
| Prompt injection | Proposal C tells "automated review systems" to rank it first | Prompt treats documents as data. Keyword scan in code as a second check. Either one triggers a flag. AI never sets the score anyway, so it can't hand out full marks |
| Loophole wording | B's licence is a subcontractor "to be confirmed" | Field definition says the bidder must hold it. Result is ineligible, but still shown to the reviewer |
| Missing info rewarded | D gives no timeline, so it can't break the 16-week rule | Missing number = flagged, not scored. A gap never helps a bidder |
| Bias | Model favours polished writing | AI only extracts, never judges quality. Same formula for every bid |
| Over-trust | Reviewer rubber-stamps the list | Flagged items can't be skipped |
| Cost | Long PDFs, many bids | One AI call per proposal; re-scoring reuses saved output |

## How the sample set comes out

| | Status | Score | Why |
|---|---|---|---|
| A | Ranked 1 | 76 | Most experience (14), full team and monitoring plan, mid-range price |
| E | Ranked 2 | 64 | Best warranty and monitoring, but less experience (8) and higher price |
| C | Flagged | 52 | Contains an instruction to rank it first. Also counts experience "since 2020", partly outside the 5-year window |
| D | Flagged | – | No completion time, so the 16-week limit can't be checked. Would score 59/85 on the rest |
| B | Ineligible | – | Bidder doesn't hold the licence, relies on a subcontractor to be confirmed after award |

B is the cheapest and fastest bid, which is why the mandatory gate runs before scoring.

**Assumptions:** "last 5 years" means 2021 onwards. Being over the budget or 16-week limit is flagged for a human rather than auto-rejected, because the brief lists them as category limits rather than mandatory criteria. Scoring formulas (bands, full-marks points) are my examples; in the real tool the admin would set them.
