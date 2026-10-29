"""
Deterministic scoring step.

Reads the admin's criteria (criteria.json) and the extracted facts
(sample_extraction.json, or the output of extract.py) and writes ranking.json.
No AI here. Same inputs always give the same output.

Usage: python score.py [extraction.json] [criteria.json] [out.json]
"""
import json
import sys


def linear(value, full_marks_at, zero_at):
    pct = (value - zero_at) / (full_marks_at - zero_at)
    return max(0.0, min(1.0, pct)) * 100


def bands(value, band_list):
    for minimum, score in band_list:
        if value >= minimum:
            return score
    return 0


def score_criterion(c, fields):
    """Return (score 0-100, list of missing fields)."""
    if c["type"] == "parts":
        needed = [p["field"] for p in c["parts"]]
    elif c["type"] == "checklist":
        needed = c["fields"]
    else:
        needed = [c["field"]]

    # A checklist item that wasn't found simply scores 0 for that item.
    # Any other missing number means we can't score this criterion.
    if c["type"] != "checklist":
        missing = [f for f in needed if fields[f]["status"] == "not_found"]
        if missing:
            return None, missing

    if c["type"] == "bands":
        return bands(fields[c["field"]]["value"], c["bands"]), []
    if c["type"] == "linear":
        return linear(fields[c["field"]]["value"], c["full_marks_at"], c["zero_at"]), []
    if c["type"] == "parts":
        total = sum(linear(fields[p["field"]]["value"], p["full_marks_at"], p["zero_at"]) * p["share"] / 100
                    for p in c["parts"])
        return total, []
    if c["type"] == "checklist":
        hits = sum(1 for f in c["fields"] if fields[f]["value"] is True)
        return hits / len(c["fields"]) * 100, []
    raise ValueError(f"Unknown criterion type {c['type']}")


def evaluate(letter, proposal, criteria):
    fields = proposal["fields"]
    flags = []

    # 1. Mandatory gate (pass / fail / unclear)
    for m in criteria["mandatory"]:
        values = [fields[f] for f in m["fields"]]
        if any(v["status"] == "found" and v["value"] is False for v in values):
            note = next((v.get("note") for v in values if v.get("note")), "")
            return {"status": "ineligible", "score": None,
                    "reason": f"Fails mandatory check ({m['label']}): {note}.".replace(": .", ".")}
        if any(v["status"] != "found" for v in values):
            flags.append(f"cannot confirm '{m['label']}' from the document")

    # 2. Safety flags
    if proposal.get("instructions_to_reviewer_found"):
        flags.append("document tells the reviewer how to rank it (ignored)")

    for field, limit in criteria["limits"].items():
        v = fields.get(field)
        if v and v["status"] == "found" and v["value"] > limit["max"]:
            flags.append(f"{field} is over the category limit of {limit['max']}")

    for name, v in fields.items():
        if v["status"] == "unclear":
            flags.append(v.get("note", f"{name} is unclear"))

    # 3. Weighted score
    parts, missing = {}, []
    for c in criteria["weighted"]:
        s, miss = score_criterion(c, fields)
        parts[c["id"]] = s
        missing += miss

    if missing:
        scored = [c for c in criteria["weighted"] if parts[c["id"]] is not None]
        partial = sum(parts[c["id"]] * c["weight"] / 100 for c in scored)
        possible = sum(c["weight"] for c in scored)
        notes = "; ".join(fields[m].get("note", m + " not stated").rstrip(".") for m in missing)
        return {"status": "flagged", "score": None,
                "reason": f"Not scored: {notes}. "
                          f"Scores {partial:.0f}/{possible} on the rest. Reviewer to ask the bidder."}

    total = round(sum(parts[c["id"]] * c["weight"] / 100 for c in criteria["weighted"]))
    result = {"status": "flagged" if flags else "ranked", "score": total, "parts": parts}
    if flags:
        result["reason"] = (f"Scores {total} but held for review: "
                            + "; ".join(f.rstrip(".") for f in flags) + ".")
    return result


def describe(cid, fields):
    """Plain-language value for a criterion, used in the reason line."""
    v = lambda f: fields[f]["value"]
    team = sum(1 for f in ["named_project_lead", "crew_described", "safety_plan", "monitoring_plan"] if v(f))
    return {
        "experience": f"experience ({v('installs_100kw_5yrs')} installs)",
        "price": f"price (${v('price_cad'):,})",
        "timeline": f"timeline ({v('completion_weeks')} weeks)",
        "warranty": f"warranty ({v('panel_warranty_years')}y panel, {v('workmanship_warranty_years')}y workmanship)",
        "team": f"team plan ({team}/4 items)",
    }[cid]


def ranked_reason(r, fields):
    p = r["parts"]
    best = sorted(p, key=lambda k: (-p[k], k))[:2]
    worst = min(p, key=lambda k: (p[k], k))
    return (f"Passes mandatory checks. Best on {describe(best[0], fields)} and {describe(best[1], fields)}; "
            f"weakest on {describe(worst, fields)}.")


def main():
    extraction_path = sys.argv[1] if len(sys.argv) > 1 else "sample_extraction.json"
    criteria_path = sys.argv[2] if len(sys.argv) > 2 else "criteria.json"
    out_path = sys.argv[3] if len(sys.argv) > 3 else "../ranking.json"

    extraction = json.load(open(extraction_path))
    criteria = json.load(open(criteria_path))

    results = {k: evaluate(k, v, criteria) for k, v in extraction.items() if not k.startswith("_")}

    ranked = sorted([k for k, r in results.items() if r["status"] == "ranked"],
                    key=lambda k: (-results[k]["score"], k))  # tie-break on letter so order never flips
    for i, k in enumerate(ranked, 1):
        results[k]["rank"] = i
        results[k]["reason"] = ranked_reason(results[k], extraction[k]["fields"])

    out = []
    for k in sorted(results, key=lambda k: (results[k].get("rank") or 99, k)):
        r = results[k]
        out.append({"proposal": k, "rank": r.get("rank"), "status": r["status"],
                    "score": r["score"], "reason": r["reason"]})

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    for row in out:
        print(row)


if __name__ == "__main__":
    main()
