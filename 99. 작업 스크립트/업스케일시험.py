# -*- coding: utf-8 -*-
"""**업스케일이 얼마나 값을 하는가를 우리 사진으로 잰다** — Topaz 를 사기 전에.

## 왜 이 방법인가

**「AI 업스케일러가 좋다」는 말은 많은데, 우리 2005년 디카 사진에 얼마나 듣는지는
아무도 모른다.** 그렇다고 $29 를 먼저 낼 수는 없다.

**답이 우리 사진 안에 있다** — **2048×1536 짜리가 일곱 장 있다.**

| 단계 | 무엇 |
|---|---|
| 1 | 그 일곱을 **1024×768 로 줄인다** — 나머지 사진과 같은 조건으로 만든다 |
| 2 | 다시 **2048×1536 으로 키운다** (지금 쓰는 Lanczos 방식) |
| 3 | **진짜 원본과 견준다** |

**2에서 3까지의 거리가 「업스케일러가 되찾아야 할 것」의 전부**다.
**AI 업스케일러라도 그 이상은 못 한다.** 그러니 이 값이 **천장**이다.

## 무엇을 재나

| | |
|---|---|
| **SSIM** | 원본과 얼마나 닮았는가. 1.0 이면 똑같다 |
| **선명도** | 가장자리가 얼마나 또렷한가 (라플라시안 분산). **이것이 업스케일의 목적** |

## 자기검사 — 셋
"""
import io
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def 회색(im):
    return np.asarray(im.convert("L"), dtype=np.float64)


def ssim(a, b):
    """두 그림이 얼마나 닮았는가. `PoC검증.py` 와 같은 방식(8×8 창)."""
    from scipy.ndimage import uniform_filter
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mu1, mu2 = uniform_filter(a, 8), uniform_filter(b, 8)
    s11 = uniform_filter(a * a, 8) - mu1 * mu1
    s22 = uniform_filter(b * b, 8) - mu2 * mu2
    s12 = uniform_filter(a * b, 8) - mu1 * mu2
    return float((((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) /
                  ((mu1 ** 2 + mu2 ** 2 + C1) * (s11 + s22 + C2))).mean())


def 선명도(a):
    """가장자리가 얼마나 또렷한가. **클수록 선명하다.**"""
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], float)
    from scipy.signal import convolve2d
    return float(convolve2d(a, k, mode="valid").var())


def 자검사():
    """**답을 아는 것으로 잰다.**"""
    rng = np.random.default_rng(7)
    a = rng.random((240, 320)) * 255
    결과 = [
        ("자기 자신과의 SSIM 이 1 인가",
         None if abs(ssim(a, a) - 1) < 1e-6 else "%.4f" % ssim(a, a)),
        ("흐리게 하면 SSIM 이 떨어지는가", None),
        ("흐리게 하면 선명도가 떨어지는가", None),
    ]
    from scipy.ndimage import gaussian_filter
    b = gaussian_filter(a, 2.0)
    if ssim(a, b) >= 0.99:
        결과[1] = (결과[1][0], "안 떨어진다 (%.4f)" % ssim(a, b))
    if 선명도(b) >= 선명도(a):
        결과[2] = (결과[2][0], "안 떨어진다")
    print("=== 자기검사 ===")
    for 이, 틀 in 결과:
        print("  %-28s %s" % (이, "OK" if 틀 is None else "✗ " + 틀))
    if any(x for _, x in 결과):
        sys.exit("\n**자가 틀렸다. 재지 않는다.**")
    print("  → **셋 다 통과**\n")


def main():
    자검사()
    import csv
    P = os.path.join(ROOT, "산출물", "20260820 - 가락은 내가 입힌다", "사진 목록.csv")
    큰것 = [x for x in csv.DictReader(io.open(P, encoding="utf-8-sig"))
            if int(x["가로"]) >= 2048 or int(x["세로"]) >= 2048]
    if not 큰것:
        sys.exit("2048 짜리 사진이 없다")

    소재 = os.path.join(ROOT, "2005년 12월 스페인")
    print("=== 2048 짜리 %d장으로 잰다 ===" % len(큰것))
    print("  %-16s %-12s %10s %12s %12s"
          % ("파일", "원본", "되키운 SSIM", "원본 선명도", "되키운 선명도"))
    표 = []
    for x in 큰것:
        p = os.path.join(소재, x["폴더"], x["파일"])
        원 = Image.open(p).convert("RGB")
        작 = 원.resize((원.width // 2, 원.height // 2), Image.LANCZOS)
        되 = 작.resize(원.size, Image.LANCZOS)
        A, B = 회색(원), 회색(되)
        s, so, sd = ssim(A, B), 선명도(A), 선명도(B)
        표.append((s, so, sd))
        print("  %-16s %-12s %10.4f %12.0f %12.0f"
              % (x["파일"], "%sx%s" % (x["가로"], x["세로"]), s, so, sd))

    S = np.array(표)
    print("\n=== 평균 ===")
    print("  SSIM              **%.4f**" % S[:, 0].mean())
    print("  선명도  원본 %.0f  →  되키운 것 %.0f  (**%.0f%% 만 남는다**)"
          % (S[:, 1].mean(), S[:, 2].mean(), S[:, 2].mean() / S[:, 1].mean() * 100))
    잃음 = 1 - S[:, 2].mean() / S[:, 1].mean()
    print("\n=== 뜻 ===")
    print("  **2배로 키우면 선명도의 %.0f%% 를 잃는다.**" % (잃음 * 100))
    print("  **업스케일러가 되찾을 수 있는 최대치가 그 %.0f%% 다.**" % (잃음 * 100))
    if 잃음 < 0.25:
        print("  → **잃는 것이 적다.** $29 를 쓸 값이 있는지 다시 생각할 자리다")
    elif 잃음 < 0.55:
        print("  → **애매하다.** 무료 도구로 얼마나 되찾는지 보고 정한다")
    else:
        print("  → **많이 잃는다.** 업스케일이 눈에 띄게 값을 할 자리다")


if __name__ == "__main__":
    main()
