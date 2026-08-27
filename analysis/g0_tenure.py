#!/usr/bin/env python3
"""G0 — 영업 지속기간 신호의 타당성 측정.
합격선은 EVIDENCE.local.md에 사전등록(해시 a44996a4…)되어 있다. 여기서 바꾸지 않는다.

절차 (결과를 보기 전 확정):
  1. 영업중(TRDSTATENM='영업/정상')만 남긴다.
  2. 구 = 주소에서 추출. 업태 = UPTAENM.
  3. 영업기간 = APVPERMYMD → AS_OF.
  4. 백분위는 (구, 업태) 셀 안에서. 셀 n < MIN_CELL 이면 구 전체로 폴백,
     구 전체도 미달이면 서울 전체로 폴백. (미해결 2번 교란을 결과에 섞지 않기 위함)
  5. 판정 B용: 상위 5%에서 고정시드 무작위 30곳.
"""
import json, os, re, sys, random, datetime, collections, statistics

AS_OF    = datetime.date(2026, 8, 27)
MIN_CELL = 30
SEED     = 20260827
HERE     = os.path.dirname(os.path.abspath(__file__))
SRC      = os.path.join(HERE, "..", "data", "raw", "LOCALDATA_072404.jsonl")

GU = re.compile(r"서울특별시\s+(\S+?구)\s")

def gu_of(r):
    for f in ("SITEWHLADDR", "RDNWHLADDR"):
        m = GU.search((r.get(f) or "") + " ")
        if m:
            return m.group(1)
    return None

def days(s):
    s = (s or "").strip()
    if len(s) < 10:
        return None
    try:
        d = datetime.date.fromisoformat(s[:10])
    except ValueError:
        return None
    if not (1900 < d.year <= AS_OF.year + 1) or d > AS_OF:
        return None
    return (AS_OF - d).days

def load():
    open_, skipped = [], collections.Counter()
    for line in open(SRC, encoding="utf-8"):
        r = json.loads(line)
        if r.get("TRDSTATENM", "").strip() != "영업/정상":
            skipped["폐업등"] += 1; continue
        g, t = gu_of(r), (r.get("UPTAENM") or "").strip()
        d = days(r.get("APVPERMYMD"))
        if not g:   skipped["구파싱실패"] += 1; continue
        if not t:   skipped["업태없음"]  += 1; continue
        if d is None: skipped["일자불량"] += 1; continue
        open_.append({"name": (r.get("BPLCNM") or "").strip(), "gu": g, "uptae": t,
                      "days": d, "addr": (r.get("SITEWHLADDR") or "").strip(),
                      "rdn": (r.get("RDNWHLADDR") or "").strip(),
                      "mgtno": r.get("MGTNO"), "area": r.get("SITEAREA")})
    return open_, skipped

def rank(rows):
    """셀 안에서 백분위(0~100). 높을수록 오래 버팀."""
    cells = collections.defaultdict(list)
    for r in rows:
        cells[(r["gu"], r["uptae"])].append(r)
        cells[(r["gu"], None)].append(r)
        cells[(None, None)].append(r)
    sorted_days = {k: sorted(x["days"] for x in v) for k, v in cells.items()}
    import bisect
    for r in rows:
        for key, lvl in (((r["gu"], r["uptae"]), "구+업태"),
                         ((r["gu"], None), "구"),
                         ((None, None), "서울")):
            arr = sorted_days[key]
            if len(arr) >= MIN_CELL or lvl == "서울":
                lo = bisect.bisect_left(arr, r["days"]); hi = bisect.bisect_right(arr, r["days"])
                r["pct"] = 100.0 * ((lo + hi) / 2) / len(arr)
                r["cell"] = lvl; r["cell_n"] = len(arr)
                break
    return rows

def main():
    rows, skipped = load()
    print(f"영업중 표본 N = {len(rows):,}")
    print("제외:", dict(skipped))
    rank(rows)
    yrs = [r["days"] / 365.25 for r in rows]
    q = statistics.quantiles(yrs, n=100)
    print(f"\n영업기간(년)  중앙값 {statistics.median(yrs):.1f}  "
          f"p75 {q[74]:.1f}  p90 {q[89]:.1f}  p95 {q[94]:.1f}  최대 {max(yrs):.1f}")
    print("셀 수준 분포:", dict(collections.Counter(r["cell"] for r in rows)))
    print("\n상위 업태 10:", [f"{k}({v:,})" for k, v in collections.Counter(r["uptae"] for r in rows).most_common(10)])

    top = [r for r in rows if r["pct"] >= 95]
    print(f"\n상위 5% 모집단 = {len(top):,}곳")
    print("상위 5%의 업태 구성:", [f"{k}({v})" for k, v in collections.Counter(r["uptae"] for r in top).most_common(12)])

    random.seed(SEED)
    sample = random.sample(top, 30)
    out = os.path.join(HERE, "g0_judgment_B_sample.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# G0 판정 B — 상위 5% 무작위 30곳 (육안 검사용)\n\n")
        f.write(f"모집단 {len(top):,}곳 중 seed={SEED}로 30곳. 기준일 {AS_OF}.\n\n")
        f.write("**판정**: \"이 집 때문에 이동할 만한가\"가 명백히 아닌 곳이 **과반(16곳 이상)이면 불합격.**\n\n")
        f.write("| # | 상호 | 구 | 업태 | 영업기간 | 백분위 | 주소 | 판정 |\n|---|---|---|---|---|---|---|---|\n")
        for i, r in enumerate(sorted(sample, key=lambda x: -x["days"]), 1):
            f.write(f"| {i} | {r['name']} | {r['gu']} | {r['uptae']} | {r['days']/365.25:.0f}년 "
                    f"| {r['pct']:.1f} | {(r['rdn'] or r['addr'])[:40]} |  |\n")
    print(f"\n판정 B 표본 → {out}")

    with open(os.path.join(HERE, "g0_ranked.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("전체 랭킹 → analysis/g0_ranked.jsonl (판정 A에서 정답셋 조회에 사용)")

main()
