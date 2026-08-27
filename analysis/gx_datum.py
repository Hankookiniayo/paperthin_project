#!/usr/bin/env python3
"""G-X — LOCALDATA TM 좌표의 참 좌표계를 실측으로 정한다 (EPSG:2097 vs EPSG:5174).

정답 소스: 한국관광공사 TourAPI KorService2 (서울 음식점, WGS84 경위도).
매칭: 도로명주소 정규화 완전일치 AND 상호 완전일치. 다대일·모호는 버린다.
판정 규약은 .re0/iteration/v0.2.0-fact-on-screen/EVIDENCE.local.md 「측정 규약」에
측정 실행 전에 고정돼 있다. 이 스크립트는 그 규약을 집행할 뿐 바를 정하지 않는다.
"""
import json, os, re, sys, urllib.parse, urllib.request, statistics as st
from pyproj import CRS, Transformer, Geod

DUMP = "data/raw/LOCALDATA_072404.jsonl"
PAREN = re.compile(r"\([^)]*\)")
WS = re.compile(r"\s+")

def norm_addr(a):
    a = PAREN.sub(" ", a or "")
    a = WS.sub(" ", a).strip()
    return a

def norm_name(n):
    return WS.sub("", (n or "")).strip()

def fetch_tour():
    key = os.environ["TOUR_API_KEY_ENCODED"]; base = os.environ["TOUR_ENDPOINT"]
    out, page = [], 1
    while True:
        url = (f"{base}/areaBasedList2?serviceKey={key}&MobileOS=ETC&MobileApp=jjinmap"
               f"&_type=json&areaCode=1&contentTypeId=39&numOfRows=1000&pageNo={page}")
        with urllib.request.urlopen(url, timeout=30) as r:
            body = json.loads(r.read().decode("utf-8"))["response"]["body"]
        items = body.get("items") or {}
        rows = items.get("item") or []
        out.extend(rows)
        if len(out) >= int(body["totalCount"]) or not rows:
            break
        page += 1
    return out

def main():
    tour = fetch_tour()
    print(f"TourAPI 서울 음식점 수신: {len(tour)}건", file=sys.stderr)

    # (정규화주소, 정규화상호) -> WGS84. 같은 키가 둘 이상이면 모호로 표시해 버린다.
    truth, dup = {}, set()
    for t in tour:
        x, y = t.get("mapx"), t.get("mapy")
        if not x or not y:
            continue
        k = (norm_addr(t.get("addr1")), norm_name(t.get("title")))
        if not k[0] or not k[1]:
            continue
        if k in truth and truth[k] != (float(x), float(y)):
            dup.add(k)
        truth[k] = (float(x), float(y))
    for k in dup:
        truth.pop(k, None)
    print(f"정답 키 {len(truth)}개 (모호 {len(dup)}개 제외)", file=sys.stderr)

    # LOCALDATA 영업중에서 같은 키를 찾는다. 다대일이면 버린다.
    hits, seen = {}, set()
    with open(DUMP, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["TRDSTATENM"].strip() != "영업/정상":
                continue
            k = (norm_addr(d.get("RDNWHLADDR")), norm_name(d.get("BPLCNM")))
            if k not in truth:
                continue
            try:
                X, Y = float(d["X"]), float(d["Y"])
            except (ValueError, KeyError, TypeError):
                continue
            if k in seen:              # 같은 키에 LOCALDATA 레코드가 둘 이상 → 모호
                hits.pop(k, None)
                continue
            seen.add(k)
            hits[k] = (X, Y)
    print(f"매칭쌍: {len(hits)}", file=sys.stderr)
    if not hits:
        sys.exit("매칭 0건 — 정규화 규칙을 다시 본다. 판정하지 않는다.")

    geod = Geod(ellps="WGS84")
    tf = {c: Transformer.from_crs(CRS.from_epsg(c), CRS.from_epsg(4326), always_xy=True)
          for c in (2097, 5174)}

    rows = []
    for k, (X, Y) in hits.items():
        tlon, tlat = truth[k]
        r = {"addr": k[0], "name": k[1], "gu": k[0].split()[1] if len(k[0].split()) > 1 else "?"}
        for c in (2097, 5174):
            lon, lat = tf[c].transform(X, Y)
            r[c] = (lon, lat)
            r[f"d{c}"] = geod.inv(lon, lat, tlon, tlat)[2]
        r["gap"] = geod.inv(*r[2097], *r[5174])[2]   # 두 가설 사이의 거리 = 어긋남의 크기
        rows.append(r)

    gus = sorted({r["gu"] for r in rows})
    print(f"\n=== G-X 실측 (N={len(rows)}, 구 {len(gus)}개) ===")
    print(f"구: {' '.join(gus)}\n")
    hdr = f"{'가설':<10}{'중앙값(m)':>12}{'IQR(m)':>10}{'p10':>9}{'p90':>9}{'IQR<중앙값':>12}"
    print(hdr); print("-" * len(hdr.replace('가설','xx').replace('중앙값(m)','xxxxxxxx')))
    verdict = {}
    for c in (2097, 5174):
        ds = sorted(r[f"d{c}"] for r in rows)
        q1, q3 = st.quantiles(ds, n=4)[0], st.quantiles(ds, n=4)[2]
        med, iqr = st.median(ds), q3 - q1
        p10 = ds[int(.10 * len(ds))]; p90 = ds[int(.90 * len(ds))]
        verdict[c] = (med, iqr)
        print(f"EPSG:{c:<5}{med:>12.1f}{iqr:>10.1f}{p10:>9.1f}{p90:>9.1f}{'예' if iqr < med else '아니오':>12}")

    gaps = sorted(r["gap"] for r in rows)
    print(f"\n두 가설 사이의 거리(= 미해결 4번이 묻는 어긋남): "
          f"중앙값 {st.median(gaps):.1f}m  범위 {gaps[0]:.1f}~{gaps[-1]:.1f}m")

    win = min(verdict, key=lambda c: verdict[c][0])
    med, iqr = verdict[win]
    print(f"\n채택 조건 1 (중앙값 작은 쪽): EPSG:{win}  ({med:.1f}m vs "
          f"{verdict[2097 if win==5174 else 5174][0]:.1f}m)")
    ok2 = iqr < med
    print(f"채택 조건 2 (IQR < 중앙값 → 일관): IQR {iqr:.1f}m vs 중앙값 {med:.1f}m → "
          f"{'만족' if ok2 else '불만족'}")
    print(f"표본 하한 (N≥30, 구≥3): N={len(rows)}, 구={len(gus)} → "
          f"{'만족' if len(rows)>=30 and len(gus)>=3 else '불만족'}")
    print(f"\n판정: {'EPSG:'+str(win)+' 채택' if ok2 and len(rows)>=30 and len(gus)>=3 else '판정 보류 — 변환식 확정 안 함, 핀 안 찍음'}")

    with open("analysis/gx_pairs.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({k: v for k, v in r.items() if not isinstance(v, tuple)},
                               ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
