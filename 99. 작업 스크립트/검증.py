"""
문서 검증 — 04. 문서 개정 이력 5장 운영 절차의 6단계.

MusicVideo 폴더에서 실행:
    python3 "99. 작업 스크립트/검증.py"

검사 항목
  1. 마크다운 표 열 수와 구분선
  2. 내부 링크가 실제 파일을 가리키는가
  3. 목차 앵커가 실제 헤딩과 맞는가
  4. 문서 간 공유 수치가 일치하는가
  5. 모든 문서의 버전이 같은가
  6. 최신 스냅샷이 현재 문서와 일치하는가
"""
import glob
import hashlib
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# 문서 간 반드시 일치해야 하는 값 — 바뀌면 여기도 함께 고친다
SHARED = {
    "유효 사진 장수": "253",
    "총 길이": "9분 40초",
    "총 기간": "30.0",
    "PoC 비용 상한": "$20",
    "본편 비용 상한": "$40",
}

problems = []


def fail(msg):
    problems.append(msg)
    print("  FAIL  " + msg)


def check_markdown(path):
    s = io.open(path, encoding="utf-8").read()
    lines = s.split("\n")

    # 1. 표
    i = tables = 0
    while i < len(lines):
        if lines[i].startswith("|"):
            blk = []
            while i < len(lines) and lines[i].startswith("|"):
                blk.append(lines[i])
                i += 1
            tables += 1
            widths = {len(r.split("|")) - 2 for r in blk}
            if len(widths) != 1:
                fail("%s: 표 열 수 불일치 %s — %s" % (path, widths, blk[0][:45]))
            if len(blk) < 2 or not re.match(r"^\|[\s\-:|]+\|$", blk[1]):
                fail("%s: 표 구분선 없음 — %s" % (path, blk[0][:45]))
        else:
            i += 1

    # 2. 내부 링크
    links = re.findall(r"\]\(<?((?!http)[^)>#]+)>?\)", s)
    for l in set(links):
        if not os.path.exists(l):
            fail("%s: 링크 대상 없음 — %s" % (path, l))

    # 3. 앵커
    heads = [h.strip() for h in re.findall(r"^#{1,4}\s+(.+)$", s, re.M)]
    anchors = {re.sub(r"[^\w가-힣\s-]", "", h).strip().lower().replace(" ", "-")
               for h in heads}
    for a in re.findall(r"\]\(#([^)]+)\)", s):
        if a not in anchors:
            fail("%s: 앵커 없음 — #%s" % (path, a))

    return tables, len(heads)


def main():
    docs = sorted(glob.glob("*.md"))
    if not docs:
        print("문서를 찾지 못했습니다. MusicVideo 폴더에서 실행하세요.")
        return 1

    print("=== 1~3. 문서별 검사 ===")
    for d in docs:
        t, h = check_markdown(d)
        print("  %-38s 표 %2d · 헤딩 %2d" % (d, t, h))

    print("\n=== 4. 문서 간 공유 수치 ===")
    texts = {d: io.open(d, encoding="utf-8").read() for d in docs}
    for name, val in SHARED.items():
        holders = [d for d in docs if val in texts[d]]
        if len(holders) < 2:
            print("  참고  %-16s '%s' — %d개 문서에만 등장" % (name, val, len(holders)))
        else:
            print("  OK    %-16s '%s' — %d개 문서 일치" % (name, val, len(holders)))

    print("\n=== 5. 버전 일치 ===")
    # CLAUDE.md 는 Claude Code 가 이름을 강제하는 인수인계 파일이다.
    # 머리 표·버전 표기 형식을 따르지 않으므로 이 검사에서만 제외한다.
    vers = {}
    for d in [x for x in docs if x != "CLAUDE.md"]:
        m = re.search(r"\*\*v(\d+\.\d+)\*\*\s*\(", texts[d])
        vers[d] = m.group(1) if m else None
        if not vers[d]:
            fail("%s: 머리 표에 버전 표기 없음" % d)
    found = {v for v in vers.values() if v}
    if len(found) > 1:
        fail("문서 간 버전 불일치 — %s" % vers)
    elif found:
        print("  OK    전 문서 v%s" % found.pop())

    print("\n=== 6. 최신 스냅샷 대조 ===")
    # 버전 번호로 정렬한다 — 문자열 정렬이면 "v1.10"이 "v1.2"보다 앞에 온다.
    # v1.10 부터 실제로 최신 스냅샷을 잘못 집는다. (2026-08-06)
    def _vkey(p):
        m = re.search(r"v(\d+)\.(\d+)", p)
        return (int(m.group(1)), int(m.group(2))) if m else (-1, -1)

    snaps = sorted(glob.glob("백업/v*/"), key=_vkey)
    if not snaps:
        print("  참고  스냅샷 없음")
    else:
        latest = snaps[-1]
        print("  기준  %s" % latest)
        for d in docs:
            sp = os.path.join(latest, d)
            if not os.path.exists(sp):
                fail("스냅샷에 없는 문서 — %s" % d)
                continue
            h1 = hashlib.md5(io.open(d, "rb").read()).hexdigest()
            h2 = hashlib.md5(io.open(sp, "rb").read()).hexdigest()
            if h1 != h2:
                fail("스냅샷과 다름 — %s (수정 후 새 스냅샷을 남기세요)" % d)
        else:
            pass

    print("\n" + "=" * 46)
    if problems:
        print("총 %d건의 문제가 있습니다." % len(problems))
        return 1
    print("문제 없음. 검증 통과.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
