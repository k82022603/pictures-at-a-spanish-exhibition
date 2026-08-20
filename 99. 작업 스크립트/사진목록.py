# -*- coding: utf-8 -*-
"""**사진 245장을 세고 재서 목록으로 만든다** — WBS 2.1 셀렉의 첫 단계.

2026-08-20. 검수자 — *"영상쪽 오늘 시작해도 되잖아. 음성과 병렬로 작업
진행 가능한거잖아."* 맞다. `01` 6장이 **Phase 1·2 병렬을 유일한 예외로**
적어두고 있고, 오늘 세운 마일스톤 7.1 이 **Phase 2 가 2주 늦었다**고 적었다.

**등급(A·B·C)을 매기는 것은 눈으로 하는 일이다. 이 도구는 그 앞을 맡는다** —
세고, 재고, 같은 장면을 묶는다. **눈이 볼 것을 245장에서 줄여 준다.**

무엇을 재나 — **셀렉에서 실제로 쓰는 것만.**

  | 재는 것 | 왜 |
  |---|---|
  | 크기 · 가로세로 | **세로 사진은 멀티패널로 묶는다**(`00` 영상 설계). 43%가 세로다 |
  | 밝기 | **너무 어두운 것은 업스케일해도 안 산다.** 2005년 12월 실내·야간이 많다 |
  | 대비 | 낮으면 뿌옇다 |
  | **선명도** | **AI 영상 생성의 입력 품질을 좌우한다**(`02` PoC 파라미터) |
  | 어두운 화소 비율 | 밝기 평균만으로는 **역광**과 **야경**이 구별 안 된다 |

**같은 장면 묶기는 바이트가 아니라 픽셀로 한다.** `01` 문서가 못박은 것이다 —
*"「바이트가 같은가」는 「같은 사진인가」가 아니다."* 원래 실사가 바이트만
비교해서 **축소본 다섯을 별개 사진으로 세고 있었다.**

**사진을 고치지도 옮기지도 지우지도 않는다. 읽기만 한다**(R11).

    python 사진목록.py                # → 산출물/…/사진 목록.md · .csv
"""
import csv
import os
import sys
from collections import defaultdict

import numpy as np
from PIL import Image

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
사진 = os.path.join(ROOT, "2005년 12월 스페인")
낼곳 = os.path.join(ROOT, "산출물", "20260820 - 가락은 내가 입힌다")

# 악장과 도시의 대응은 `00` 기획서 악장 구성표가 정본이다. 여기서는
# **폴더 이름에 든 도시**만 읽는다 — 손으로 옮겨 적지 않는다
def 도시(폴더):
    n = 폴더.split("-", 1)
    return n[1].strip() if len(n) > 1 else 폴더


def 재기(p):
    """사진 하나를 연다. **원본은 안 건드린다.**"""
    with Image.open(p) as im:
        w, h = im.size
        g = np.asarray(im.convert("L"), dtype=np.float64)
    밝기 = float(g.mean())
    대비 = float(g.std())
    # 선명도 — 이웃 화소와 얼마나 다른가. 흐린 사진은 이 값이 낮다
    lap = (g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
           - 4.0 * g[1:-1, 1:-1])
    선명 = float(lap.var())
    어두움 = float((g < 40).mean() * 100.0)
    날림 = float((g > 250).mean() * 100.0)
    # 같은 장면 묶기용 — 32×32 로 줄여 밝기 패턴만 남긴다
    with Image.open(p) as im:
        s = np.asarray(im.convert("L").resize((32, 32), Image.BILINEAR),
                       dtype=np.float64)
    s = (s - s.mean()) / (s.std() + 1e-9)
    return dict(가로=w, 세로=h, 밝기=밝기, 대비=대비, 선명=선명,
                어두움=어두움, 날림=날림, 지문=s.ravel())


def 같은장면(항목, 문턱=0.985):
    """지문끼리 견줘 **같은 장면**을 묶는다. 크기가 달라도 잡힌다."""
    n = len(항목)
    F = np.stack([a["지문"] for a in 항목])
    F = F / (np.linalg.norm(F, axis=1, keepdims=True) + 1e-9)
    묶음, 본것 = [], set()
    for i in range(n):
        if i in 본것:
            continue
        같음 = [i]
        sim = F[i] @ F[i + 1:].T if i + 1 < n else np.array([])
        for k, s in enumerate(sim):
            j = i + 1 + k
            if j not in 본것 and s >= 문턱:
                같음.append(j)
                본것.add(j)
        본것.add(i)
        if len(같음) > 1:
            묶음.append(같음)
    return 묶음


def main():
    if not os.path.isdir(사진):
        raise SystemExit("원본 폴더가 없다 — %s" % 사진)
    os.makedirs(낼곳, exist_ok=True)

    항목 = []
    for 폴더 in sorted(os.listdir(사진)):
        d = os.path.join(사진, 폴더)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith((".jpg", ".jpeg")):
                continue
            a = 재기(os.path.join(d, f))
            a.update(폴더=폴더, 도시=도시(폴더), 파일=f,
                     크기=os.path.getsize(os.path.join(d, f)))
            항목.append(a)

    print("사진 %d 장을 쟀다\n" % len(항목))

    묶음 = 같은장면(항목)
    중복 = sum(len(g) - 1 for g in 묶음)
    print("=== 도시별 ===")
    print("  %-12s %5s %5s %5s   %-22s" % ("도시", "장수", "가로", "세로", "어두운 것(밝기<70)"))
    도시별 = defaultdict(list)
    for a in 항목:
        도시별[a["도시"]].append(a)
    for c, v in 도시별.items():
        세 = sum(1 for a in v if a["세로"] > a["가로"])
        어 = sum(1 for a in v if a["밝기"] < 70)
        print("  %-12s %5d %5d %5d   %d 장" % (c, len(v), len(v) - 세, 세, 어))

    세로 = sum(1 for a in 항목 if a["세로"] > a["가로"])
    print("\n=== 전체 ===")
    print("  파일 %d 장 · **같은 장면 %d 쌍** → 고유 장면 %d 개"
          % (len(항목), 중복, len(항목) - 중복))
    print("  세로 %d 장 (%.0f%%) — 멀티패널 대상" % (세로, 100.0 * 세로 / len(항목)))
    print("  어두운 것(밝기<70) %d 장 · 흐린 것(선명<100) %d 장"
          % (sum(1 for a in 항목 if a["밝기"] < 70),
             sum(1 for a in 항목 if a["선명"] < 100)))

    if 묶음:
        print("\n=== 같은 장면으로 묶인 것 ===")
        for g in 묶음:
            print("  " + "  ·  ".join("%s/%s (%d×%d)"
                                      % (항목[i]["도시"], 항목[i]["파일"],
                                         항목[i]["가로"], 항목[i]["세로"])
                                      for i in g))

    # CSV — 등급을 여기에 손으로 적는다
    p = os.path.join(낼곳, "사진 목록.csv")
    with open(p, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["도시", "파일", "가로", "세로", "방향", "밝기", "대비",
                    "선명도", "어두움%", "날림%", "같은장면", "등급", "메모"])
        같은표 = {}
        for k, g in enumerate(묶음):
            for i in g:
                같은표[i] = k + 1
        for i, a in enumerate(항목):
            w.writerow([a["도시"], a["파일"], a["가로"], a["세로"],
                        "세로" if a["세로"] > a["가로"] else "가로",
                        "%.0f" % a["밝기"], "%.0f" % a["대비"],
                        "%.0f" % a["선명"], "%.1f" % a["어두움"],
                        "%.2f" % a["날림"], 같은표.get(i, ""), "", ""])
    print("\n→ %s" % os.path.relpath(p, ROOT))
    print("   **등급 칸은 비어 있다.** 눈으로 보고 채운다")


if __name__ == "__main__":
    main()
