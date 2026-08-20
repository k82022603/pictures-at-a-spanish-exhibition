# -*- coding: utf-8 -*-
"""**사진을 한 판에 열여섯 장씩 붙여 눈으로 보게 만든다** — 컨택트 시트.

2026-08-20. WBS 2.1 셀렉. `사진목록.py` 가 **숫자**를 냈고, 등급은 **구도**를
봐야 나온다. 248 장을 한 장씩 여는 것은 낭비이므로 **도시별로 판을 짜서**
한 번에 열여섯 장씩 본다.

**원본은 안 건드린다. 줄여서 새 이미지에 그릴 뿐이다**(R11).
판은 **보기 위한 것이지 산출물이 아니다** — 임시 폴더에 낸다(`CLAUDE.md` 8절).
**G3 전에 사진으로 영상을 만들지 않는다**(9절)에 안 걸린다. 이것은 영상이
아니라 **목록을 눈으로 훑는 도구**다.

    python 사진판.py <낼 폴더>
"""
import os
import sys

from PIL import Image, ImageDraw

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
사진 = os.path.join(ROOT, "2005년 12월 스페인")

칸가로, 칸세로 = 430, 322      # 칸 하나에 들어갈 최대 크기
열, 행 = 4, 4                  # 한 판에 4×4 = 열여섯 장
글자띠 = 18


def 판만들기(묶음, 낼파일):
    W = 열 * (칸가로 + 8) + 8
    H = 행 * (칸세로 + 글자띠 + 8) + 8
    판 = Image.new("RGB", (W, H), (24, 24, 24))
    그리기 = ImageDraw.Draw(판)
    for k, (이름, 경로) in enumerate(묶음):
        r, c = divmod(k, 열)
        x = 8 + c * (칸가로 + 8)
        y = 8 + r * (칸세로 + 글자띠 + 8)
        with Image.open(경로) as im:
            im = im.convert("RGB")
            im.thumbnail((칸가로, 칸세로), Image.LANCZOS)
            판.paste(im, (x + (칸가로 - im.width) // 2, y))
        그리기.text((x + 2, y + 칸세로 + 3), 이름, fill=(235, 235, 120))
    판.save(낼파일, quality=88)
    return 낼파일


def main():
    낼곳 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_판")
    os.makedirs(낼곳, exist_ok=True)
    for 폴더 in sorted(os.listdir(사진)):
        d = os.path.join(사진, 폴더)
        if not os.path.isdir(d):
            continue
        파일들 = [(f, os.path.join(d, f)) for f in sorted(os.listdir(d))
                if f.lower().endswith((".jpg", ".jpeg"))]
        if not 파일들:
            continue
        도시 = 폴더.split("-", 1)[-1].strip()
        날 = 폴더.split("-", 1)[0].replace("2005.", "")
        for i in range(0, len(파일들), 열 * 행):
            묶음 = 파일들[i:i + 열 * 행]
            이름 = "%s %s %02d.jpg" % (날, 도시, i // (열 * 행) + 1)
            p = 판만들기(묶음, os.path.join(낼곳, 이름))
            print("%s  (%d장)" % (os.path.basename(p), len(묶음)))


if __name__ == "__main__":
    main()
