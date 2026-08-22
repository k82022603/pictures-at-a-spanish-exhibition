# -*- coding: utf-8 -*-
"""**두 판을 자세히 견준다** — 검수자 선택과 지표 추천이 갈린 자리를 본다.

2026-08-22. 「닮음 평균」 하나로는 왜 귀가 다르게 들었는지 설명이 안 된다.
**구간을 셋으로 잘라 보고, 음량이 곡 안에서 어떻게 움직이는지 본다.**
"""
import os
import sys

import numpy as np
from scipy import signal as sg

import Suno대조 as S
import 타악점검 as T

sys.stdout.reconfigure(encoding="utf-8")
SR = 44100


def 대역(m):
    """저·중·고 세 대역의 에너지 비율."""
    f, P = sg.welch(m, SR, nperseg=8192)
    tot = P.sum() + 1e-20
    lo = P[(f >= 20) & (f < 250)].sum() / tot
    mi = P[(f >= 250) & (f < 2000)].sum() / tot
    hi = P[(f >= 2000) & (f < 12000)].sum() / tot
    return lo, mi, hi


def 크레스트(m):
    """peak / RMS — 다이내믹이 살아 있는가. 클수록 살아 있다."""
    return 20 * np.log10(np.abs(m).max() / (np.sqrt((m ** 2).mean()) + 1e-12))


def 음량곡선(m, 창=4.0):
    h = int(창 * SR)
    n = (len(m) // h) * h
    e = np.sqrt((m[:n].reshape(-1, h) ** 2).mean(axis=1))
    return 20 * np.log10(e + 1e-12)


def 재기(이름, p, 기준, 목표):
    m = S.읽기(p)
    c = S.창별크로마(m)
    v = S.닮음(기준, c)
    k = len(v) // 3
    앞, 중, 뒤 = v[:k].mean(), v[k:2 * k].mean(), v[2 * k:].mean()
    lo, mi, hi = 대역(m)
    q = 음량곡선(m)
    print("  %-10s %6.2f초 (%+6.2f)  닮음 %.3f  [앞 %.3f 중 %.3f 뒤 %.3f]"
          % (이름, len(m) / SR, len(m) / SR - 목표, v.mean(), 앞, 중, 뒤))
    print("             RMS %6.1f dB  크레스트 %4.1f dB  음량폭 %4.1f dB"
          "  대역 저%.2f 중%.2f 고%.2f  저역타격 %.2f"
          % (20 * np.log10(np.sqrt((m ** 2).mean()) + 1e-12), 크레스트(m),
             q.max() - q.min(), lo, mi, hi, T.킥(m)))
    return m, v, q


if __name__ == "__main__":
    B = "../산출물/20260821 - 전곡을 Suno 에 넘긴다/Suno 전곡 맡기기"
    C = "../산출물/20260822 - 0악장을 다시 만든다"
    일 = [
        ("0악장", 50.0,  C + "/0악장 안A - 베이스가 먼저.wav",
         [("Suno-02 ★검수자", C + "/받은 것 - 0악장/0악장 Suno-02.wav"),
          ("Suno-04 지표",   C + "/받은 것 - 0악장/0악장 Suno-04.wav")]),
        ("1부b", 110.0, B + "/1부b (1~3악장) 0.50-2.40.wav",
         [("Suno-03 ★검수자", B + "/받은 것 - 1부b/1부b Suno-03.wav"),
          ("Suno-04 지표",   B + "/받은 것 - 1부b/1부b Suno-04.wav")]),
        ("2부",  165.0, B + "/2부 (4~6악장) 2.40-5.25.wav",
         [("Suno-03 둘다",   B + "/받은 것 - 2부/2부 Suno-03.wav")]),
        ("3부",  200.0, B + "/3부 (7~8악장) 5.25-8.45.wav",
         [("Suno-04 둘다",   B + "/받은 것 - 3부/3부 Suno-04.wav")]),
        ("4부",   55.0, B + "/4부 (9악장) 8.45-9.40.wav",
         [("Suno-03 ★검수자", B + "/받은 것 - 4부/4부 Suno-03.wav"),
          ("Suno-01 지표",   B + "/받은 것 - 4부/4부 Suno-01.wav")]),
    ]
    for 이름, 목표, 원본, 판들 in 일:
        a = S.읽기(원본)
        기준 = S.창별크로마(a)
        print("\n=== %s (우리 %.0f초)" % (이름, 목표))
        재기("우리 원본", 원본, 기준, 목표)
        for n, p in 판들:
            if os.path.exists(p):
                재기(n, p, 기준, 목표)
