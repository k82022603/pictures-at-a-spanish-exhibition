# -*- coding: utf-8 -*-
"""**셀렉 전에 숫자가 어떻게 퍼져 있는지 본다** — 문턱을 감으로 정하지 않기 위해.

2026-08-20. `사진목록.py` 가 낸 CSV 를 읽어 도시별·전체 분포를 찍는다.
**등급을 매기는 것은 눈이지만, 눈이 볼 것을 고르는 것은 숫자다.**

    python 사진분포.py
"""
import csv
import io
import os
import sys
from collections import defaultdict

import numpy as np

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
CSV = os.path.join(ROOT, "산출물", "20260820 - 가락은 내가 입힌다", "사진 목록.csv")


def main():
    rows = list(csv.DictReader(io.open(CSV, encoding="utf-8-sig")))
    print("사진 %d 장\n" % len(rows))

    for 열 in ("밝기", "대비", "선명도", "어두움%", "날림%"):
        v = np.array([float(r[열]) for r in rows])
        q = np.percentile(v, [5, 25, 50, 75, 95])
        print("  %-7s  최소 %7.1f | 5%% %7.1f | 25%% %7.1f | 중앙 %7.1f "
              "| 75%% %7.1f | 95%% %7.1f | 최대 %8.1f"
              % (열, v.min(), q[0], q[1], q[2], q[3], q[4], v.max()))

    print("\n=== 도시별 선명도 ===")
    도시별 = defaultdict(list)
    for r in rows:
        도시별[r["도시"]].append(r)
    for c, v in 도시별.items():
        s = np.array([float(r["선명도"]) for r in v])
        b = np.array([float(r["밝기"]) for r in v])
        세 = sum(1 for r in v if r["방향"] == "세로")
        print("  %-8s %3d장 (세로 %3d)  선명도 중앙 %6.0f  밝기 중앙 %5.0f  "
              "흐림(<100) %2d  어두움(<70) %2d"
              % (c, len(v), 세, np.median(s), np.median(b),
                 sum(1 for x in s if x < 100), sum(1 for x in b if x < 70)))

    print("\n=== 흐린 것 (선명도 < 150) ===")
    for r in sorted(rows, key=lambda r: float(r["선명도"]))[:30]:
        print("  %-8s %-22s %4s×%-4s 선명 %5s 밝기 %4s 어두움%% %5s"
              % (r["도시"], r["파일"], r["가로"], r["세로"],
                 r["선명도"], r["밝기"], r["어두움%"]))

    print("\n=== 어두운 것 (밝기 낮은 순 25) ===")
    for r in sorted(rows, key=lambda r: float(r["밝기"]))[:25]:
        print("  %-8s %-22s 밝기 %4s 어두움%% %5s 선명 %6s"
              % (r["도시"], r["파일"], r["밝기"], r["어두움%"], r["선명도"]))

    print("\n=== 날린 것 (하이라이트 > 3%%) ===")
    for r in sorted(rows, key=lambda r: -float(r["날림%"]))[:15]:
        print("  %-8s %-22s 날림%% %6s 밝기 %4s"
              % (r["도시"], r["파일"], r["날림%"], r["밝기"]))

    print("\n=== 선명도 상위 40 (히어로 후보 1차) ===")
    for r in sorted(rows, key=lambda r: -float(r["선명도"]))[:40]:
        print("  %-8s %-22s %4s×%-4s %s 선명 %6s 밝기 %4s 대비 %4s"
              % (r["도시"], r["파일"], r["가로"], r["세로"], r["방향"],
                 r["선명도"], r["밝기"], r["대비"]))


if __name__ == "__main__":
    main()
