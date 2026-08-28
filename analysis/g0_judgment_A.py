#!/usr/bin/env python3
"""G0 판정 A — 미쉐린 서울 빕구르망 51곳의 지속기간 백분위.

매칭 규칙 (결과를 보기 전에 고정. 사전등록된 "매칭 실패분은 탈락이 아니라 별도 집계"의 구체화):
  - 공백·괄호 제거 후 **완전일치**만 채택. 부분일치는 오탐 위험이 커서 쓰지 않는다.
  - 완전일치 1건  → 판정 A 표본에 넣는다.
  - 완전일치 2건+ → 지점/동명업소이고 주소가 없어 특정 불가. **모호**로 별도 집계, 표본에서 제외.
  - 완전일치 0건  → **미매칭**으로 별도 집계. (일반음식점이 아닌 업태일 수 있다)
  - 합격선은 사전등록값 그대로: 중앙값 ≥ 65, N ≥ 25. 여기서 바꾸지 않는다.
"""
import json, re, statistics, sys

GOLDSET = "data/raw/g0_goldset_bib.txt"   # gitignore — 목록 재배포를 피한다

try:
    BIB = [l.strip() for l in open(GOLDSET, encoding="utf-8")
           if l.strip() and not l.startswith("#")]
except FileNotFoundError:
    sys.exit(f"정답셋이 없다: {GOLDSET}\n"
             "미쉐린 가이드 서울 빕구르망 목록을 한 줄에 하나씩 넣어야 한다.\n"
             "자동 수집은 불가하다(CloudFront WAF) — 사람이 브라우저에서 복사한다.\n"
             "이 파일을 커밋하지 않는 것은 의도다. README 「배지 제외 결정」 참고.")


norm = lambda s: re.sub(r"[\s()（）\[\]·.,'\"-]", "", s or "")
rows = [json.loads(l) for l in open("analysis/g0_ranked.jsonl", encoding="utf-8")]
idx = {}
for r in rows:
    idx.setdefault(norm(r["name"]), []).append(r)

print(f"정답셋 {len(BIB)}곳 / 검색 모집단(서울 일반음식점 영업중) {len(rows):,}\n")
matched, ambiguous, missing = [], [], []
for b in BIB:
    hits = idx.get(norm(b), [])
    if len(hits) == 1:   matched.append((b, hits[0]))
    elif len(hits) > 1:  ambiguous.append((b, hits))
    else:                missing.append(b)

print("=== 단일 매칭 (판정 A 표본) ===")
for b, h in sorted(matched, key=lambda x: x[1]["pct"]):
    print(f"  {b:16} {h['gu']:5} {h['uptae'][:6]:7} {h['days']/365.25:5.1f}년  백분위 {h['pct']:5.1f}")

print(f"\n=== 모호 (완전일치 2건 이상, 표본 제외) : {len(ambiguous)}곳 ===")
for b, hs in ambiguous:
    ps = sorted(h["pct"] for h in hs)
    print(f"  {b:16} {len(hs)}건  백분위 {['%.0f'%p for p in ps]}")

print(f"\n=== 미매칭 (표본 제외) : {len(missing)}곳 ===")
print("  " + ", ".join(missing))

pcts = [h["pct"] for _, h in matched]
print("\n" + "=" * 58)
print(f"판정 A 표본 N = {len(pcts)}   (사전등록 하한 N ≥ 25)")
if pcts:
    print(f"백분위 중앙값 = {statistics.median(pcts):.1f}   (무작위 = 50, 합격선 ≥ 65)")
    print(f"  평균 {statistics.mean(pcts):.1f} / 최소 {min(pcts):.1f} / 최대 {max(pcts):.1f}")
    print(f"  50 초과 {sum(1 for p in pcts if p>50)}곳 / 50 이하 {sum(1 for p in pcts if p<=50)}곳")
    ok_n, ok_m = len(pcts) >= 25, statistics.median(pcts) >= 65
    print(f"\n  N 요건      : {'충족' if ok_n else '미달 → 판정 불능'}")
    print(f"  중앙값 요건 : {'충족' if ok_m else '미달'}")
    print(f"\n  판정 A = {'합격' if (ok_n and ok_m) else ('불합격' if ok_n else '판정 불능')}")
