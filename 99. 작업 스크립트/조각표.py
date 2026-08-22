# -*- coding: utf-8 -*-
"""**다섯 조각의 모든 판을 한 표로.** 이어붙이기 전에 무엇을 고를지 정하는 자료.

2026-08-22. 「가장 좋은 판」을 손으로 옮겨 적다가 2부 값을 틀렸다.
**표는 손으로 안 적고 여기서 낸다.**
"""
import os
import sys

import numpy as np
from scipy import signal as sg

import 화성
import Suno대조 as S
import 타악점검 as T

sys.stdout.reconfigure(encoding="utf-8")
SR = 44100
B = "../산출물/20260821 - 전곡을 Suno 에 넘긴다/Suno 전곡 맡기기"
C = "../산출물/20260822 - 0악장을 다시 만든다"

조각 = [
    ("0악장",  50.0, C + "/0악장 안A - 베이스가 먼저.wav", C + "/받은 것 - 0악장/0악장 Suno-%s.wav"),
    ("1부b",  110.0, B + "/1부b (1~3악장) 0.50-2.40.wav",  B + "/받은 것 - 1부b/1부b Suno-%s.wav"),
    ("2부",   165.0, B + "/2부 (4~6악장) 2.40-5.25.wav",   B + "/받은 것 - 2부/2부 Suno-%s.wav"),
    ("3부",   200.0, B + "/3부 (7~8악장) 5.25-8.45.wav",   B + "/받은 것 - 3부/3부 Suno-%s.wav"),
    ("4부",    55.0, B + "/4부 (9악장) 8.45-9.40.wav",     B + "/받은 것 - 4부/4부 Suno-%s.wav"),
]

print("조각  판   길이     차이    닮음   끝뺀   0.90↑   밖    RMS    저역  고역")
print("-" * 78)
for 이름, 목표, 원본, 꼴 in 조각:
    a = S.읽기(원본)
    기준 = S.창별크로마(a)
    for n in ["01", "02", "03", "04"]:
        p = 꼴 % n
        if not os.path.exists(p):
            continue
        m = S.읽기(p)
        c = S.창별크로마(m)
        v = S.닮음(기준, c)
        rms = 20 * np.log10(np.sqrt((m ** 2).mean()) + 1e-12)
        print("%-5s %s  %6.2f  %+6.2f  %.3f  %.3f  %3.0f%%  %.3f  %6.1f  %.2f  %.2f"
              % (이름, n, len(m) / SR, len(m) / SR - 목표,
                 v.mean(), v[:-1].mean(), 100 * (v >= 0.90).mean(),
                 S.밖(np.mean(c, axis=0)), rms, T.킥(m), T.심벌(m)))
    # 우리 원본도 같은 줄로
    c0 = S.창별크로마(a)
    print("%-5s 우리 %6.2f   ----   1.000  1.000  100%%  %.3f  %6.1f  %.2f  %.2f"
          % (이름, len(a) / SR, S.밖(np.mean(c0, axis=0)),
             20 * np.log10(np.sqrt((a ** 2).mean()) + 1e-12), T.킥(a), T.심벌(a)))
    print("-" * 78)
