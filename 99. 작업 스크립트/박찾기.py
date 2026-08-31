# -*- coding: utf-8 -*-
"""**음악에서 박을 찾는다 — 컷을 박에 붙이려고.**

2026-08-30. 검수자 — *"박에 맞춰 컷 ... 동영상 다시 구워 주세요."*

## 무엇을 하나

**소리가 새로 나기 시작하는 순간**(온셋)을 찾고, 그 간격에서 **박의 주기**를 재고,
**박이 놓일 시각을 격자로 깐다.** 컷을 그 격자에 붙이면 화면이 음악을 탄다.

## 왜 온셋만으로는 안 되나

**온셋은 박이 아니다.** 재즈는 박 사이에도 음이 들어가고(싱코페이션),
어떤 박에는 아무도 안 친다. **온셋을 그대로 컷 시각으로 쓰면 불규칙해진다.**

**그래서 주기를 먼저 재고 격자를 깐다** — 온셋의 자기상관에서 가장 센 주기를 찾고,
그 주기로 격자를 만든 뒤 **격자를 좌우로 밀어 온셋과 가장 잘 맞는 자리**를 고른다.

## 도시마다 따로 잰다

**토막마다 다른 재즈다.** 프롬나드는 피아노 솔로이고 바르셀로나는 콜트레인이다.
**한 빠르기로 전곡을 덮으면 어느 쪽도 안 맞는다.**

## 자검사 — 답을 아는 문제 넷

| 넣는 것 | 나와야 하는 값 |
|---|---|
| **120 BPM 딸깍이** | 주기 **0.50초** (±0.02) |
| 그 딸깍이의 격자 | 딸깍 시각과 **±0.03초** 안에서 맞는다 |
| **90 BPM 딸깍이** | 주기 **0.667초** (±0.03) |
| 무음 | 온셋 **0개** |

**미달이면 `sys.exit`.** 자를 안 재고 쓰지 않는다.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 화성

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
음원 = os.path.join(HERE, "..", "산출물", "20260829 - 재즈 2판",
                    "전곡 재즈 2판 - 원본 그대로 · 무음 1.5초.wav")
구간표 = os.path.join(HERE, "..", "산출물", "20260829 - 재즈 2판", "도시 구간.json")
낼곳 = os.path.join(HERE, "..", "산출물", "20260830 - 사진 고르기", "박.json")

N, HOP = 2048, 512
최소BPM, 최대BPM = 60.0, 200.0


def 온셋세기(m, sr):
    """**스펙트럼이 커지는 양**(spectral flux). 소리가 새로 날 때 솟는다."""
    w = np.hanning(N)
    nf = max(1, (len(m) - N) // HOP + 1)
    S = np.empty((nf, N // 2 + 1))
    for i in range(nf):
        S[i] = np.abs(np.fft.rfft(m[i * HOP:i * HOP + N] * w))
    S = np.log1p(S)
    flux = np.maximum(0.0, np.diff(S, axis=0)).sum(1)
    if flux.std() > 0:
        flux = (flux - flux.mean()) / flux.std()
    # **프레임 하나가 몇 초인지가 아니라 「그 프레임이 언제인지」를 돌려준다.**
    # `diff` 로 i 번째 값은 창 i 와 i+1 사이의 변화이므로 **창 i+1 의 한가운데**가 그 시각이다.
    # 이것을 안 맞춰 격자가 0.05초 어긋난 적이 있다 (2026-08-30).
    t = ((np.arange(len(flux)) + 1) * HOP + N / 2.0) / sr
    return flux, t


def 주기(flux, t):
    """온셋 세기의 자기상관에서 가장 센 주기(초)."""
    if len(flux) < 8:
        return None
    fps = 1.0 / (t[1] - t[0])
    x = flux - flux.mean()
    ac = np.correlate(x, x, "full")[len(x) - 1:]
    lo = max(1, int(fps * 60.0 / 최대BPM))
    hi = min(len(ac) - 1, int(fps * 60.0 / 최소BPM))
    if hi <= lo:
        return None
    k = lo + int(np.argmax(ac[lo:hi]))
    return k / fps


def 격자(flux, t, T, 시작초):
    """주기 `T` 짜리 격자를 좌우로 밀어 **온셋과 가장 잘 맞는 자리**를 고른다.

    **미는 폭을 촘촘히 훑는다** — 24칸으로 훑었더니 0.05초가 어긋났다.
    """
    if len(flux) < 4:
        return []
    처음, 끝 = float(t[0]), float(t[-1])
    n = int((끝 - 처음) / T)
    if n < 2:
        return []
    최고, 최고밀기 = -1e18, 0.0
    for 밀기 in np.linspace(0, T, 400, endpoint=False):
        때 = 처음 + 밀기 + np.arange(n) * T
        i = np.clip(np.searchsorted(t, 때), 0, len(flux) - 1)
        v = float(flux[i].sum())
        if v > 최고:
            최고, 최고밀기 = v, float(밀기)
    격자때 = 처음 + 최고밀기 + np.arange(n) * T

    # **계통 오차를 없앤다.** 창 한가운데를 시각으로 삼기 때문에 격자 전체가
    # 한 프레임쯤 밀린다. **온셋 봉우리와의 어긋남 중앙값만큼 통째로 되민다.**
    # 봉우리 하나하나에 붙이지 않는 이유 — 그러면 격자가 아니라 온셋 목록이 된다.
    봉우리 = []
    for i in range(1, len(flux) - 1):
        if flux[i] > flux[i - 1] and flux[i] >= flux[i + 1] and flux[i] > 0.5:
            봉우리.append(t[i])
    if len(봉우리) >= 3:
        봉우리 = np.array(봉우리)
        차 = np.array([봉우리[np.argmin(np.abs(봉우리 - g))] - g for g in 격자때])
        차 = 차[np.abs(차) < T / 3.0]
        if len(차) >= 3:
            격자때 = 격자때 + float(np.median(차))
    return [시작초 + v for v in 격자때]


def 딸깍이(bpm, 길이=12.0, sr=48000):
    """답을 아는 신호 — 일정한 간격으로 짧게 친다."""
    x = np.zeros(int(길이 * sr))
    T = 60.0 / bpm
    때 = []
    t = 0.0
    while t < 길이 - 0.2:
        s = int(t * sr)
        n = int(0.05 * sr)
        tt = np.arange(n) / sr
        x[s:s + n] += np.sin(2 * np.pi * 1200 * tt) * np.exp(-tt * 60)
        때.append(t)
        t += T
    return x, 때


def 자검사():
    실패 = []
    sr = 48000
    for bpm, 허용 in ((120.0, 0.02), (90.0, 0.03)):
        x, 때 = 딸깍이(bpm, sr=sr)
        f, tt = 온셋세기(x, sr)
        T = 주기(f, tt)
        if T is None or abs(T - 60.0 / bpm) > 허용:
            실패.append("① %g BPM 에서 주기 %s (기대 %.3f)"
                        % (bpm, "없음" if T is None else "%.3f" % T, 60.0 / bpm))
            continue
        g = 격자(f, tt, T, 0.0)
        if not g:
            실패.append("② %g BPM 격자가 비었다" % bpm)
            continue
        어긋남 = max(min(abs(t - c) for c in 때) for t in g[:8])
        if 어긋남 > 0.03:
            실패.append("② %g BPM 격자가 딸깍과 %.3f초 어긋난다" % (bpm, 어긋남))

    f, _ = 온셋세기(np.zeros(int(5 * sr)), sr)
    if float(np.abs(f).max()) > 1e-6:
        실패.append("④ 무음인데 온셋이 잡힌다")
    return 실패


def 도시별박(m, sr, 구간):
    나온것 = []
    for g in 구간:
        a, b = int(g["시작"] * sr), int(g["끝"] * sr)
        f, tt = 온셋세기(m[a:b], sr)
        T = 주기(f, tt)
        if T is None:
            나온것.append({"도시": g["도시"], "주기": None, "BPM": None, "박": []})
            continue
        박 = [t for t in 격자(f, tt, T, g["시작"]) if g["시작"] <= t <= g["끝"]]
        나온것.append({"도시": g["도시"], "주기": round(T, 4),
                       "BPM": round(60.0 / T, 1), "박": [round(t, 3) for t in 박]})
    return 나온것


if __name__ == "__main__":
    실패 = 자검사()
    print("자검사")
    if 실패:
        for s in 실패:
            print("   " + s)
        sys.exit("\n자검사 미달 — 이 자로는 박을 안 찾는다.")
    print("   → 통과 4/4\n")

    sr, x = 화성.read_wav(음원)
    m = x.mean(1) if x.ndim == 2 else x
    구간 = json.load(open(구간표, encoding="utf-8"))["구간"]
    결과 = 도시별박(m, sr, 구간)

    print("%-22s %8s %8s %8s" % ("구간", "주기", "BPM", "박 수"))
    print("-" * 50)
    for r in 결과:
        print("%-22s %7.3f초 %8.1f %8d"
              % (r["도시"], r["주기"] or 0, r["BPM"] or 0, len(r["박"])))
    with open(낼곳, "w", encoding="utf-8") as f:
        json.dump({"구간": 결과}, f, ensure_ascii=False, indent=1)
    print("\n→ %s" % os.path.basename(낼곳))
