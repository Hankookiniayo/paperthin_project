#!/usr/bin/env python3
"""B6 판정 B — 사람이 지명한 10곳이 핫플 레이어에서 보이는가.

규약: EVIDENCE.local.md 「합격선」(23ec3a66…) + 「합격선 보칙 — G-C′ 판정 B」(dddff130…).
  - 매칭: 공백 제거 후 부분 문자열 포함. `·` `/`는 대안으로 가른다(실행 전 고정).
  - 다대일이면 **하나라도 채워져 있으면 채워짐**.
  - 어디에도 안 붙으면 **「모집단에 없음」이고, 이것도 「비는 곳」으로 센다.**
  - **비는 곳 6곳 이상이면 판정 B 불합격 → G-C′ 전체 불합격.**

10곳은 커밋 4104e67에 실행 전 고정돼 있다. 이 스크립트는 규약을 집행할 뿐이다.
"""
import json, re

NAMED = ["성수동", "홍대", "강남역", "연남동", "을지로",
         "한남동", "잠실", "망원동", "용리단길", "압구정·도산공원"]
FAIL_AT = 6
WS = re.compile(r"\s+")
norm = lambda s: WS.sub("", s or "")

cov = json.load(open("analysis/b6_coverage.json", encoding="utf-8"))
filled, empty = set(cov["filled"]), set(cov["empty"])
pop = [a["name"] for a in json.load(open("data/seoul_areas.json", encoding="utf-8"))]

rows, n_bad = [], 0
for nm in NAMED:
    alts = [norm(x) for x in re.split(r"[·/]", nm) if x.strip()]
    hits = [p for p in pop if any(a in norm(p) for a in alts)]
    if not hits:
        verdict, why = "비는 곳", "모집단에 없음"
    elif any(h in filled for h in hits):
        verdict, why = "채워짐", ""
    else:
        verdict, why = "비는 곳", "결제 비었음"
    n_bad += verdict == "비는 곳"
    rows.append((nm, hits, verdict, why))

print("=== G-C′ 판정 B — 지명 10곳 (사전등록 규약 집행) ===\n")
print(f"{'지명':<14} {'판정':<8} {'사유':<12} 붙은 citydata 장소")
print("-" * 92)
for nm, hits, v, why in rows:
    mark = "○" if v == "채워짐" else "✗"
    print(f"{mark} {nm:<12} {v:<8} {why:<12} {', '.join(hits) if hits else '—'}")

print(f"\n비는 곳 {n_bad} / 10   (불합격선: {FAIL_AT}곳 이상)")
print(f"  ├ 결제 비었음   {sum(1 for r in rows if r[3]=='결제 비었음')}")
print(f"  └ 모집단에 없음 {sum(1 for r in rows if r[3]=='모집단에 없음')}")
b_ok = n_bad < FAIL_AT
print(f"\n**판정 B: {'합격' if b_ok else '불합격'}**")
print(f"**판정 A: 합격** (82/120 = 68.3%, 합격선 3.5%)")
print(f"\n=== G-C′ 전체: {'**합격**' if b_ok else '**불합격**'} ===")
print("두 판정을 모두 통과해야 합격이다." if b_ok else
      "판정 A가 통과해도 B가 불합격이면 전체 불합격이다 — 커버리지 숫자가 높아도\n"
      "보여주려는 곳에서 안 보이면 그 레이어는 필터가 아니다.\n"
      "→ 핫플 모드는 **필터가 아니라 북마크 레이어**다. 그렇게 부른다.\n"
      "→ 두 모드를 나란히 놓는 UI 설계(미해결 8번)가 무산된다. 나이 축은 영향받지 않는다.")
