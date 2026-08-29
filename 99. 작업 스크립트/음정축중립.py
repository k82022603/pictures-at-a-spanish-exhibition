# -*- coding: utf-8 -*-
"""
CQT 스펙트럼의 음정축 이미지 생성.
showcqt 는 x축을 로그 주파수에 선형으로 매핑하므로, C1~C7 6옥타브가
폭을 정확히 6등분한다. 건반을 그려 넣으면 화면이 곧 음정 자(尺)가 된다.
그리고 이 곡의 음집합 {B♭ C D E♭ F G A} 을 밝게, F♯ 을 붉게 표시한다.
"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1856, 46
OCT = 6                       # C1 ~ C7
# **글꼴 경로를 하나만 박아두지 않는다** (2026-08-20 정정).
# 옛 샌드박스(리눅스)의 경로가 박혀 있어서 **이 PC 에서 `cannot open resource`**
# 로 죽었다. 8-06 에 만든 `음정축.png` 가 남아 있어서 넉 달 동안 안 드러났다.
# **도구가 안 도는 것을 산출물이 가려주고 있었다.**
import os

FONTS = [
    "C:/Windows/Fonts/arialbd.ttf",                       # 윈도우
    "C:/Windows/Fonts/segoeuib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",   # 리눅스
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",      # 맥
]


def _font(크기):
    for p in FONTS:
        if os.path.exists(p):
            return ImageFont.truetype(p, 크기)
    raise SystemExit("굵은 글꼴을 못 찾았다 — FONTS 목록에 경로를 더하세요")


FS = _font(15)
FT = _font(12)

BLACK_PC = {1, 3, 6, 8, 10}                 # C♯ E♭ F♯ A♭ B♭
IN_KEY = {10, 0, 2, 3, 5, 7, 9}             # B♭ C D E♭ F G A — 이 곡의 음집합
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

img = Image.new("RGB", (W, H), (12, 15, 22))
d = ImageDraw.Draw(img)
sw = W / (OCT * 12.0)                       # 반음 하나의 폭

for i in range(OCT * 12):
    pc = i % 12
    x0 = i * sw
    x1 = (i + 1) * sw
    if pc in BLACK_PC:
        base = (26, 30, 40)
    else:
        base = (60, 66, 78)
    d.rectangle([x0, 6, x1 - 1, H - 15], fill=base)

# 옥타브 경계와 C 표기
for o in range(OCT + 1):
    x = o * 12 * sw
    d.line([(x, 0), (x, H - 1)], fill=(120, 132, 150), width=1)
    if o < OCT:
        lbl = "C%d" % (o + 1)
        d.text((x + 4, H - 14), lbl, font=FS, fill=(190, 200, 214))

img.save("음정축 - 중립.png")
print("음정축 - 중립.png %dx%d  반음폭 %.2fpx  (C1~C7 6옥타브)" % (W, H, sw))
print("중립 축 — 이 곡의 음집합 표시를 뺐다. Suno 판은 우리 음집합을 안 따른다")
