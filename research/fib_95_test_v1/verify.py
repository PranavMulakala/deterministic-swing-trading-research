"""Independent recount for test #11: QQQ 1-hour, 88.7%, 2 closes, both directions, written without the mirror
trick and without the shared helpers (own candle builder, own pivots, own move pairing).

  PYTHONPATH=src:. .venv/bin/python -m research.fib_95_test_v1.verify
"""
from __future__ import annotations

import json

from research.crt_sweep_test_v1.backtest import load


def hourly(days):
    out = []
    for date, bars in days.items():
        buckets = {}
        for b in bars:
            buckets.setdefault((b["m"] - 570) // 60, []).append(b)
        for k in sorted(buckets):
            g = buckets[k]
            start = 570 + 60 * k
            if g[-1]["m"] == start + 55 and start + 60 <= 960:
                out.append((max(x["h"] for x in g), min(x["l"] for x in g), g[-1]["c"]))
    return out


def count(c, direction):
    n = len(c)
    H = [x[0] for x in c]
    L = [x[1] for x in c]
    C = [x[2] for x in c]
    if direction == "up":
        is_top = lambda i: all(H[i] > H[j] for j in list(range(i - 5, i)) + list(range(i + 1, i + 6)))
        is_bot = lambda i: all(L[i] < L[j] for j in list(range(i - 5, i)) + list(range(i + 1, i + 6)))
    else:
        is_top = lambda i: all(L[i] < L[j] for j in list(range(i - 5, i)) + list(range(i + 1, i + 6)))
        is_bot = lambda i: all(H[i] > H[j] for j in list(range(i - 5, i)) + list(range(i + 1, i + 6)))
    result = {"reversal": 0, "continuation": 0, "ambiguous": 0, "unresolved": 0}
    pending = []
    for i in range(5, n - 5):
        bot, top = is_bot(i), is_top(i)
        if top:
            if pending:
                if direction == "up":
                    s = min(pending, key=lambda j: (L[j], -j))
                    start, end = L[s], H[i]
                    ok = end > start and (end - start) / start >= 0.01
                else:
                    s = min(pending, key=lambda j: (-H[j], -j))
                    start, end = H[s], L[i]
                    ok = end < start and (start - end) / start >= 0.01
                if ok:
                    lvl = end - 0.887 * (end - start)
                    t, streak, sig = i + 6, 0, None
                    while t < n:
                        if (direction == "up" and H[t] > end) or (direction == "down" and L[t] < end):
                            break
                        beyond = C[t] < lvl if direction == "up" else C[t] > lvl
                        streak = streak + 1 if beyond else 0
                        if streak >= 2:
                            sig = t
                            break
                        t += 1
                    if sig is not None:
                        out = "unresolved"
                        for j in range(sig + 1, min(sig + 121, n)):
                            rev = L[j] <= start if direction == "up" else H[j] >= start
                            cont = H[j] >= end if direction == "up" else L[j] <= end
                            if rev or cont:
                                out = "ambiguous" if rev and cont else "reversal" if rev else "continuation"
                                break
                        result[out] += 1
            pending = []
        if bot:   # added after the top check: a move runs from a low to a LATER high, never within one candle
            pending.append(i)
    return result


def main():
    c = hourly(load("QQQ"))
    up, down = count(c, "up"), count(c, "down")
    mine = {k: up[k] + down[k] for k in up}
    theirs = json.load(open("output/fib-95-test-results.json"))["combos"]["QQQ_1h"]["claim1"]["0.887"]["2"]
    same = all(mine[k] == theirs.get(k, 0) for k in mine)
    print(json.dumps({"independent": mine, "backtest": theirs, "match": same}, indent=1))


if __name__ == "__main__":
    main()
