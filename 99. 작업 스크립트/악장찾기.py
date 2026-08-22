# -*- coding: utf-8 -*-
"""**이어붙인 Suno 음원에서 악장 경계를 찾는다.**

2026-08-22. 조각 경계 넷은 안다(우리가 잘라 올렸으니까). **문제는 조각 안이다** —
1부b 안에 악장 셋, 2부 안에 셋, 3부 안에 둘이 들어 있는데
**Suno 가 그것들을 어디로 옮겼는지 모른다.**

**계산으로 적지 않는다**(`CLAUDE.md` v4.16). 화성이 바뀌는 자리를 실측으로 찾는다.
우리 곡의 상대 위치 ±6초 안에서 **크로마가 가장 크게 바뀌는 지점**을 고른다.
"""
import os
import sys

import numpy as np
from scipy import signal as sg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 화성

sys.stdout.reconfigure(encoding="utf-8")
C = "../산출물/20260822 - 0악장을 다시 만든다"
sr, x = 화성.read_wav(C + "/이어붙인 것/전곡 A - 그대로 이은 것.wav")
SR = sr
m = x.mean(axis=1).astype(np.float64)

# 조각 경계 — 이어붙일 때 나온 값
조각경계 = [0.0, 50.56, 161.14, 326.60, 526.50, len(m) / SR]
# 우리 곡에서 각 조각 안의 악장 경계 (조각 시작으로부터 몇 초)
안쪽 = {1: [40.0, 55.0],          # 1부b: 1→2악장(50s), 2→3악장(65s) → 조각 시작 50 기준
        2: [100.0, 115.0],        # 2부: 4→5(260s), 5→6(275s) → 조각 시작 160 기준
        3: [100.0]}               # 3부: 7→8(425s) → 조각 시작 325 기준
# 조각 길이가 달라졌으므로 비율로 옮긴다
우리길이 = {1: 110.0, 2: 165.0, 3: 200.0}


def 크로마열(seg, 창=1.0):
    h = int(창 * SR)
    n = (len(seg) // h) * h
    out = []
    for i in range(0, n, h):
        s = seg[i:i + h]
        f, t, Z = sg.stft(s, SR, nperseg=1 << 13, noverlap=1 << 12)
        P = (np.abs(Z) ** 2).mean(axis=1)
        ok = (f > 55) & (f < 4200)
        ff, PP = f[ok], P[ok]
        pc = np.rint(12 * np.log2(ff / 440.0) + 69).astype(int) % 12
        c = np.array([PP[pc == k].sum() for k in range(12)])
        out.append(c / (c.sum() + 1e-20))
    return np.array(out)


def 급변(seg, 후보초, 폭=6.0):
    """후보 시각 ±폭 에서 앞뒤 4초 크로마가 가장 크게 갈리는 지점."""
    best, bt = 2.0, 후보초
    for t in np.arange(후보초 - 폭, 후보초 + 폭, 0.5):
        k = int(t * SR); w = int(4 * SR)
        if k - w < 0 or k + w > len(seg):
            continue
        a = 크로마열(seg[k - w:k], 4.0)[0]
        b = 크로마열(seg[k:k + w], 4.0)[0]
        s = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
        if s < best:
            best, bt = s, t
    return bt, best


print("악장 경계 찾기 — 조각 경계 넷은 확정, 안쪽 다섯은 실측")
print("-" * 66)
경계 = [0.0]
for i in range(5):
    조각시작, 조각끝 = 조각경계[i], 조각경계[i + 1]
    if i in 안쪽:
        길이 = 조각끝 - 조각시작
        비 = 길이 / 우리길이[i]
        for off in 안쪽[i]:
            후보 = 조각시작 + off * 비
            t, s = 급변(m, 후보)
            print("  조각%d 안  후보 %6.2f초 → **%6.2f초**  (화성 닮음 %.3f)" % (i, 후보, t, s))
            경계.append(t)
    경계.append(조각끝)
경계 = sorted(set([0.0] + 경계 + [len(m) / SR]))
print()
print("찾은 경계 %d개" % len(경계))
print(" ".join("%.2f" % t for t in 경계))
np.save("악장경계_Suno.npy", np.array(경계))
