# 사전등록 (pre-registration)

측정 **전에** 합격선을 못 박았음을 증명하는 파일. `re0` 게이트 G5의 증거 형태다.

`.re0/`는 로컬 스크래치라 `.gitignore` 대상이고, 그래서 `EVIDENCE.local.md` 자체는
커밋 이력을 남길 수 없다. 대신 합격선 블록의 해시를 여기 남긴다.
**이 줄이 담긴 커밋이 측정 결과 커밋보다 앞서면 G5가 성립한다.**

검증:

```sh
python3 - <<'EOF'
import hashlib,io
CYCLE="v0.2.0-fact-on-screen"          # 또는 "v0.1.0-source-decision"
H1,H2="### 합격선","### 판정의 의미"    # G-A는 "### 합격선 — G-A" / "### 판정의 의미 — G-A"
s=io.open(f".re0/iteration/{CYCLE}/EVIDENCE.local.md",encoding="utf-8").read()
b=H1+s.split(H1)[1].split(H2)[0]
print(hashlib.sha256(b.encode("utf-8")).hexdigest())
EOF
```

| 게이트 | 사이클 | 합격선 블록 SHA-256 | 등록일 |
|---|---|---|---|
| G0 — 신호 타당성 | `v0.1.0-source-decision` | `a44996a4eac79bfcd59b97b333d6a7d8316125729620243e865942ca0e892af7` | 2026-08-27 |
| G-C′ — 레이어 커버리지 하한 | `v0.2.0-fact-on-screen` | `23ec3a666b6915158412843cd0779c53e2185f59e1e322fa432cba84c00e7322` | 2026-08-27 |
| G-A — 축의 타당성 (백년가게 모순 검사) | `v0.2.0-fact-on-screen` | `8d759975d28713f2c9e7008dff0d27f7708692f7668cf24af00ad22d9982b86a` | 2026-08-27 |

해시가 안 맞으면 합격선이 사후에 수정된 것이고, 그 게이트는 무효다.
