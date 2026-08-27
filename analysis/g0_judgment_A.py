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

BIB = """능동미나리 황금콩밭 알트에이 소바키리스즈 서령 미진 유림면 유한 오일제 안덕
고사리익스프레스 역전회관 안암 용금옥 필동면옥 황생가칼국수 대성집 할매집 개성만두궁
호라파 금돼지식당 우래옥 자하손만두 정면 게방식당 곰탕랩 니시무라멘 합정옥 스바루
미필담 베이스이즈나이스 마포옥 3대삼계장인 정인면옥 사루카메 서교난면방 면서울 꿉당
옥동식 교다이야 진진 담택 오레노라멘 삼청동수제비 만두집 양양메밀막국수 맷돌
임병주산동칼국수 화해당 계월 옥돌현옥""".split()

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
