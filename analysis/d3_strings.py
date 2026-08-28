#!/usr/bin/env python3
"""D3 — 화면 문자열 전수 추출 + G-V 3항(등급 0개) 기계 대조.

G-V 규약: "없음"을 선언으로 적지 않는다. 3항은 **전수 목록으로 보이는 것**이다.
이 스크립트가 목록을 만든다. 1·2항(역추적·한계 노출)의 판정은 사람이 목록을 보고 한다 —
기계가 "되짚어진다"를 판정할 수 없다.
"""
import re, sys
from html.parser import HTMLParser

BAN = ["찐", "추천", "베스트", "best", "순위", "랭킹", "1위", "top",
       "좋은", "맛있", "맛집", "등급", "별점", "평점", "점수", "인증", "선정"]
ALLOW = {  # 부정문·출처명 안에서 쓰인 금지어는 사람이 확인 후 여기에 사유와 함께 남긴다
    "좋은 순이 아니다": "부정문 — 등급을 붙이지 않는다는 선언 자체",
    "오래된 순. 좋은 순이 아니다.": "부정문",
    "등급도 순위도 없다": "부정문 — B4 표(측정 전 고정)가 승인한 「좋은 순이 아니다」와 같은 부류. "
                        "3항이 금하는 것은 등급 라벨이지 등급의 부재를 말하는 문장이 아니다.",
}


class T(HTMLParser):
    def __init__(self):
        super().__init__(); self.out = []; self.skip = 0; self.tag = None
    def handle_starttag(self, t, a):
        d = dict(a)
        if t in ("script", "style"):
            self.skip += 1
        self.tag = t
        if t == "input" and d.get("placeholder"):
            self.out.append(("placeholder", d["placeholder"]))
        if t == "a" and d.get("href"):
            self.out.append(("링크 href", d["href"]))
    def handle_endtag(self, t):
        if t in ("script", "style"):
            self.skip = max(0, self.skip - 1)
    def handle_data(self, d):
        if self.skip:
            return
        d = re.sub(r"\s+", " ", d).strip()
        if d:
            self.out.append(("텍스트" if self.tag != "title" else "title", d))


src = open("web/index.html", encoding="utf-8").read()
p = T(); p.feed(src)

# 스크립트 안의 사용자 노출 문자열(팝업 템플릿 등)은 따로 뽑는다 — 화면에 보이므로 대상이다
js = src.split("<script>")[-1]
tpl = re.findall(r"`([^`]*\$\{[^`]*)`", js) + re.findall(r"'([^']*[가-힣][^']*)'", js)
tpl = [re.sub(r"\s+", " ", t).strip() for t in tpl]
tpl = [t for t in tpl if any("가" <= c <= "힣" for c in t)]

print("=== D3 — 화면 문자열 전수 ===\n")
n = 0
for kind, t in p.out:
    n += 1
    print(f"{n:>3}. [{kind}] {t}")
print(f"\n--- 동적(스크립트 내 사용자 노출 템플릿) ---")
for t in dict.fromkeys(tpl):
    n += 1
    print(f"{n:>3}. [템플릿] {t}")
print(f"\n총 {n}개\n")

print("=== G-V 3항 — 등급 0개 (금지어 기계 대조) ===")
allt = [t for _, t in p.out] + tpl
hits = []
for t in allt:
    for b in BAN:
        if b.lower() in t.lower():
            hits.append((b, t))
if not hits:
    print("금지어 출현 0건.")
else:
    for b, t in hits:
        ok = next((v for k, v in ALLOW.items() if k in t), None)
        print(f"  {'○' if ok else '✗'} 「{b}」 in: {t}")
        if ok:
            print(f"      → 허용: {ok}")
        else:
            print(f"      → **불합격 후보. 사람이 판정한다.**")
    bad = [h for h in hits if not any(k in h[1] for k in ALLOW)]
    print(f"\n미해소 {len(bad)}건 → {'**3항 불합격**' if bad else '**3항 통과**'}")
