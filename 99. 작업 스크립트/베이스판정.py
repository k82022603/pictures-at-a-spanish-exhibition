# -*- coding: utf-8 -*-
"""**더블베이스 판인가 — 소리로 잰다.**

2026-08-29. 검수자 지적에서 나왔다 — *"더블베이스만 있는 소리 듣고 싶다고!!!!"* ·
*"재즈 연주에서 더블베이스가 어떻게 이용되는지 잘 모르는 듯 ... 활을 사용하지 않는 연주로."*

## 무엇을 재나 — 넷

| 재는 것 | 무슨 뜻인가 | 더블베이스 판이면 |
|---|---|---|
| **무게 중심** (Hz) | 소리의 에너지가 어느 높이에 몰려 있나 | **낮다.** 다른 악기가 끼면 올라간다 |
| **낮은 쪽 몫** (300 Hz 아래) | 저역이 전체의 몇 할인가 | **높다** |
| **뜯는 횟수** (초당) | 음이 새로 나기 시작하는 빈도 | **워킹이면 초당 2 안팎** — 한 마디에 네 음 |
| **박이 고른가** | 뜯는 간격이 얼마나 일정한가 | **워킹이면 고르다.** 활로 긋는 판은 안 고르다 |

**활(arco)로 그으면 뜯는 횟수가 뚝 떨어지고 간격이 흐트러진다.** 그것이 「활을 안 쓴다」를 숫자로 보는 방법이다.

## 자검사 — 답을 아는 문제 셋

| 넣는 것 | 나와야 하는 값 |
|---|---|
| 80 Hz 사인파 | 무게 중심 ≈ 80 Hz · 낮은 쪽 몫 ≈ 1.0 |
| 2000 Hz 사인파 | 무게 중심 ≈ 2000 Hz · 낮은 쪽 몫 ≈ 0.0 |
| **초당 2번 뜯는 소리** | **뜯는 횟수 ≈ 2.0 · 박이 고름 ≈ 1.0** |

**미달이면 `sys.exit`.** 자를 안 재고 쓰지 않는다.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 화성

sys.stdout.reconfigure(encoding="utf-8")

N, HOP = 2048, 512


def 읽기(p):
    sr, x = 화성.read_wav(p)
    return sr, (x.mean(1) if x.ndim == 2 else x)


def 스펙트럼(m, sr):
    win = np.hanning(N)
    nf = max(1, (len(m) - N) // HOP + 1)
    S = np.empty((nf, N // 2 + 1))
    for i in range(nf):
        S[i] = np.abs(np.fft.rfft(m[i * HOP:i * HOP + N] * win))
    return S, np.fft.rfftfreq(N, 1 / sr)


def 재기(m, sr):
    S, f = 스펙트럼(m, sr)
    합 = S.sum(1)
    쓸것 = 합 > np.percentile(합, 20)          # 무음 구간은 뺀다
    무게중심 = float((S[쓸것] @ f).sum() / max(합[쓸것].sum(), 1e-9))
    낮은쪽 = float(S[쓸것][:, f < 300].sum() / max(S[쓸것].sum(), 1e-9))

    # 뜯는 시점 — 스펙트럼이 커지는 순간만 센다
    플럭스 = np.maximum(0.0, np.diff(np.log1p(S.sum(1))))
    문턱 = 플럭스.mean() + 1.2 * 플럭스.std()
    시점 = []
    최소간격 = int(0.12 * sr / HOP)
    i = 0
    while i < len(플럭스):
        if 플럭스[i] > 문턱:
            시점.append(i * HOP / sr)
            i += 최소간격
        else:
            i += 1
    길이 = len(m) / sr
    횟수 = len(시점) / max(길이, 1e-9)
    if len(시점) >= 4:
        간격 = np.diff(시점)
        고름 = float(1.0 - min(1.0, np.std(간격) / max(np.mean(간격), 1e-9)))
    else:
        고름 = 0.0
    return 무게중심, 낮은쪽, 횟수, 고름


def 자검사(허용=0.15):
    sr = 48000
    t = np.arange(int(6.0 * sr)) / sr
    실패 = []

    c, l, _, _ = 재기(np.sin(2 * np.pi * 80 * t), sr)
    if abs(c - 80) > 25 or l < 0.9:
        실패.append("① 80 Hz 사인파에서 무게중심 %.0f Hz · 낮은쪽 %.2f" % (c, l))

    c, l, _, _ = 재기(np.sin(2 * np.pi * 2000 * t), sr)
    if abs(c - 2000) > 120 or l > 0.1:
        실패.append("② 2000 Hz 사인파에서 무게중심 %.0f Hz · 낮은쪽 %.2f" % (c, l))

    # 초당 두 번 뜯는 소리
    x = np.zeros(int(10.0 * sr))
    for k in range(20):
        s = int(k * 0.5 * sr)
        n = int(0.35 * sr)
        tt = np.arange(n) / sr
        x[s:s + n] += np.sin(2 * np.pi * 98 * tt) * np.exp(-tt * 6)
    _, _, h, e = 재기(x, sr)
    if abs(h - 2.0) > 0.3 or e < 0.85:
        실패.append("③ 초당 2번 뜯는 소리에서 %.2f 회/초 · 고름 %.2f" % (h, e))
    return 실패


if __name__ == "__main__":
    실패 = 자검사()
    print("자검사")
    if 실패:
        for s in 실패:
            print("   " + s)
        sys.exit("\n자검사 미달 — 이 자로는 재지 않는다.")
    print("   → 통과 3/3\n")

    print("%-26s %8s %8s %8s %8s" % ("파일", "무게중심", "낮은쪽", "뜯기/초", "고름"))
    print("-" * 62)
    for p in sys.argv[1:]:
        sr, m = 읽기(p)
        c, l, h, e = 재기(m, sr)
        print("%-26s %7.0f㎐ %7.1f%% %8.2f %8.2f"
              % (os.path.basename(p)[:26], c, l * 100, h, e))
