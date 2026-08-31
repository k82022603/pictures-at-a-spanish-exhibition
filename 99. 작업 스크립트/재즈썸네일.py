# -*- coding: utf-8 -*-
"""**재즈판 유튜브 썸네일을 만든다.** 1280×720.

2026-08-30. 검수자 — *"유튜브 썸네일 이미지 만들어줘요."*

## 지난 판과 무엇이 다른가

| | 승인판 썸네일 | 이 판 |
|---|---|---|
| 어디서 뽑나 | **영상 프레임** | **★ 원본 사진** |
| 왜 | 그 판은 화면이 사진으로 꽉 찼다 | **이 판은 세로 사진에 좌우 여백이 579화소**다. 그대로 뽑으면 썸네일의 절반이 검다 |
| 자르기 | 위쪽 하늘을 잘랐다 | **가로 사진을 16:9 로 얕게 자른다** |

> **★ 영상에서는 안 자르고 썸네일에서는 자른다.**
> 「가로 사진도 잘라내지 않는다」는 **영상의 규칙**이고,
> **썸네일은 영상이 아니라 표지**다. 16:9 로 안 맞추면 유튜브가 알아서 자른다.

## 왜 자동 썸네일을 안 쓰나

**유튜브가 알아서 고르면 도시 경계의 얼룩무늬나 페이드 중간이 잡힐 수 있다.**
이 영상은 컷마다 앞뒤 0.6초가 어둡다.

## 자기검사 — 넷

| 무엇 | 통과 기준 |
|---|---|
| 크기 | **1280×720** |
| 밝기 | 평균 **60 이상** — 작게 보면 어두운 것은 안 보인다 |
| **색이 살아 있는가** | 채도 평균 **25 이상.** 이 판은 컬러가 요지다 |
| **글자 자리가 읽히는가** | 위 250화소 밝기 **150 아래**. **글자 있는 판에만 묻는다** |

**미달이면 `sys.exit`.**
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
사진밑 = os.path.join(ROOT, "2005년 12월 스페인")
낼곳 = os.path.join(ROOT, "산출물", "20260830 - 사진 고르기", "썸네일")

굵은글꼴 = "C:/Windows/Fonts/malgunbd.ttf"
보통글꼴 = "C:/Windows/Fonts/malgun.ttf"

제목 = "스페인 전람회의 그림"
부제 = "재즈판 · Jazz Version"
# **여정의 때를 못박는다** (2026-08-31 검수자 — *"2005년 12월 여정 명기"*).
# 20년 전 사진이라는 것이 이 영상의 요지이고, 썸네일에서 그것이 보여야 한다.
여정 = "2005년 12월 여정"

# 후보 — (이름, 사진, 세로로 어디를 남길까 0=위 1=아래 0.5=가운데)
후보들 = [
    ("알람브라", "2005.12.12-그라나다/P1010145.JPG", 0.5),
    ("마드리드", "2005.12.08-마드리드/PC080004.JPG", 0.55),
]


def 자르기(im, 앵커):
    """**16:9 로 얕게 자른다.** 4:3 사진이면 위아래에서 25%가 나간다."""
    목표 = 16 / 9
    w, h = im.size
    if w / h > 목표:
        새폭 = int(h * 목표)
        x = int((w - 새폭) * 0.5)
        im = im.crop((x, 0, x + 새폭, h))
    else:
        새높 = int(w / 목표)
        y = int((h - 새높) * 앵커)
        im = im.crop((0, y, w, y + 새높))
    return im.resize((1280, 720), Image.LANCZOS)


def 글자얹기(im):
    글 = im.copy()
    d = ImageDraw.Draw(글, "RGBA")
    # **위쪽에 어둠을 깔아 글자가 읽히게 한다** — 사진이 밝아도 흰 글자가 산다
    for i in range(250):
        d.line([(0, i), (1280, i)], fill=(0, 0, 0, int(170 * (1 - i / 250))))
    d.text((54, 34), 제목, font=ImageFont.truetype(굵은글꼴, 62),
           fill=(246, 243, 236))
    d.text((57, 114), 부제, font=ImageFont.truetype(보통글꼴, 30),
           fill=(198, 208, 220))
    d.text((57, 156), 여정, font=ImageFont.truetype(보통글꼴, 26),
           fill=(168, 180, 196))
    return 글


def 자검사(im, 이름, 글자있음=False):
    결과 = []
    결과.append(("1280x720 인가", None if im.size == (1280, 720) else str(im.size)))

    a = np.asarray(im.convert("L"), float)
    결과.append(("너무 어둡지 않은가",
                 None if a.mean() > 60 else "평균 밝기 %.0f" % a.mean()))

    hsv = np.asarray(im.convert("HSV"), float)
    채도 = hsv[:, :, 1].mean()
    결과.append(("색이 살아 있는가",
                 None if 채도 > 25 else "채도 평균 %.0f — 흑백처럼 보인다" % 채도))

    # **글자 있는 판에만 묻는다** — 글자 없는 판에 물으면 밝은 하늘이 걸린다.
    # 처음에 이 구분을 안 해서 멀쩡한 썸네일이 미달로 찍혔다 (2026-08-30).
    if 글자있음:
        위 = a[:250].mean()
        결과.append(("글자 자리가 읽히는가",
                     None if 위 < 150 else "위 250화소 밝기 %.0f — 흰 글자가 묻힌다" % 위))

    print("  [%s]" % 이름)
    for 이, 틀 in 결과:
        print("    %-22s %s" % (이, "OK" if 틀 is None else "X " + 틀))
    return not any(x for _, x in 결과)


if __name__ == "__main__":
    os.makedirs(낼곳, exist_ok=True)
    print("=== 자기검사 ===")
    다통과 = True
    for 이름, 상대, 앵커 in 후보들:
        p = os.path.join(사진밑, 상대.replace("/", os.sep))
        if not os.path.exists(p):
            sys.exit("없는 사진 — %s" % 상대)
        민 = 자르기(Image.open(p).convert("RGB"), 앵커)
        글 = 글자얹기(민)
        민.save(os.path.join(낼곳, "썸네일 %s - 글자 없음.png" % 이름))
        글.save(os.path.join(낼곳, "썸네일 %s - 글자 있음.png" % 이름))
        다통과 &= 자검사(민, "%s · 글자 없음" % 이름)
        다통과 &= 자검사(글, "%s · 글자 있음" % 이름, True)
    if not 다통과:
        sys.exit("\n**자기검사 미달.**")
    print("\n→ %s" % 낼곳)
