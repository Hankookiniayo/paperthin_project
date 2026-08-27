#!/usr/bin/env python3
"""B2 — 영업중 전수를 EPSG:5174 → WGS84로 변환해 v0가 읽을 정적 파일로 굽는다.

좌표계는 B1(G-X)이 실측으로 확정했다: 155쌍·23구에서 5174 잔차 중앙값 6.2m,
2097 가정은 256.6m. 근거는 EVIDENCE.local.md 「G-X」.
변환을 브라우저가 아니라 여기서 하는 이유(B0 하위 결정): 변환식이 벤더 SDK 안에
숨지 않고 감사 가능한 곳에 남아야 G-X가 증명한 것이 유지된다.
"""
import json
from datetime import date
from pyproj import CRS, Transformer

DUMP  = "data/raw/LOCALDATA_072404.jsonl"
OUT   = "web/data/points.json"
TODAY = date(2026, 8, 27)

tf = Transformer.from_crs(CRS.from_epsg(5174), CRS.from_epsg(4326), always_xy=True)

rows, uptae_idx, uptae = [], {}, []
n_live = n_nocoord = n_nodate = 0
oldest = newest = None

with open(DUMP, encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        if r["TRDSTATENM"].strip() != "영업/정상":
            continue
        n_live += 1
        try:
            X, Y = float(r["X"]), float(r["Y"])
        except (ValueError, KeyError, TypeError):
            n_nocoord += 1
            continue
        if not (X and Y):
            n_nocoord += 1
            continue
        d = (r.get("APVPERMYMD") or "").strip()
        if len(d) < 10:
            n_nodate += 1
            continue
        apv = int(d[0:4] + d[5:7] + d[8:10])
        oldest = apv if oldest is None else min(oldest, apv)
        newest = apv if newest is None else max(newest, apv)
        lon, lat = tf.transform(X, Y)
        u = (r.get("UPTAENM") or "").strip()
        if u not in uptae_idx:
            uptae_idx[u] = len(uptae); uptae.append(u)
        parts = (r.get("SITEWHLADDR") or "").split()
        gu  = parts[1] if len(parts) > 1 else ""
        dong = parts[2] if len(parts) > 2 else ""
        rows.append([round(lon, 5), round(lat, 5), apv,
                     (r.get("BPLCNM") or "").strip(), uptae_idx[u], gu, dong])

import os
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({
        "generated": TODAY.isoformat(),
        "source": "서울열린데이터광장 LOCALDATA 일반음식점 인허가 (OA-16094)",
        "crs_in": "EPSG:5174", "crs_out": "EPSG:4326",
        "crs_note": "데이터셋 라벨은 EPSG:2097이나 실측 결과 5174다 (255m 차이). analysis/gx_datum.py",
        "fields": ["lon", "lat", "apv", "name", "uptae_i", "gu", "dong"],
        "uptae": uptae, "rows": rows,
    }, f, ensure_ascii=False, separators=(",", ":"))

print(f"영업중            {n_live:,}")
print(f"  좌표 없음/0     {n_nocoord:,}")
print(f"  인허가일 없음   {n_nodate:,}")
print(f"  → 출력          {len(rows):,}  ({len(rows)/n_live*100:.2f}% of 영업중)")
print(f"인허가일 범위     {oldest} ~ {newest}")
print(f"업태 종류         {len(uptae)}")
print(f"파일              {OUT}  {os.path.getsize(OUT)/1e6:.1f} MB")
