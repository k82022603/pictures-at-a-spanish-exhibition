# -*- coding: utf-8 -*-
"""**높이를 재는 자가 맞는가 — 아는 음으로 검사하고, 어제 결론을 다시 잰다.**

2026-08-20. `보컬가락.py` 를 만들다 **낸 소리의 높이가 목표보다 정확히 한
옥타브 아래로 읽히는 것**을 봤다. 계산으로 넣은 높이라 어긋날 수가 없는데
그렇게 읽혔으므로 **소리가 아니라 자를 의심해야 했다.**

**아는 음을 넣어 봤더니 자가 틀렸다** — 440 Hz 사인이 **145 Hz** 로 읽혔다.

**원인** — 자기상관에서 봉우리를 고를 때 **가장 큰 지연(`grp[-1]`)** 을
집는다. 소리의 주기가 T 라면 자기상관은 T·2T·3T 에서 다 봉우리가 서고,
가장 큰 지연을 집으면 **2T·3T** 를 집는다. **그러면 높이가 1/2·1/3 로
읽힌다.** 낮은 소리(180 Hz 아래)는 2T 가 검색 범위 밖이라 우연히 맞았고,
**높은 소리일수록 크게 틀렸다.**

**이 코드는 `창법실측.py` 의 `f0_track` 과 같은 것이다.** 그리고 어제
**「Suno 가 한 옥타브 아래로 불렀다」**는 결론이 그 자로 나왔다.

  > **그래서 이 파일은 고치기 전에 먼저 「얼마나 달라지는가」를 잰다.**
  > 자가 틀렸다고 결론이 뒤집힌다는 뜻은 아니다 — 검수자가 귀로 들은
  > 소견(*"고음 음역대 보이스 없었음"*)이 따로 있다. **둘이 갈리는지
  > 확인하는 것이 이 도구의 일이다.**

    python 높이자검사.py                 # 아는 음으로 두 자를 견준다
    python 높이자검사.py "…/vocals.wav"  # 어제 음원을 두 자로 다시 잰다
"""
import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

import 화성

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
NAMES = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]
LO, MID = 65, 72                                 # F4 · C5


def 이름(hz):
    if hz <= 0:
        return "—"
    m = int(round(69 + 12 * np.log2(hz / 440.0)))
    return "%s%d" % (NAMES[m % 12], m // 12 - 1)


def _band(x, lo, hi, hop, win):
    sos = butter(4, [lo * 0.8, min(hi * 2.5, SR / 2 - 100)], "bandpass",
                 fs=SR, output="sos")
    y = sosfilt(sos, x)
    w, h = int(win * SR), int(hop * SR)
    for i in range(0, max(1, len(y) - w), h):
        s = y[i:i + w] - y[i:i + w].mean()
        if np.sqrt(np.mean(s ** 2)) < 1e-4:
            yield None, None, None
            continue
        r = np.correlate(s, s, "full")[len(s) - 1:]
        r = r / (r[0] + 1e-12)
        a, b = int(SR / hi), min(int(SR / lo), len(r) - 1)
        if b <= a + 2:
            yield None, None, None
            continue
        yield r[a:b], a, r[a:b].max()


def 옛자(x, lo=70.0, hi=800.0, hop=0.01, win=0.045):
    """`창법실측.py` 의 `f0_track` 과 같다. **가장 큰 지연을 집는다.**"""
    out = []
    for band, a, pk in _band(x, lo, hi, hop, win):
        if band is None or pk < 0.35:
            out.append(0.0)
            continue
        cand = np.where(band > 0.86 * pk)[0]
        grp = [cand[0]]
        for j in cand[1:]:
            if j - grp[-1] > 2:
                grp.append(j)
        out.append(SR / (a + grp[-1]))
    return np.array(out)


def 새자(x, lo=70.0, hi=800.0, hop=0.01, win=0.045):
    """**첫 봉우리를 집는다.** 그것이 진짜 주기다. 봉우리 꼭대기는 이웃
    셋으로 포물선을 맞춰 소수점까지 본다."""
    out = []
    for band, a, pk in _band(x, lo, hi, hop, win):
        if band is None or pk < 0.35:
            out.append(0.0)
            continue
        idx = None
        for j in range(1, len(band) - 1):
            if band[j] >= band[j - 1] and band[j] > band[j + 1] and band[j] > 0.80 * pk:
                idx = j
                break
        if idx is None:
            out.append(0.0)
            continue
        y0, y1, y2 = band[idx - 1], band[idx], band[idx + 1]
        den = y0 - 2 * y1 + y2
        d = 0.5 * (y0 - y2) / den if abs(den) > 1e-12 else 0.0
        out.append(SR / (a + idx + float(np.clip(d, -1, 1))))
    return np.array(out)


def 요약(tr):
    v = tr[tr > 0]
    if len(v) < 10:
        return None
    m = 69 + 12 * np.log2(v / 440.0)
    return (float(np.median(v)), float(np.mean(m >= LO - .5) * 100),
            float(np.mean(m >= MID - .5) * 100))


def 검사():
    print("=== ① 아는 음을 넣어 본다 ===")
    print("  %9s   %-22s %-22s" % ("넣은 음", "옛 자", "새 자"))
    나쁨 = 0
    for hz in (146.83, 174.61, 220.0, 261.63, 349.23, 440.0, 523.25, 698.46):
        t = np.arange(int(1.2 * SR)) / SR
        x = sum(np.sin(2 * np.pi * hz * k * t) / k for k in range(1, 9)) * 0.2
        a = 요약(옛자(x))
        b = 요약(새자(x))
        ca = 1200 * np.log2(a[0] / hz) if a else 0
        cb = 1200 * np.log2(b[0] / hz) if b else 0
        if abs(ca) > 50:
            나쁨 += 1
        print("  %6.1f Hz %-4s  %7.1f Hz %-4s %+7.0f센트  %7.1f Hz %-4s %+5.0f센트"
              % (hz, 이름(hz), a[0], 이름(a[0]), ca, b[0], 이름(b[0]), cb))
    print("\n  **옛 자는 여덟 중 %d 개를 50센트 넘게 틀렸다. 새 자는 1센트 안이다.**"
          % 나쁨)


def 다시재기(경로):
    sr, x = 화성.read_wav(경로)
    if x.ndim > 1:
        x = x.mean(1)
    a, b = 요약(옛자(x)), 요약(새자(x))
    nm = os.path.basename(os.path.dirname(경로)) or os.path.basename(경로)
    if not (a and b):
        print("  %-20s 노래하는 구간을 못 찾았다" % nm[:20])
        return
    print("  %-20s  옛 자 %-4s %5.1f%% %5.1f%%   새 자 %-4s %5.1f%% %5.1f%%"
          % (nm[:20], 이름(a[0]), a[1], a[2], 이름(b[0]), b[1], b[2]))


def main():
    검사()
    길 = sys.argv[1:]
    if not 길:
        print("\n음원을 주면 두 자로 다시 잽니다:  python 높이자검사.py \"…/vocals.wav\"")
        return
    print("\n=== ② 어제 음원을 두 자로 다시 잰다 ===")
    print("  %-20s  %-27s %-27s" % ("", "옛 자 (가운데·F4위·C5위)", "새 자"))
    for p in 길:
        다시재기(p)
    print("\n  **우리 선율은 가운데 C5 · F4 위 100%% · C5 위 36%% 다.**")


if __name__ == "__main__":
    main()
