# -*- coding: utf-8 -*-
"""**원곡의 악장 경계를 다시 연주된 판으로 옮긴다.**

2026-08-29. 검수자 지적에서 나왔다 — *"2:10.50 뭐야? 노래가 잘리면서... 엉망이 되었네."*

## 왜 필요한가

`구조분석2.py` 는 **경계 후보**를 준다. 그런데 **어느 후보가 몇 번 악장 경계인지는
안 말해 준다.** 나는 원곡의 악장 길이 비율로 짐작했고, **재즈판은 Suno 가 다시
연주해 1부b 가 21초 늘어나 있어서** 그 비율이 안 맞았다. 악구 한가운데를 잘랐다.

**짐작을 없애는 방법은 하나다 — 두 음원의 시간축을 소리로 맞춘다.**
원곡의 40초가 재즈판의 몇 초인지 DTW 로 찾고, 알려진 경계를 그 길로 옮긴다.

## 자검사 — 답을 아는 문제

| 넣는 것 | 나와야 하는 값 |
|---|---|
| 원본 ↔ 자기 자신 | 옮긴 경계가 **원래 값 그대로** (±0.5초) |
| 원본 ↔ 1.25배 늘린 판 | 옮긴 경계가 **원래 값 × 1.25** (±2초) |

**미달이면 `sys.exit`.** 자를 안 재고 쓰지 않는다.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 화성

sys.stdout.reconfigure(encoding="utf-8")

N, HOP = 4096, 2048          # 크로마 창
STEP = 0.20                  # 정렬 격자 (초)


def 읽기(p):
    """**`화성.read_wav` 가 자료형을 본다.** 표본율도 같이 돌려준다 —
    Suno 는 48000, 우리 렌더는 44100 이다. **이것을 안 맞춰 하루를 버린 적이 있다.**"""
    sr, x = 화성.read_wav(p)
    return sr, (x.mean(1) if x.ndim == 2 else x)


def 크로마(m, sr):
    f = np.fft.rfftfreq(N, 1 / sr)
    쓸것 = (f > 55) & (f < 4200)
    반음 = np.zeros(len(f), int)
    반음[쓸것] = np.round(12 * np.log2(f[쓸것] / 440.0)).astype(int) % 12
    win = np.hanning(N)
    hop = int(STEP * sr)
    nf = max(1, (len(m) - N) // hop + 1)
    C = np.zeros((nf, 12))
    for i in range(nf):
        S = np.abs(np.fft.rfft(m[i * hop:i * hop + N] * win))
        for p in range(12):
            C[i, p] = S[쓸것 & (반음 == p)].sum()
    C /= np.maximum(np.linalg.norm(C, axis=1, keepdims=True), 1e-9)
    return C


def 정렬(A, B):
    """DTW. **A 의 프레임 i 가 B 의 어느 프레임인지** 돌려준다."""
    D = 1.0 - A @ B.T                       # 코사인 거리
    n, m = D.shape
    큰 = 1e18
    acc = np.full((n + 1, m + 1), 큰)
    acc[0, 0] = 0.0
    for i in range(1, n + 1):
        d = D[i - 1]
        prev, cur = acc[i - 1], acc[i]
        for j in range(1, m + 1):
            cur[j] = d[j - 1] + min(prev[j], cur[j - 1], prev[j - 1])
    # 되짚기
    i, j = n, m
    map_ = np.zeros(n, int)
    while i > 0 and j > 0:
        map_[i - 1] = j - 1
        cands = (acc[i - 1, j], acc[i, j - 1], acc[i - 1, j - 1])
        k = int(np.argmin(cands))
        if k == 0:
            i -= 1
        elif k == 1:
            j -= 1
        else:
            i -= 1
            j -= 1
    return map_


def 옮기기(원본, 새판, 경계들, sr_o=None, sr_n=None):
    """원본의 시각 `경계들`(초)이 새판의 몇 초인지."""
    A = 크로마(원본, sr_o)
    B = 크로마(새판, sr_n)
    map_ = 정렬(A, B)
    out = []
    for t in 경계들:
        i = min(int(round(t / STEP)), len(map_) - 1)
        out.append(map_[i] * STEP)
    return out


def 자검사(허용1=0.5, 허용2=2.0):
    """**답을 아는 문제 둘.** 짧은 신호를 만들어 쓴다 — 파일에 안 기댄다."""
    sr = 22050
    rng = np.random.default_rng(20051212)
    # 12초짜리 신호: 3초마다 화음이 바뀐다
    구간 = [[261.6, 329.6, 392.0], [293.7, 349.2, 440.0],
            [220.0, 261.6, 329.6], [246.9, 311.1, 370.0]]
    x = []
    for hz in 구간:
        t = np.arange(int(3.0 * sr)) / sr
        s = sum(np.sin(2 * np.pi * f * t) for f in hz)
        x.append(s * (1 + 0.05 * rng.standard_normal(len(t))))
    x = np.concatenate(x)
    경계 = [3.0, 6.0, 9.0]

    실패 = []
    a = 옮기기(x, x, 경계, sr, sr)
    if max(abs(np.array(a) - 경계)) > 허용1:
        실패.append("① 자기 자신과 정렬했는데 경계가 %s (기대 %s)" % (a, 경계))

    n = int(len(x) * 1.25)                                  # 1.25배 늘린 판
    y = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
    b = 옮기기(x, y, 경계, sr, sr)
    기대 = [t * 1.25 for t in 경계]
    if max(abs(np.array(b) - 기대)) > 허용2:
        실패.append("② 1.25배 판에서 %s (기대 %s)" % (b, 기대))
    return 실패, a, b


if __name__ == "__main__":
    실패, a, b = 자검사()
    print("자검사")
    print("   ① 자기 자신     %s   (기대 [3.0, 6.0, 9.0])" % [round(v, 2) for v in a])
    print("   ② 1.25배 늘린 판 %s   (기대 [3.75, 7.5, 11.25])" % [round(v, 2) for v in b])
    if 실패:
        for s in 실패:
            print("   " + s)
        sys.exit("\n자검사 미달 — 이 자로는 옮기지 않는다.")
    print("   → 통과\n")

    if len(sys.argv) > 3:
        so, o = 읽기(sys.argv[1])
        sn, n_ = 읽기(sys.argv[2])
        경계 = [float(v) for v in sys.argv[3:]]
        r = 옮기기(o, n_, 경계, so, sn)
        print("[옮김] %s → %s" % (sys.argv[1], sys.argv[2]))
        for t, v in zip(경계, r):
            print("   원본 %7.2f초  →  새판 %7.2f초" % (t, v))
