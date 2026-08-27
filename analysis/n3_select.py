#!/usr/bin/env python3
"""N-3 — 나이 축 가독 판정 대상 동 3곳을 사전등록 규칙으로 자동 선택한다.

규칙은 .re0/iteration/v0.2.0-fact-on-screen/EVIDENCE.local.md 「N-3 사전등록」에
화면을 보기 전에 고정돼 있다. 이 스크립트는 그 규칙을 집행할 뿐 고르지 않는다.
법정동은 (구, 동)으로 식별한다 — 동명이 여러 구에 있으므로 구 없이는 특정되지 않는다.
"""
import json, statistics as st
from datetime import date

DUMP  = "data/raw/LOCALDATA_072404.jsonl"
TODAY = date(2026, 8, 27)
MIN_N = 150          # 사전등록: 업소 수 ≥ 150

def tenure_years(s):
    s = (s or "").strip()
    if len(s) < 10:
        return None
    try:
        y, m, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
        return (TODAY - date(y, m, d)).days / 365.25
    except ValueError:
        return None

cells = {}
with open(DUMP, encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        if r["TRDSTATENM"].strip() != "영업/정상":
            continue
        t = tenure_years(r.get("APVPERMYMD"))
        if t is None or t < 0:
            continue
        parts = (r.get("SITEWHLADDR") or "").split()
        if len(parts) < 3:
            continue
        cells.setdefault((parts[1], parts[2]), []).append(t)

cand = {k: v for k, v in cells.items() if len(v) >= MIN_N}
print(f"영업중이 속한 법정동 {len(cells)}개 → 업소 수 ≥{MIN_N} 후보 {len(cand)}개")

def stats(v):
    q = st.quantiles(sorted(v), n=4)
    return st.median(v), q[2] - q[0]

rows = {k: (len(v), *stats(v)) for k, v in cand.items()}

def pick(keyfn, taken):
    # 동점이면 업소 수가 많은 쪽 (사전등록)
    return max((k for k in rows if k not in taken),
               key=lambda k: (keyfn(rows[k]), rows[k][0]))

sel, taken = {}, set()
for label, keyfn in (("오래된 상권", lambda r:  r[1]),
                     ("신흥",        lambda r: -r[1]),
                     ("혼합",        lambda r:  r[2])):
    k = pick(keyfn, taken); taken.add(k); sel[label] = k

print(f"\n{'범주':<12}{'법정동':<22}{'업소수':>7}{'영업기간 중앙값':>16}{'IQR':>9}")
print("-" * 72)
for label, k in sel.items():
    n, med, iqr = rows[k]
    print(f"{label:<12}{k[0]+' '+k[1]:<22}{n:>7}{med:>15.1f}년{iqr:>8.1f}년")

allmed = st.median([r[1] for r in rows.values()])
print(f"\n(후보 {len(cand)}개 동의 영업기간 중앙값들의 중앙값: {allmed:.1f}년 — 비교용)")
