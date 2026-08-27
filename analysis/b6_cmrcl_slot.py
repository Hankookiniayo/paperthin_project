#!/usr/bin/env python3
"""B6 — 결제 블록 실측. 한 슬롯을 전수 호출해 원본을 그대로 저장한다.

모집단: data/seoul_areas.json (citydata 장소 120곳). 전수, 추출 없음.
엔드포인트는 `citydata_cmrcl` — 결제 블록만 준다. 전체 `citydata`를 안 쓰는 것은
나머지 16블록을 **받지 않기 위해서**다 (WORKFLOW B6: 응답에 있다는 것은 쓸 이유가 아니다).

이 스크립트는 판정하지 않는다. 슬롯 하나를 받아 적을 뿐이다.
판정은 서로 다른 갱신 슬롯 2회가 모인 뒤 b6_judge.py가 한다.
사용: python analysis/b6_cmrcl_slot.py <슬롯번호>
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime

AREAS = "data/seoul_areas.json"


def main():
    slot = sys.argv[1] if len(sys.argv) > 1 else "1"
    key, base = os.environ["SEOUL_API_KEY"], os.environ["SEOUL_ENDPOINT"]
    areas = json.load(open(AREAS, encoding="utf-8"))
    stamp = datetime.now().strftime("%Y%m%dT%H%M")
    out = f"data/raw/cmrcl_slot{slot}_{stamp}.jsonl"

    ok = err = 0
    with open(out, "w", encoding="utf-8") as f:
        for i, a in enumerate(areas, 1):
            url = f"{base}/{key}/json/citydata_cmrcl/1/5/{urllib.parse.quote(a['name'])}"
            rec = {"code": a["code"], "name": a["name"],
                   "fetched_at": datetime.now().isoformat(timespec="seconds")}
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    rec["body"] = json.loads(r.read().decode("utf-8"))
                ok += 1
            except Exception as e:                      # noqa: BLE001 — 실패도 기록한다
                rec["error"] = f"{type(e).__name__}: {e}"
                err += 1
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 20 == 0:
                print(f"  {i}/{len(areas)}  ok={ok} err={err}", file=sys.stderr)
            time.sleep(0.15)

    print(f"슬롯 {slot} 저장: {out}  ({ok} ok / {err} err / 전수 {len(areas)})")


if __name__ == "__main__":
    main()
