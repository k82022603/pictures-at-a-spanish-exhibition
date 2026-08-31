# -*- coding: utf-8 -*-
"""**244장에서 쓸 사진을 고른다 — 재는 것 하나, 눈으로 보는 것 하나.**

2026-08-30. 검수자 지시 — *"뿌옇게 나온 사진 사용하지 않기"* · *"인물 사진 배제"* ·
*"무희 사진 없어도 됩니다"*.

## 두 가지를 다르게 고른다

| 무엇 | 어떻게 | 왜 |
|---|---|---|
| **뿌연 사진** | **잰다** — 라플라시안 분산 | 「또렷한가」는 숫자로 갈린다. 이 244장은 **6.6 ~ 1006.6 으로 150배** 벌어져 있다 |
| **인물 사진** | **눈으로 본다** — 연락표를 만들어 사람이 고른다 | **`cv2` 가 없고**, 있어도 「얼굴이 있다」와 「인물 사진이다」는 다르다. 거리에 사람이 지나가는 풍경은 인물 사진이 아니다 |

**그래서 이 도구는 판정하지 않는다.** 재서 표를 내고 연락표를 만들 뿐이고,
**인물 목록은 `뺄 사람 사진.txt` 에 손으로 적는다.**

> **★ 「자른다」는 목록에서 빼는 것이지 사진을 오려내는 것이 아니다.**
> 검수자 지시(2026-08-24) — *"가로 사진도 잘라내지 않는다."*

## 자검사 — 답을 아는 문제 셋

| 넣는 것 | 나와야 하는 값 |
|---|---|
| 또렷한 격자무늬 | 흐리게 한 같은 그림보다 **분산이 크다** |
| 같은 그림을 두 번 | **같은 값** |
| 단색 이미지 | **분산 ≈ 0** |

**미달이면 `sys.exit`.**
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
사진밑 = os.path.join(HERE, "..", "2005년 12월 스페인")
낼밑 = os.path.join(HERE, "..", "산출물", "20260830 - 사진 고르기")

선 = 20.0                      # 이보다 뿌연 것은 안 쓴다 (2026-08-30)

# **도시마다 선을 달리 둔다.**
#
# 세비야는 인물(타블라오 아홉)을 빼고 나면 **13장밖에 안 남는다.** 음악은 165초라
# **한 장을 12.7초씩** 봐야 한다. 검수자 지시 (2026-08-30) —
# *"세비야는 뿌옇게 나온 사진들도 사용해야 할 듯. 인물 사진들은 빼고"*
#
# **뿌연 것을 쓰는 것이 같은 사진을 12초 보는 것보다 낫다는 판단이다.**
도시별선 = {"세비야": 0.0}

# **그라나다·바르셀로나는 장수를 줄인다.**
#
# 그 구간 음악이 201초인데 인물을 빼고도 114장이 남아 **한 장에 1.8초**다.
# 다른 도시는 5~10초인데 여기만 눈이 못 따라간다. 검수자 지시 (2026-08-30) —
# *"그라나다와 바르셀로나는 적당히 추려내줘. 아주 잘 나온 사진들만 선별해도 좋고."*
#
# **또렷한 순으로 위에서 자른다.** 45장이면 한 장에 4.5초로 다른 도시와 비슷해진다.
# 바르셀로나는 이틀치를 합쳐서 센다.
최대장수 = {"그라나다": 24, "바르셀로나 (13일)": 10, "바르셀로나 (14일)": 11}
# ※ 실제 추림은 `장면배치.py` 가 한다 — 이 도구는 재고 연락표만 만든다.
K = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], float)

도시이름 = {
    "2005.12.08-마드리드": "마드리드",
    "2005.12.09-세고비아": "세고비아",
    "2005.12.10-세비야": "세비야",
    "2005.12.11-론다": "론다",
    "2005.12.12-그라나다": "그라나다",
    "2005.12.13-바르셀로나": "바르셀로나 (13일)",
    "2005.12.14-바르셀로나": "바르셀로나 (14일)",
}


def 또렷한정도(회색):
    """**윤곽이 얼마나 선명한가.** 라플라시안(이웃과의 차이)의 분산이다.
    초점이 안 맞거나 흔들리면 이웃과의 차이가 줄어 값이 작아진다."""
    return float(ndimage.convolve(회색, K, mode="reflect").var()) * 1e4


def 읽기(p):
    return np.asarray(Image.open(p).convert("L"), float) / 255.0


def 연락표(사진들, 낼곳, 값들, 문턱):
    """**작은 사진을 격자로 붙인다.** 사람이 눈으로 인물 사진을 고르라고 만드는 것이다.
    **선에 걸려 빠진 것은 붉은 테두리**를 둘러 왜 빠졌는지 보이게 한다."""
    COL, TH, PAD, LBL = 5, 300, 8, 18
    행 = (len(사진들) + COL - 1) // COL
    W = COL * (TH + PAD) + PAD
    H = 행 * (TH + PAD + LBL) + PAD
    장 = Image.new("RGB", (W, H), (18, 20, 26))
    d = ImageDraw.Draw(장)
    for i, p in enumerate(사진들):
        im = Image.open(p)
        im.thumbnail((TH, TH))
        x = PAD + (i % COL) * (TH + PAD)
        y = PAD + (i // COL) * (TH + PAD + LBL)
        장.paste(im, (x + (TH - im.width) // 2, y + (TH - im.height) // 2))
        이름 = os.path.basename(p).replace(".JPG", "")
        v = 값들[p]
        빠짐 = v < 문턱
        if 빠짐:
            d.rectangle([x, y, x + TH, y + TH], outline=(190, 60, 60), width=3)
        d.text((x + 2, y + TH + 3),
               "%s  %.0f%s" % (이름, v, "  ← 뿌옇다" if 빠짐 else ""),
               fill=(190, 90, 90) if 빠짐 else (190, 200, 214))
    장.save(낼곳)
    return W, H


def 자검사():
    실패 = []
    rng = np.random.default_rng(20051212)
    격자 = np.indices((256, 256)).sum(0) % 2 * 1.0        # 또렷한 격자무늬
    흐림 = ndimage.gaussian_filter(격자, 2.0)
    if 또렷한정도(격자) <= 또렷한정도(흐림):
        실패.append("① 흐린 그림이 더 또렷하게 나온다")
    if 또렷한정도(격자) != 또렷한정도(격자.copy()):
        실패.append("② 같은 그림을 두 번 쟀는데 값이 다르다")
    if 또렷한정도(np.full((256, 256), 0.5)) > 1e-6:
        실패.append("③ 단색인데 분산이 0 이 아니다")
    return 실패


if __name__ == "__main__":
    실패 = 자검사()
    print("자검사")
    if 실패:
        for s in 실패:
            print("   " + s)
        sys.exit("\n자검사 미달 — 이 자로는 안 고른다.")
    print("   → 통과 3/3\n")

    os.makedirs(낼밑, exist_ok=True)
    폴더들 = sorted(d for d in os.listdir(사진밑)
                    if os.path.isdir(os.path.join(사진밑, d)) and d in 도시이름)

    전체 = {}
    print("%-18s %5s %5s %5s   %s" % ("도시", "전체", "쓸것", "뿌옇", "연락표"))
    print("-" * 62)
    합 = [0, 0, 0]
    for d in 폴더들:
        ps = sorted(p for p in
                    (os.path.join(사진밑, d, f) for f in os.listdir(os.path.join(사진밑, d)))
                    if p.upper().endswith(".JPG"))
        값 = {p: 또렷한정도(읽기(p)) for p in ps}
        이름 = 도시이름[d]
        내선 = 도시별선.get(이름, 선)
        쓸것 = [p for p in ps if 값[p] >= 내선]
        f = os.path.join(낼밑, "연락표 - %s.png" % 이름)
        연락표(ps, f, 값, 내선)
        전체[이름] = [{"파일": os.path.basename(p), "폴더": d,
                       "또렷": round(값[p], 1), "쓸것": 값[p] >= 내선} for p in ps]
        합 = [합[0] + len(ps), 합[1] + len(쓸것), 합[2] + len(ps) - len(쓸것)]
        print("%-18s %5d %5d %5d   %s" % (이름, len(ps), len(쓸것),
                                          len(ps) - len(쓸것), os.path.basename(f)))
    print("-" * 62)
    print("%-18s %5d %5d %5d" % ("합계", *합))

    with open(os.path.join(낼밑, "또렷한 정도.json"), "w", encoding="utf-8") as fh:
        json.dump({"선": 선, "도시": 전체}, fh, ensure_ascii=False, indent=2)
    print("\n선 %.0f — 이보다 뿌연 것은 안 쓴다" % 선)
    print("★ 인물 사진은 이 도구가 못 고른다. 연락표를 보고 `뺄 사람 사진.txt` 에 적는다")
