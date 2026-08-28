#!/usr/bin/env python3
"""G-H — 축의 조준. 사전등록 블록 SHA-256 86ee451d… (PREREG.md).

나이 축이 인증 노포를 화면 상단에 올리는가.
판정 A: 인증 노포의 대장 나이 백분위 중앙값 >= 92.0
판정 B: 모집단 상위 100곳 중 인증 노포 >= 5곳
둘 다 통과해야 /hate의 root가 죽는다.
"""
import json, bisect, datetime, statistics, io

REF = datetime.date(2026, 8, 27)          # points.json generated와 동일
TOPN, LINE_A, LINE_B = 100, 92.0, 5

def age(apv):
    s = str(apv)
    d = datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return (REF - d).days / 365.25

pts = json.load(open("web/data/points.json"))
rows = pts["rows"]                          # [lon, lat, apv, name, uptae_i, gu, dong]
N = len(rows)
ages = sorted(age(r[2]) for r in rows)

# 인증 노포 = 백년가게 매칭 35 + 알려진 반례 3
certified = {}
for ln in io.open("analysis/ga_pairs.jsonl", encoding="utf-8"):
    p = json.loads(ln)
    certified[(p["name"].replace(" ", ""), str(p["apv"]).replace("-", ""))] = "백년가게"
for nm, apv in [("이문 설농탕", "19770521"), ("우래옥", "19880629"), ("은호식당", "19920304")]:
    certified.setdefault((nm.replace(" ", ""), apv), "알려진 반례")

# (name, apv) 완전일치. 다대일은 별도 집계하고 버리지 않는다.
hits = {}
for i, r in enumerate(rows):
    k = (r[3].replace(" ", ""), str(r[2]))
    if k in certified:
        hits.setdefault(k, []).append(i)

matched = {k: v for k, v in hits.items() if len(v) == 1}
multi   = {k: v for k, v in hits.items() if len(v) > 1}
missing = [k for k in certified if k not in hits]

def pct(a):                                  # 백분위 = (나이가 더 어린 수) / N * 100
    return bisect.bisect_left(ages, a) / N * 100

pcts = sorted((pct(age(rows[v[0]][2])), certified[k], k[0]) for k, v in matched.items())
med = statistics.median(p for p, _, _ in pcts)

top = sorted(range(N), key=lambda i: -age(rows[i][2]))[:TOPN]
top_keys = {(rows[i][3].replace(" ", ""), str(rows[i][2])) for i in top}
in_top = [k for k in certified if k in top_keys]

print(f"모집단 {N:,}행 · 기준일 {REF} · 인증 노포 {len(certified)}곳")
print(f"  단일 완전일치 {len(matched)} / 다대일 {len(multi)} / 미매칭 {len(missing)}")
print()
print(f"판정 A — 백분위 중앙값 {med:.1f} (합격선 >= {LINE_A})  "
      f"→ {'통과' if med >= LINE_A else '미달'}")
print(f"판정 B — 상위 {TOPN}곳 중 인증 노포 {len(in_top)}곳 (합격선 >= {LINE_B})  "
      f"→ {'통과' if len(in_top) >= LINE_B else '미달'}")
print()
print("인증 노포의 백분위 (낮은 순):")
for p, src, nm in pcts:
    print(f"  {p:6.2f}  {age(rows[matched[[k for k in matched if k[0]==nm][0]][0]][2]):5.1f}년  {nm} [{src}]")
print()
lo = age(rows[top[-1]][2])
print(f"상위 {TOPN}곳의 나이 하한 = {lo:.1f}년 (= 백분위 {pct(lo):.2f})")
print(f"상위 20곳: " + " · ".join(
    f"{rows[i][3]}({age(rows[i][2]):.0f}년,{rows[i][5]})" for i in top[:20]))
if multi:
    print("\n다대일 (판정에 안 들어감):", {k[0]: len(v) for k, v in multi.items()})
if missing:
    print("미매칭 (판정에 안 들어감):", [k[0] for k in missing])
