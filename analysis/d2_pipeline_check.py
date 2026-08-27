#!/usr/bin/env python3
"""D2 — 화면이 실제로 읽는 파일을 정답과 대조한다 (파이프라인 검산).

B1(G-X)이 잰 것은 **변환식**이고, 155쌍짜리 실험 스크립트 안에서였다.
D2가 재는 것은 **산출물** — web/data/points.json — 이다. 둘은 다르다:
변환식이 옳아도 build_points.py가 축을 뒤집거나 자리를 잘못 자르면 여기서 갈린다.
WORKFLOW D2: "수치가 맞는데 핀이 엉뚱한 데 있으면 변환식이 아니라 파이프라인이 틀렸다."

정답: 한국관광공사 TourAPI KorService2 (WGS84). 매칭 규칙은 gx_datum.py와 같다.
"""
import json, os, re, sys, urllib.request, statistics as st
from pyproj import Geod

PAREN = re.compile(r"\([^)]*\)")
WS = re.compile(r"\s+")
norm_addr = lambda a: WS.sub(" ", PAREN.sub(" ", a or "")).strip()
norm_name = lambda n: WS.sub("", (n or "")).strip()


def fetch_tour():
    key, base = os.environ["TOUR_API_KEY_ENCODED"], os.environ["TOUR_ENDPOINT"]
    out, page = [], 1
    while True:
        url = (f"{base}/areaBasedList2?serviceKey={key}&MobileOS=ETC&MobileApp=jjinmap"
               f"&_type=json&areaCode=1&contentTypeId=39&numOfRows=1000&pageNo={page}")
        with urllib.request.urlopen(url, timeout=30) as r:
            b = json.loads(r.read().decode("utf-8"))["response"]["body"]
        rows = (b.get("items") or {}).get("item") or []
        out.extend(rows)
        if len(out) >= int(b["totalCount"]) or not rows:
            return out
        page += 1


truth, dup = {}, set()
for t in fetch_tour():
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
print(f"TourAPI 정답 키 {len(truth)}개 (모호 {len(dup)} 제외)", file=sys.stderr)

# 화면이 읽는 바로 그 파일. LOCALDATA 덤프가 아니다.
pts = json.load(open("web/data/points.json", encoding="utf-8"))
F = pts["fields"]
iLon, iLat, iNm, iGu, iDo = (F.index(c) for c in ("lon", "lat", "name", "gu", "dong"))
print(f"points.json: {len(pts['rows']):,}행  crs_in={pts['crs_in']}  기준일={pts['generated']}",
      file=sys.stderr)

# points.json에는 도로명주소가 없다(지번만 gu/dong). 상호로 후보를 잡고,
# 같은 상호가 둘 이상이면 모호로 버린다 — gx_datum과 같은 보수성.
by_name = {}
for r in pts["rows"]:
    by_name.setdefault(norm_name(r[iNm]), []).append(r)

geod = Geod(ellps="WGS84")
rows = []
miss = ambig = 0
for (addr, name), (tlon, tlat) in truth.items():
    c = by_name.get(name)
    if not c:
        miss += 1; continue
    if len(c) > 1:
        ambig += 1; continue
    r = c[0]
    rows.append({"name": name, "gu": r[iGu], "dong": r[iDo],
                 "lon": r[iLon], "lat": r[iLat],
                 "d": geod.inv(r[iLon], r[iLat], tlon, tlat)[2]})

print(f"\n=== D2 파이프라인 검산 (정답 {len(truth)} → 매칭 {len(rows)}, "
      f"상호없음 {miss} / 동명이인 {ambig}) ===")
if not rows:
    sys.exit("매칭 0건 — 판정하지 않는다.")

ds = sorted(r["d"] for r in rows)
gus = sorted({r["gu"] for r in rows})
q = st.quantiles(ds, n=4)
print(f"정답과의 거리(m): 중앙값 {st.median(ds):.1f}  p25 {q[0]:.1f}  p75 {q[2]:.1f}  "
      f"p90 {ds[int(.9*len(ds))]:.1f}  최대 {ds[-1]:.1f}")
print(f"구 {len(gus)}개: {' '.join(gus)}")
for bar in (10, 25, 50, 100, 255):
    print(f"  ≤{bar:>4}m: {sum(1 for d in ds if d <= bar):>4} / {len(ds)} "
          f"({sum(1 for d in ds if d <= bar)/len(ds)*100:.1f}%)")

# B1이 낸 것과 같은 말을 하는가. 다르면 파이프라인이 틀렸다.
med = st.median(ds)
print(f"\nB1(G-X) 5174 잔차 중앙값 6.2m vs D2 산출물 중앙값 {med:.1f}m")
if med < 25:
    print("→ **일치. 파이프라인 통과.** 변환식이 전수에 그대로 적용됐다.")
elif med > 200:
    print("→ **불일치 — 255m대. 산출물이 2097로 변환됐거나 변환이 안 됐다.**")
else:
    print("→ **불일치. 변환식은 맞는데 산출물이 어긋난다 — 파이프라인 문제다.**")

print(f"\n가장 먼 10건 (파이프라인 오류라면 여기 몰린다):")
for r in sorted(rows, key=lambda r: -r["d"])[:10]:
    print(f"  {r['d']:>8.1f}m  {r['gu']} {r['dong']:<10} {r['name']}")

json.dump(rows, open("analysis/d2_pairs.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
