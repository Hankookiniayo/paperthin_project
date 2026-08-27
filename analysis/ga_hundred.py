#!/usr/bin/env python3
"""G-A — 나이 축의 타당성. 대장 인허가일이 실제 업력을 과소평가하는지 모순 검사로 잰다.

정답 소스: 소상공인시장진흥공단 「백년가게 지정리스트」 (data.go.kr 15132695, odcloud).
창업연도 필드가 없으므로 연도가 아니라 **지정 요건**을 쓴다 — 백년가게 지정 =
제3자가 업력 ≥ 30년을 인증했다는 뜻이다. 대장 나이 < 30년인 건이 모순이다.

판정 규약은 .re0/iteration/v0.2.0-fact-on-screen/EVIDENCE.local.md
「합격선 — G-A」에 측정 실행 전에 고정됐고 그 블록의 SHA-256(8d759975…)이
PREREG.md에 커밋돼 있다. 이 스크립트는 그 규약을 집행할 뿐 바를 정하지 않는다.
"""
import json, os, re, sys, urllib.parse, urllib.request, statistics as st
from datetime import date

DUMP = "data/raw/LOCALDATA_072404.jsonl"
UDDI = ("uddi:d4c7ac3f-f6c0-457f-9cde-9703b6bd8f66",
        "uddi:82fc1cc1-f636-46fc-ae0d-b1f2da5052b4")
ASOF = date(2026, 8, 27)      # 합격선 블록이 못 박은 기준일
BAR_YEARS = 30                # 백년가게 지정 요건 = 업력 ≥ 30년
N_MIN = 20                    # 표본 하한. 미달이면 판정 불능
PAREN = re.compile(r"\([^)]*\)")
WS = re.compile(r"\s+")


def norm_addr(a):
    """괄호 안은 버리고, 시도 표기를 통일하고, 공백을 모두 제거한다."""
    a = PAREN.sub(" ", a or "").strip()
    a = WS.sub("", a)
    if a.startswith("서울특별시"):
        a = "서울" + a[len("서울특별시"):]
    return a


def norm_name(n):
    return WS.sub("", PAREN.sub("", n or "")).strip()


def fetch_odcloud():
    key = urllib.parse.unquote(os.environ["TOUR_API_KEY_ENCODED"])
    base, ns = os.environ["ODCLOUD_BASE"], os.environ["ODCLOUD_NS_100YR"]
    rows = []
    for u in UDDI:
        page, got = 1, 0
        while True:
            q = urllib.parse.urlencode({"serviceKey": key, "page": page, "perPage": 1000})
            with urllib.request.urlopen(f"{base}/{ns}/{u}?{q}", timeout=60) as r:
                body = json.loads(r.read().decode("utf-8"))
            rows.extend(body["data"])
            got += body["currentCount"]
            print(f"  {u[-12:]} page {page}: {body['currentCount']}건 "
                  f"(누적 {got}/{body['totalCount']})", file=sys.stderr)
            if got >= body["totalCount"] or not body["currentCount"]:
                break
            page += 1
    return rows


def main():
    print("백년가게 지정리스트 수신 중…", file=sys.stderr)
    raw = fetch_odcloud()
    print(f"두 uddi 합계 {len(raw)}건", file=sys.stderr)

    # 1. (업체명, 업체주소) 기준 합집합·중복 제거
    uniq = {}
    for r in raw:
        uniq.setdefault((r.get("업체명"), r.get("업체주소")), r)
    print(f"중복 제거 후 {len(uniq)}건", file=sys.stderr)

    # 2. 서울만
    seoul = {k: v for k, v in uniq.items() if "서울" in (k[1] or "")}
    print(f"서울 소재 {len(seoul)}건", file=sys.stderr)

    # 정규화 키. 같은 키에 서로 다른 백년가게가 둘 이상이면 모호로 버린다
    want, amb = {}, set()
    for (nm, ad), v in seoul.items():
        k = (norm_addr(ad), norm_name(nm))
        if not k[0] or not k[1]:
            continue
        if k in want:
            amb.add(k)
        want[k] = v
    for k in amb:
        want.pop(k, None)
    print(f"정답 키 {len(want)}개 (모호 {len(amb)}개 제외)", file=sys.stderr)

    # 3. LOCALDATA 영업/정상과 매칭. 다대일·모호는 버린다
    hits, seen = {}, {}
    with open(DUMP, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["TRDSTATENM"].strip() != "영업/정상":
                continue
            k = (norm_addr(d.get("RDNWHLADDR")), norm_name(d.get("BPLCNM")))
            if k not in want:
                continue
            ymd = (d.get("APVPERMYMD") or "").strip()[:10]
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", ymd):
                continue
            if k in seen and seen[k] != ymd:      # 인허가일이 다른 레코드 둘 이상 → 모호
                hits.pop(k, None)
                continue
            seen[k] = ymd
            hits[k] = (ymd, d.get("UPTAENM", "").strip())

    n = len(hits)
    print(f"\n=== G-A 실측 (기준일 {ASOF}) ===")
    print(f"매칭 N = {n}   (표본 하한 N≥{N_MIN} → {'만족' if n >= N_MIN else '미달'})")
    if n < N_MIN:
        print("\n판정: **판정 불능** — 표본 하한 미달. 다른 독립 정답 소스를 찾는다.")
        print("미측정을 통과로 읽지 않는다.")
        _dump(hits)
        return

    # 4. 대장 나이
    rows = []
    for (ad, nm), (ymd, upt) in hits.items():
        y, m, dd = map(int, ymd.split("-"))
        age = (ASOF - date(y, m, dd)).days / 365.2425
        rows.append({"name": nm, "addr": ad, "apv": ymd, "uptae": upt,
                     "age": round(age, 1),
                     "floor": round(BAR_YEARS - age, 1) if age < BAR_YEARS else None})
    rows.sort(key=lambda r: r["age"])

    bad = [r for r in rows if r["floor"] is not None]
    print(f"모순 (대장 나이 < {BAR_YEARS}년): {len(bad)}건 / {n}건 = {len(bad)/n*100:.1f}%")

    if not bad:
        print("\n판정: **판정 불능 (0건 분기)** — 모순 0건은 「대장이 맞다」와")
        print("「소진공도 같은 인허가 대장으로 업력을 확인했다」를 구분하지 못한다.")
        print("0건을 대장이 정확하다는 근거로 쓰지 않는다.")
        _dump(rows)
        return

    fl = sorted(r["floor"] for r in bad)
    ages = sorted(r["age"] for r in rows)
    print(f"과소평가 하한: 중앙값 {st.median(fl):.1f}년   최대 {fl[-1]:.1f}년   "
          f"(p25 {fl[len(fl)//4]:.1f} / p75 {fl[3*len(fl)//4]:.1f})")
    print(f"매칭 전체 대장 나이: 중앙값 {st.median(ages):.1f}년  범위 {ages[0]:.1f}~{ages[-1]:.1f}년")

    print(f"\n모순 건 상위 15 (하한 큰 순):")
    hdr = f"{'하한(년)':>9}  {'대장나이':>8}  {'인허가':>10}  {'업태':<8} 상호"
    print(hdr); print("-" * 72)
    for r in sorted(bad, key=lambda r: -r["floor"])[:15]:
        print(f"{r['floor']:>9.1f}  {r['age']:>8.1f}  {r['apv']:>10}  {r['uptae'][:7]:<8} {r['name']}")

    print(f"\n판정: **모순 {len(bad)}건 확인.** 두 출처가 독립이라는 것과")
    print(f"대장이 노포를 과소평가한다는 것이 동시에 증명된다.")
    print(f"나이 축은 「영업 지속기간」이 아니라 「대장 등록 후 경과」다.")
    print(f"\n한계: 표본이 꼬리에 치우친다(오래된 집만 모은 목록). 모집단 전체의")
    print(f"오차 분포가 아니다. 이 측정이 답하는 것은 노포 구간의 과소평가 하한 하나다.")
    _dump(rows)


def _dump(rows):
    out = "analysis/ga_pairs.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in (rows if isinstance(rows, list) else
                  [{"addr": k[0], "name": k[1], "apv": v[0]} for k, v in rows.items()]):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n쌍 목록: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
