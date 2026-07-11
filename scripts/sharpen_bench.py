"""
Sharpen benchmark — the wrapper-killer proof, in one number.

Runs a fixed question set twice through the SAME infused brain:
  RAW       = one plain model call (a "wrapper" would stop here).
  SHARPENED = ILLIP's draft -> critique -> refine loop around that same model.

Then prints an accuracy score for each. If SHARPENED > RAW, the lift came from
ILLIP's loop, not the model — which is exactly the thing a wrapper cannot do.

Scoring is deterministic and offline: each question ships required keywords; a
answer scores 1.0 only if it contains all of them (case-insensitive). Crude on
purpose — no judge model, no network, reproducible on any machine.

Run:  python scripts/sharpen_bench.py
      python scripts/sharpen_bench.py --rounds 2
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# "Partial-miss" tasks: ones a strong small model still commonly gets subtly
# wrong or incomplete on the FIRST pass — the exact place a self-critique earns
# its keep. Easy trivia has no headroom (the model's already right, so the loop
# can't lift it); these have headroom. Keywords are chosen so the common WRONG
# answer does not accidentally contain them (collision-safe scoring).
CASES = [
    {
        # Century rule is the classic omission: models write %4 and forget %100/%400.
        "q": "Write a Python function is_leap(year) that returns True for leap years. It MUST handle century years correctly (1900 is NOT a leap year, 2000 IS). Return only the code.",
        "must": ["def", "400", "100"],
    },
    {
        # Common wrong answer: 'git reset --hard' (loses work) or 'git revert'.
        "q": "Give the single git command to undo the most recent commit while KEEPING its changes staged in the index. Command only.",
        "must": ["--soft"],
    },
    {
        # Bat-and-ball. Intuitive-but-wrong answer is 0.10; correct is 0.05.
        "q": "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost? Give the amount in dollars as a decimal.",
        "must": ["0.05"],
    },
    {
        # Relational trap. Wrong answer is 2; Sally is herself the other sister -> 1.
        "q": "Sally has 3 brothers. Each of her brothers has 2 sisters. How many sisters does Sally have? Give the number only.",
        "must": ["1"],
    },
    {
        # Letter-count: models routinely answer 2. Correct is 3.
        "q": "How many times does the letter 'r' appear in the word 'strawberry'? Give the number only.",
        "must": ["3"],
    },
    {
        # 2nd-highest salary. First pass often forgets DISTINCT or uses MAX wrongly.
        "q": "Write a SQL query to select the second highest DISTINCT salary from a table Employee(salary). It must still work when the salaries have duplicates. Query only.",
        "must": ["DISTINCT"],
    },
    {
        # Order of operations. Wrong answer 16; correct 4.
        "q": "Evaluate 12 - 4 * 2 using standard order of operations. Give the number only.",
        "must": ["4"],
    },
    {
        # Reverse linked list — first pass often omits the empty-list guard mention.
        "q": "In one sentence, what edge case must a function that reverses a singly linked list handle besides a normal multi-node list? Name the case explicitly.",
        "must": ["empty"],
    },
]


def score(answer: str, must: list[str]) -> float:
    a = (answer or "").lower()
    hit = sum(1 for k in must if k.lower() in a)
    return hit / len(must)


async def main(rounds: int):
    from app.services.chat_service import get_llm
    from app.services.sharpener import sharpen
    from app.providers import get_provider

    provider = await get_provider()
    llm = get_llm()
    print(f"Brain infused: {provider.name}\n")
    print(f"{'#':>2}  {'RAW':>5}  {'SHARP':>5}  question")
    print("-" * 72)

    raw_total = sharp_total = 0.0
    t0 = time.time()
    for i, case in enumerate(CASES, 1):
        raw = await llm.complete(case["q"])
        res = await sharpen(case["q"], rounds=rounds, ground=False)
        rs = score(raw, case["must"])
        ss = score(res.answer, case["must"])
        raw_total += rs
        sharp_total += ss
        flag = "↑" if ss > rs else ("↓" if ss < rs else " ")
        print(f"{i:>2}  {rs*100:>4.0f}%  {ss*100:>4.0f}% {flag} {case['q'][:44]}")

    n = len(CASES)
    raw_pct = raw_total / n * 100
    sharp_pct = sharp_total / n * 100
    dt = time.time() - t0
    print("-" * 72)
    print(f"    RAW accuracy      : {raw_pct:5.1f}%")
    print(f"    SHARPENED accuracy: {sharp_pct:5.1f}%")
    delta = sharp_pct - raw_pct
    verdict = "LIFT" if delta > 0 else ("no change" if delta == 0 else "REGRESSION")
    print(f"    Delta             : {delta:+5.1f} pts  [{verdict}]")
    print(f"    ({n} questions, rounds={rounds}, {dt:.0f}s total)")
    if delta > 0:
        print("\n  ILLIP's loop lifted the SAME brain. That lift is the product, not the model.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=1, help="critique+refine cycles (1-3)")
    args = ap.parse_args()
    asyncio.run(main(max(1, min(args.rounds, 3))))
