#!/usr/bin/env python3
"""B6 판정 A + G-N — 두 슬롯을 합쳐 사전등록 규약대로 판정한다.

규약: EVIDENCE.local.md 「합격선」(SHA-256 23ec3a66…, PREREG.md 45ad219).
  절차 3: 두 슬롯 중 **한 번이라도** 채워졌으면 「채워짐」. 관대함은 합격 쪽으로
          기울므로 불합격 판정을 보수적으로 만든다.
  판정 A: 채워진 장소 수 ÷ citydata 장소 전수 ≥ 3.5%.
  판정 B: 사람이 지명한 10곳 필요 — 이 스크립트는 하지 않는다.

이 스크립트는 규약을 집행할 뿐 바를 정하지 않는다.
"""
import json, glob, collections, sys

BAR = 0.035
POP = json.load(open("data/seoul_areas.json", encoding="utf-8"))


def blk(r):
    s = (r.get("body") or {}).get("LIVE_CMRCL_STTS")
    if isinstance(s, list):
        s = s[0] if s else None
    return s


def load(n):
    f = sorted(glob.glob(f"data/raw/cmrcl_slot{n}_*.jsonl"))
    if not f:
        sys.exit(f"슬롯 {n} 없음")
    rows = [json.loads(l) for l in open(f[-1], encoding="utf-8")]
    return f[-1], {r["name"]: r for r in rows}


f1, s1 = load(1)
f2, s2 = load(2)
print(f"슬롯1 {f1.split('_')[-1][:-6]}  슬롯2 {f2.split('_')[-1][:-6]}", file=sys.stderr)

filled, empty, per = {}, [], {}
for a in POP:
    nm = a["name"]
    got = []
    for tag, s in (("s1", s1), ("s2", s2)):
        r = s.get(nm)
        b = blk(r) if r else None
        got.append(bool(b and b.get("CMRCL_RSB")))
    per[nm] = got
    (filled if any(got) else empty).__setitem__(nm, got) if any(got) else empty.append(nm)

n_pop, n_fill = len(POP), len(filled)
cov = n_fill / n_pop
print(f"\n=== G-C′ 판정 A (사전등록 규약) ===")
print(f"모집단(citydata 전수)      {n_pop}")
print(f"채워짐 (두 슬롯 중 한 번이라도) {n_fill}")
print(f"비어 있음                  {len(empty)}")
print(f"커버리지                   {n_fill}/{n_pop} = {cov*100:.1f}%   합격선 {BAR*100:.1f}%")
print(f"판정 A: {'**합격**' if cov >= BAR else '**불합격**'}  ({cov/BAR:.1f}배)")

both = sum(1 for v in per.values() if all(v))
only1 = sum(1 for v in per.values() if v[0] and not v[1])
only2 = sum(1 for v in per.values() if v[1] and not v[0])
print(f"\n슬롯 일치성: 두 슬롯 다 채워짐 {both} / 슬롯1만 {only1} / 슬롯2만 {only2} / 둘 다 빔 {len(empty)}")
if only1 == 0 and only2 == 0:
    print("→ **같은 장소가 두 시간대에 같은 답을 냈다. 결측이 구조적이다** (일시적 장애 아님).")
else:
    print("→ ⚠️ 슬롯마다 다른 장소가 있다. 결측이 전부 구조적이지는 않다.")

print(f"\n=== G-N — 분류 우주 (장소 × 시간대) ===")
lrg, mid, by_slot = set(), set(), {}
for tag, s in (("s1", s1), ("s2", s2)):
    L, M = set(), set()
    for r in s.values():
        b = blk(r)
        for e in (b or {}).get("CMRCL_RSB") or []:
            L.add(e["RSB_LRG_CTGR"]); M.add((e["RSB_LRG_CTGR"], e["RSB_MID_CTGR"]))
    by_slot[tag] = (L, M); lrg |= L; mid |= M
    print(f"  {tag}: 대분류 {len(L)} · 중분류 {len(M)}")
print(f"  합집합: 대분류 {len(lrg)} · 중분류 {len(mid)}")
newm = by_slot["s2"][1] - by_slot["s1"][1]
gone = by_slot["s1"][1] - by_slot["s2"][1]
print(f"  슬롯2에서 새로 나온 중분류: {sorted(m[1] for m in newm) or '없음'}")
print(f"  슬롯2에서 사라진 중분류:   {sorted(m[1] for m in gone) or '없음'}")
print(f"\nG-N 합격선: 장소 ≥3 × 시간대 ≥2 → 장소 {n_fill} · 시간대 2 → "
      f"{'**만족**' if n_fill >= 3 else '미달'}")
for l in sorted(lrg):
    print(f"  {l:<10} {', '.join(sorted(m[1] for m in mid if m[0]==l))}")

json.dump({"filled": sorted(filled), "empty": sorted(empty), "per": per},
          open("analysis/b6_coverage.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n비는 장소 목록은 analysis/b6_coverage.json 에만 있다 — 판정 B의 10곳 지명 전까지 공개하지 않는다.",
      file=sys.stderr)
