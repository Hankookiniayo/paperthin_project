# 사전등록 (pre-registration)

측정 **전에** 합격선을 못 박았음을 증명하는 파일. `re0` 게이트 G5의 증거 형태다.

`.re0/`는 로컬 스크래치라 `.gitignore` 대상이고, 그래서 `EVIDENCE.local.md` 자체는
커밋 이력을 남길 수 없다. 대신 합격선 블록의 해시를 여기 남긴다.
**이 줄이 담긴 커밋이 측정 결과 커밋보다 앞서면 G5가 성립한다.**

검증:

```sh
python3 - <<'EOF'
import hashlib,io
s=io.open(".re0/iteration/v0.1.0-source-decision/EVIDENCE.local.md",encoding="utf-8").read()
b="### 합격선"+s.split("### 합격선")[1].split("### 판정의 의미")[0]
print(hashlib.sha256(b.encode("utf-8")).hexdigest())
EOF
```

| 게이트 | 합격선 블록 SHA-256 | 등록일 |
|---|---|---|
| G0 — 신호 타당성 | `a44996a4eac79bfcd59b97b333d6a7d8316125729620243e865942ca0e892af7` | 2026-08-27 |

해시가 안 맞으면 합격선이 사후에 수정된 것이고, 그 게이트는 무효다.
