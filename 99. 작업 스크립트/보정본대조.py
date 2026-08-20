# -*- coding: utf-8 -*-
"""**「같은 사진의 다른 판」이 몇 쌍인가** — 픽셀 하나로는 못 잡는다.

2026-08-20. `사진목록.py` 의 지문 대조(32×32 밝기 패턴)가 **회전 보정본을
못 잡는다.** 돌려놓으면 밝기 패턴이 통째로 어긋나기 때문이다. 그래서
`01`·`00` 이 적어둔 보정본 셋 중 **둘(회전)이 목록에 안 나왔다.**

**「이 검색으로는 안 잡힌다」와 「없다」는 다른 말이다** (`CLAUDE.md` 7절).
그래서 경로를 셋 더 판다.

  | 경로 | 무엇을 잡나 |
  |---|---|
  | ① 이름 짝짓기 | `P1010109` 와 `P1010109_edited` 처럼 **앞부분이 같은 것** |
  | ② 촬영 시각(EXIF) | **같은 순간에 찍힌 것이 둘이면** 한쪽은 사본이다 |
  | ③ 회전을 감안한 지문 | 90°·180°·270° 로 돌려가며 다시 견준다 |
  | ④ **만든 도구(EXIF Software)** | 카메라가 아닌 프로그램 이름이 박혀 있으면 **손댄 것**이다 |
  | ⑤ **색 히스토그램** | 각도와 크기에 **상관없이** 같다. ③ 이 못 잡는 45° 회전을 잡는다 |

**③ 은 헛발질이었다** — 이 보정본들은 90° 가 아니라 **45° 안팎으로 돌아가 있다.**
그래서 ⑤ 를 더했다. **「이 검색으로는 안 잡힌다」를 「없다」로 읽지 않기 위해서다.**

**읽기만 한다. 고치지도 옮기지도 지우지도 않는다** (R11).

    python 보정본대조.py
"""
import os
import sys
from collections import defaultdict

import numpy as np
from PIL import Image, ExifTags

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
사진 = os.path.join(ROOT, "2005년 12월 스페인")

EXIF역 = {v: k for k, v in ExifTags.TAGS.items()}


def 지문(p, 각도=0):
    with Image.open(p) as im:
        im = im.convert("L")
        if 각도:
            im = im.rotate(각도, expand=True)
        s = np.asarray(im.resize((32, 32), Image.BILINEAR), dtype=np.float64)
    s = (s - s.mean()) / (s.std() + 1e-9)
    v = s.ravel()
    return v / (np.linalg.norm(v) + 1e-9)


def 찍은때(p):
    try:
        with Image.open(p) as im:
            ex = im.getexif()
            for 이름 in ("DateTimeOriginal", "DateTime"):
                t = ex.get(EXIF역.get(이름))
                if t:
                    return str(t)
            ifd = ex.get_ifd(0x8769)
            for 키 in (36867, 36868):
                if ifd.get(키):
                    return str(ifd[키])
    except Exception:
        pass
    return ""


def 소프트웨어(p):
    try:
        with Image.open(p) as im:
            return str(im.getexif().get(EXIF역.get("Software"), "") or "")
    except Exception:
        return ""


def main():
    목록 = []
    for 폴더 in sorted(os.listdir(사진)):
        d = os.path.join(사진, 폴더)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith((".jpg", ".jpeg")):
                목록.append((폴더, f, os.path.join(d, f)))

    print("사진 %d 장\n" % len(목록))

    # ① 이름 앞부분이 같은 것
    print("=== ① 이름으로 짝짓기 ===")
    뿌리 = defaultdict(list)
    for 폴더, f, p in 목록:
        n = os.path.splitext(f)[0]
        for 꼬리 in ("_edited", "_1", "_2", "_copy", "-1", " (1)", "_수정", "_보정"):
            if n.lower().endswith(꼬리.lower()):
                n = n[: -len(꼬리)]
                break
        뿌리[(폴더, n)].append((f, p))
    이름짝 = {k: v for k, v in 뿌리.items() if len(v) > 1}
    for (폴더, n), v in sorted(이름짝.items()):
        print("  %s / %s" % (폴더, n))
        for f, p in v:
            with Image.open(p) as im:
                w, h = im.size
            print("      %-22s %4d×%-4d  %8d B  찍은때 %-20s %s"
                  % (f, w, h, os.path.getsize(p), 찍은때(p) or "-",
                     소프트웨어(p) or ""))
    if not 이름짝:
        print("  (없다)")

    # ② 촬영 시각이 겹치는 것
    print("\n=== ② 촬영 시각(EXIF)이 같은 것 ===")
    때별 = defaultdict(list)
    없음 = 0
    for 폴더, f, p in 목록:
        t = 찍은때(p)
        if t:
            때별[t].append((폴더, f))
        else:
            없음 += 1
    겹침 = {k: v for k, v in 때별.items() if len(v) > 1}
    for t, v in sorted(겹침.items()):
        print("  %s" % t)
        for 폴더, f in v:
            print("      %s / %s" % (폴더, f))
    if not 겹침:
        print("  (없다)")
    print("  · EXIF 시각이 없는 파일 %d 장" % 없음)

    # ③ 회전을 감안한 지문
    print("\n=== ③ 90°·180°·270° 돌려가며 다시 대조 ===")
    기준 = np.stack([지문(p) for _, _, p in 목록])
    찾음 = []
    for 각도 in (90, 180, 270):
        회전 = np.stack([지문(p, 각도) for _, _, p in 목록])
        S = 회전 @ 기준.T
        for i in range(len(목록)):
            for j in range(len(목록)):
                if i == j:
                    continue
                if S[i, j] >= 0.93:
                    찾음.append((S[i, j], 각도, i, j))
    본것 = set()
    for s, 각도, i, j in sorted(찾음, reverse=True):
        키 = tuple(sorted((i, j)))
        if 키 in 본것:
            continue
        본것.add(키)
        print("  닮음 %.3f (%d° 회전)  %s/%s  ↔  %s/%s"
              % (s, 각도, 목록[i][0], 목록[i][1], 목록[j][0], 목록[j][1]))
    if not 본것:
        print("  (없다)")

    # ④ 만든 도구 — 카메라 펌웨어가 아닌 것
    print("\n=== ④ 만든 도구(EXIF Software)가 카메라가 아닌 것 ===")
    도구별 = defaultdict(list)
    for 폴더, f, p in 목록:
        도구별[소프트웨어(p) or "(없음)"].append((폴더, f))
    for 도구, v in sorted(도구별.items(), key=lambda x: -len(x[1])):
        print("  %-42s %3d 장" % (도구, len(v)))
    카메라 = max(도구별.items(), key=lambda x: len(x[1]))[0]
    손댄것 = [(폴더, f) for 도구, v in 도구별.items() if 도구 != 카메라
            for 폴더, f in v]
    print("  → 카메라 펌웨어는 '%s'. **그 밖의 것 %d 장**" % (카메라, len(손댄것)))
    for 폴더, f in sorted(손댄것):
        print("      %s / %s" % (폴더, f))

    # ⑤ 색 히스토그램 — 회전·크기와 무관하다
    print("\n=== ⑤ 색 히스토그램으로 대조 (회전·크기 무관) ===")
    def 색지문(p):
        with Image.open(p) as im:
            im = im.convert("RGB").resize((128, 128), Image.BILINEAR)
            a = np.asarray(im, dtype=np.uint8).reshape(-1, 3) // 16
        h = np.zeros(16 * 3, dtype=np.float64)
        for c in range(3):
            h[c * 16:(c + 1) * 16] = np.bincount(a[:, c], minlength=16)
        return h / (np.linalg.norm(h) + 1e-9)

    C = np.stack([색지문(p) for _, _, p in 목록])
    S = C @ C.T
    np.fill_diagonal(S, 0.0)
    쌍 = []
    for i in range(len(목록)):
        for j in range(i + 1, len(목록)):
            if S[i, j] >= 0.995:
                쌍.append((S[i, j], i, j))
    for s, i, j in sorted(쌍, reverse=True)[:25]:
        같은폴더 = "같은 날" if 목록[i][0] == 목록[j][0] else ""
        print("  닮음 %.4f  %s/%s  ↔  %s/%s  %s"
              % (s, 목록[i][0], 목록[i][1], 목록[j][0], 목록[j][1], 같은폴더))
    print("  · 0.995 이상인 쌍 %d 개 (색만 같아도 걸리므로 **후보**일 뿐이다)" % len(쌍))


if __name__ == "__main__":
    main()
