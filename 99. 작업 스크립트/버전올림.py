# -*- coding: utf-8 -*-
"""**프로젝트 버전 표기를 한 번에 올린다.**

2026-08-19 신설. `doc-revise` 절차 4단계(버전)를 도구로 옮긴 것이다.

**왜 스크립트로 만드나** — 이 일은 개정 때마다 한다. 그동안은 `doc-revise`
스킬에 **heredoc(`python - <<'PY'`) 예시**로 적혀 있었고, 나는 그 꼴을 따라
쓰다가 **두 번 실패했다.**

  ① 셸이 따옴표를 세다 말고 `unexpected EOF` 를 냈다
  ② 역슬래시가 **셸 → 파이썬 소스 → 파이썬 문자열** 세 겹을 지나며 몇 개인지
     헷갈렸다

**둘 다 「셸을 한 겹 끼웠기 때문」에 생긴 문제다.** 파일로 만들어 두면 그 겹이
사라진다. **그리고 이건 매번 같은 일이므로 애초에 매번 새로 짤 이유가 없다.**

    python 버전올림.py v4.26 2026-08-19 "v4.26 (2026-08-19) Suno 실측과 A판 기각"

  1번째 — 올릴 버전
  2번째 — 날짜
  3번째 — `백업/` 스냅샷 폴더 이름 (없으면 `CLAUDE.md` 3절은 건너뛴다)

**지금 버전은 문서에서 읽는다.** 손으로 안 적는다 — 그게 v1.14~v2.1 에서 일곱 번
밀렸던 원인이다.

**이 도구가 안 하는 것** — `04` 대장 3곳(2·3·4장)은 **판단이 들어가므로** 사람이
쓴다. 다 끝나면 `검증.py` 가 본다.
"""
import glob
import io
import os
import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

# 문서마다 버전 표기 꼴이 다르다. `doc-revise` 4절의 표가 정본이다.
PATS = [
    "| **버전** | **%s** (%s) |",          # 00~06 등 머리 표
    "| 현재 버전 | **%s** (%s) |",         # 04 문서
    "버전 **%s** (%s) · 작성 Claude",      # 07 작곡 계획
]


def now():
    """지금 버전과 날짜를 **문서에서 읽는다.** `04` 가 정본이다."""
    p = os.path.join(ROOT, "04. 문서 개정 이력.md")
    t = io.open(p, encoding="utf-8").read()
    m = re.search(r"\| 현재 버전 \| \*\*(v[\d.]+)\*\* \((\d{4}-\d\d-\d\d)\) \|", t)
    if not m:
        raise SystemExit("✘ `04` 머리 표에서 현재 버전을 못 읽었다")
    return m.group(1), m.group(2)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    new, newd = sys.argv[1], sys.argv[2]
    snap = sys.argv[3] if len(sys.argv) > 3 else None
    old, oldd = now()

    if new == old:
        raise SystemExit("✘ 지금이 이미 %s 다" % old)
    print("%s (%s)  →  %s (%s)\n" % (old, oldd, new, newd))

    os.chdir(ROOT)
    hit = []
    for f in sorted(glob.glob("*.md")):
        t0 = io.open(f, encoding="utf-8").read()
        t = t0
        for pat in PATS:
            t = t.replace(pat % (old, oldd), pat % (new, newd))
        if t != t0:
            io.open(f, "w", encoding="utf-8").write(t)
            hit.append(f)
    for f in hit:
        print("  갱신  %s" % f)

    # `CLAUDE.md` 는 검증 5번 검사에서 빠져 있어 손으로 고쳐야 하는 자리다.
    # **그래서 도구가 한다** — 실제로 일곱 번 밀렸던 곳이다.
    p = os.path.join(ROOT, "CLAUDE.md")
    t0 = io.open(p, encoding="utf-8").read()
    t = t0
    t = re.sub(r"\*최종 갱신 [\d-]+ · 프로젝트 v[\d.]+\*",
               "*최종 갱신 %s · 프로젝트 %s*" % (newd, new), t)
    if snap:
        t = re.sub(r"\*\*현재 버전: v[\d.]+\*\* \([\d-]+\)\. 최신 스냅샷 `백업/[^`]+`\.",
                   "**현재 버전: %s** (%s). 최신 스냅샷 `백업/%s/`."
                   % (new, newd, snap.rstrip("/")), t)
    if t != t0:
        io.open(p, "w", encoding="utf-8").write(t)
        print("  갱신  CLAUDE.md  (3절%s · 끝줄)" % ("" if snap else " 건너뜀"))

    # 안 고쳐진 곳이 남았는지 스스로 본다
    left = []
    for f in sorted(glob.glob("*.md")):
        t = io.open(f, encoding="utf-8").read()
        if any(pat % (old, oldd) in t for pat in PATS):
            left.append(f)
    print()
    if left:
        print("✘ 아직 %s 로 남은 문서 — %s" % (old, " · ".join(left)))
        raise SystemExit(1)
    print("✔ %d개 문서 + CLAUDE.md 갱신. %s 표기는 남지 않았다" % (len(hit), old))
    print()
    print("**남은 것은 사람이 한다** — `04` 대장 2·3·4장 세 곳.")
    print("  2장 화살표 · 3장 이력 행(직전 행 굵게 해제) · 4장 문서별 현황")
    print("끝나면  python \"99. 작업 스크립트/검증.py\"")


if __name__ == "__main__":
    main()
