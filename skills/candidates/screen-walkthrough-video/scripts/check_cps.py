#!/usr/bin/env python3
"""Report per-cue reading speed (characters/second) for an SRT.

Usage: check_cps.py path/to/file.srt [--warn 17] [--max 20]

Flags cues at/above --max as DENSE (tighten wording, never change timing) and
between --warn and --max as (tight). Target < 20 CPS, ideal ~17.
"""
import re, sys, argparse

def sec(x):
    h, m, r = x.split(":"); s, ms = r.split(",")
    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--warn", type=float, default=17.0)
    ap.add_argument("--max", type=float, default=20.0)
    a = ap.parse_args()

    t = open(a.srt, encoding="utf-8").read()
    cues = re.findall(r"(\d+)\n(\d\d:\d\d:\d\d,\d\d\d) --> (\d\d:\d\d:\d\d,\d\d\d)\n(.+(?:\n.+)*)", t)
    dense = 0
    print(f"{'#':>3} {'dur':>5} {'chars':>5} {'cps':>5}  text")
    for n, s, e, txt in cues:
        line = " ".join(l.strip() for l in txt.splitlines())
        d = sec(e) - sec(s)
        cps = len(line) / d if d > 0 else 999
        flag = ""
        if cps >= a.max:
            flag = " <== DENSE"; dense += 1
        elif cps >= a.warn:
            flag = " (tight)"
        print(f"{n:>3} {d:5.2f} {len(line):5d} {cps:5.1f}{flag}  {line[:48]}")
    print(f"\ncues={len(cues)}  dense(>= {a.max} cps)={dense}")
    sys.exit(1 if dense else 0)

if __name__ == "__main__":
    main()
