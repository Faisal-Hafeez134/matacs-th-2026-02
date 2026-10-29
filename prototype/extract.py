"""
AI extraction step + the code checks that wrap it.

Reads proposal text from prototype/proposals/<LETTER>.txt (not committed, see
.gitignore), asks the model to pull out facts with quotes, then:
  - drops any fact whose quote isn't really in the document
  - runs a keyword scan for text aimed at automated reviewers
Writes extraction.json in the same shape as sample_extraction.json.

Usage: python extract.py   (needs ANTHROPIC_API_KEY in .env)
"""
import glob
import json
import os
import re

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()
MODEL = os.getenv("MODEL", "claude-sonnet-4-5")

FIELDS = json.load(open("fields.json"))
SYSTEM = open("prompt_system.txt").read()
USER_TEMPLATE = open("prompt_user.txt").read()

INJECTION_PATTERNS = [
    r"automated review", r"\bAI\b.*\b(rank|score)", r"ignore (all|previous|the above)",
    r"rank (it|this|us) first", r"full marks", r"pre-?approved",
]


def normalise(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def extract(letter, text):
    user = (USER_TEMPLATE
            .replace("{{FIELDS}}", json.dumps(FIELDS, indent=2))
            .replace("{{PROPOSAL_ID}}", letter)
            .replace("{{DOCUMENT}}", text))
    resp = client.messages.create(
        model=MODEL, max_tokens=2000, temperature=0,
        system=SYSTEM, messages=[{"role": "user", "content": user}],
    )
    data = json.loads(resp.content[0].text)

    # Code check 1: every quote must appear in the source text, otherwise
    # we treat the field as not found. Stops made-up facts getting scored.
    source = normalise(text)
    for name, f in data["fields"].items():
        if f["status"] != "not_found" and normalise(f.get("quote") or "") not in source:
            data["fields"][name] = {"value": None, "status": "not_found",
                                    "note": "model quote not found in document"}

    # Code check 2: keyword scan, independent of the model.
    keyword_hit = any(re.search(p, text, re.I) for p in INJECTION_PATTERNS)
    data["instructions_to_reviewer_found"] = bool(data.get("instructions_to_reviewer_found")) or keyword_hit
    data["model"] = MODEL
    return data


if __name__ == "__main__":
    out = {}
    for path in sorted(glob.glob("proposals/*.txt")):
        letter = os.path.splitext(os.path.basename(path))[0]
        out[letter] = extract(letter, open(path).read())
        print(letter, "done")
    json.dump(out, open("extraction.json", "w"), indent=2)
    print("Now run: python score.py extraction.json")
