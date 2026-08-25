# -*- coding: utf-8 -*-
"""**유튜브 썸네일을 만든다.** 1280×720.

## 왜 자동 썸네일을 안 쓰나

**유튜브가 알아서 고르면 어두운 프레임이 잡힐 가능성이 크다** —
이 영상은 **악장이 바뀔 때마다 검은 화면**이 들어간다(0.8초).

## 어느 프레임인가

**7:25.32 알함브라 안뜰** (검수자 지정). 파란 하늘 · 사암 탑 ·
**붉은 만톤**. **이 영상에서 색 대비가 가장 큰 자리**다.

## 자르는 법

화면은 16:9 인데 **가운데 사진은 4:3** 이고 양옆은 흐린 배경이다.
**흐린 배경을 빼고 사진만 남긴 뒤 16:9 로 맞춘다** —
**위쪽 하늘을 자른다.** 그녀가 아래에 있으므로 아래는 못 자른다.

## 자기검사 — 셋
"""
import io
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# **워터마크가 붙기 전의 렌더**에서 뽑는다 — 완성본에서 뽑으면
# **오른쪽 아래 워터마크가 잘린 채로** 썸네일에 들어간다(2026-08-25 실측).
영상 = os.path.join(ROOT, "95. 영상 프로젝트", "out", "영상만-v14.mp4")
시각 = 447.6                       # 7:27.6 — 7:25.32 컷의 한가운데
낼곳 = os.path.join(ROOT, "산출물", "20260825 - 유튜브 업로드")

굵은글꼴 = "C:/Windows/Fonts/malgunbd.ttf"
보통글꼴 = "C:/Windows/Fonts/malgun.ttf"


def 자검사(im, 이름):
    """**썸네일이 썸네일 노릇을 하는가**를 잰다."""
    결과 = []
    결과.append(("1280x720 인가", None if im.size == (1280, 720) else str(im.size)))

    a = np.asarray(im.convert("L"), float)
    결과.append(("너무 어둡지 않은가",
                 None if a.mean() > 60 else "평균 밝기 %.0f — 작게 보면 안 보인다" % a.mean()))

    # **붉은 만톤이 살아 있는가** — 이 썸네일의 존재 이유다
    R = np.asarray(im.convert("RGB"), float)
    붉 = ((R[:, :, 0] - np.maximum(R[:, :, 1], R[:, :, 2])) > 45).mean() * 100
    결과.append(("붉은 만톤이 보이는가",
                 None if 붉 > 0.4 else "붉은 화소 %.2f%% — 너무 작다" % 붉))

    print("  [%s]" % 이름)
    for 이, 틀 in 결과:
        print("    %-22s %s" % (이, "OK" if 틀 is None else "X " + 틀))
    return not any(x for _, x in 결과)


def 만든다():
    os.makedirs(낼곳, exist_ok=True)
    원 = os.path.join(낼곳, "_프레임.png")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(시각),
                    "-i", 영상, "-frames:v", "1", 원], check=True)
    im = Image.open(원).convert("RGB")

    # ── 흐린 배경을 빼고 사진만 남긴다 ──────────────────────
    #
    # 4:3 사진이 1080 높이로 가운데 놓여 있으므로 폭은 1080*4/3 = 1440.
    x0 = (im.width - 1440) // 2
    사진 = im.crop((x0, 0, x0 + 1440, im.height))       # 1440x1080

    # ── 16:9 로 맞춘다 — **위쪽 하늘을 자른다** ─────────────
    #
    # 그녀가 화면 아래쪽에 서 있어서 **아래는 못 자른다.**
    높 = int(1440 * 9 / 16)                              # 810
    잘 = 사진.crop((0, 1080 - 높, 1440, 1080))
    잘 = 잘.resize((1280, 720), Image.LANCZOS)

    민 = 잘.copy()
    민.save(os.path.join(낼곳, "썸네일 - 글자 없음.png"))

    # ── 글자를 얹은 판 ────────────────────────────────────
    #
    # **작게 보일 때가 기준이다.** 유튜브 목록에서는 폭 210px 안팎으로 줄어든다.
    # 그래서 **큰 글자 한 줄 + 작은 한 줄**만 얹는다.
    글 = 잘.copy()
    d = ImageDraw.Draw(글, "RGBA")
    # 왼쪽 위에 어둠을 깔아 글자가 읽히게 한다
    for i in range(200):
        d.line([(0, i), (1280, i)], fill=(0, 0, 0, int(150 * (1 - i / 200))))
    큰 = ImageFont.truetype(굵은글꼴, 62)
    작 = ImageFont.truetype(보통글꼴, 30)
    d.text((54, 40), "스페인 전람회의 그림", font=큰, fill=(246, 243, 236))
    d.text((57, 118), "Pictures at a Spanish Exhibition", font=작,
           fill=(196, 206, 218))
    글.save(os.path.join(낼곳, "썸네일 - 글자 있음.png"))

    os.remove(원)
    print("=== 자기검사 ===")
    두 = 자검사(민, "글자 없음") & 자검사(글, "글자 있음")
    if not 두:
        sys.exit("\n**자기검사 미달.**")
    print("\n-> %s" % 낼곳)


if __name__ == "__main__":
    만든다()
