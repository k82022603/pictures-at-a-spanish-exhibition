# -*- coding: utf-8 -*-
"""**Suno 목소리를 그대로 두고 음 높이만 옮긴다** — 두 번째 방식.

2026-08-20. `보컬가락.py` 는 **목소리를 새로 만들어 넣는** 방식이다
(`resynth` — 입 모양만 남기고 성대를 다시 만든다). 그것이 낸 소리를 검수자가
**다섯 번** *"개미 지나가는 소리"* 라고 했다. 재 보니 원인이 나왔다 —
**목소리의 몸통(200~800 Hz)이 10.5%** 밖에 없고 **에너지의 67.7%가 쉭쉭거리는
3.2~6.4 kHz** 에 몰려 있었다. 성대를 임펄스로 흉내내면 배음이 전부 같은 크기라
그렇게 된다. 대역을 맞춰 49.5%까지 올렸지만 **여전히 안 들린다고 했다.**

**그래서 만들지 않고 옮긴다.**

  ① 음절마다 지금 부르는 높이를 잰다
  ② **소리를 빨리/느리게 돌려** 목표 음으로 옮긴다 (길이가 함께 변한다)
  ③ 길이를 우리 격자로 되돌린다

**목소리는 Suno 것 그대로다.** 몸통도 크기도 그대로 남는다. 대신 **입 모양도
같이 옮겨가서**(포먼트) 조금 다른 사람처럼 들릴 수 있다 — 그것이 이 방식의
값이고, 안 들리는 것보다는 낫다.

**두 방식을 나란히 두고 검수자가 고른다.** 어느 쪽도 지우지 않는다(R11).

    python 보컬가락2.py "…/vocals.wav"
"""
import os
import sys

import numpy as np

import 화성
import synth
import 음높이
import 보컬시험
import 보컬가락
from 보컬시험 import TH_A, BT9, midi_hz, stretch, shift

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
LINE_DUR = sum(b for _, b in TH_A) * BT9


def 한음(조각, 목표m):
    """음절 하나를 목표 음으로 옮긴다. **소리는 그대로 두고 속도만 바꾼다.**"""
    tr = 음높이.재기(조각)
    v = tr[tr > 0]
    if len(v) < 3:
        return 조각                               # 높이를 못 재면 그냥 둔다
    지금 = float(np.median(v))
    비 = midi_hz(목표m) / max(1e-6, 지금)
    비 = float(np.clip(비, 0.5, 2.6))             # 두 옥타브 넘게는 안 옮긴다
    return shift(조각, 비)


def 줄하나(x, 음절):
    n = int(LINE_DUR * SR)
    if len(음절) != len(TH_A):
        # 음절을 못 찾으면 줄 전체를 한 번에 옮긴다
        y = 한음(x, TH_A[0][0])
        return stretch(y, n), "음절 %d 개(11 아님) — 줄 전체를 한 번에" % len(음절)
    경계 = [0.0] + 음절[1:] + [len(x) / SR]
    조각 = []
    for k, (m, b) in enumerate(TH_A):
        a, z = int(경계[k] * SR), int(경계[k + 1] * SR)
        옮긴 = 한음(x[a:z], m)
        조각.append(stretch(옮긴, max(64, int(b * BT9 * SR))))
    겹 = int(0.008 * SR)
    y = 조각[0]
    for 다음 in 조각[1:]:
        k = min(겹, len(y) // 2, len(다음) // 2)
        if k < 8:
            y = np.concatenate([y, 다음])
            continue
        f = np.linspace(0.0, 1.0, k)
        y = np.concatenate([y[:-k], y[-k:] * (1 - f) + 다음[:k] * f, 다음[k:]])
    y = np.pad(y[:n], (0, max(0, n - len(y))))
    t = np.arange(n) / SR
    y *= np.clip(t / 0.03, 0, 1) * np.clip((LINE_DUR - t) / 0.06, 0, 1)
    return y, "음절 11 개를 음마다 하나씩 — 옮기는 방식"


def main():
    if len(sys.argv) < 2:
        raise SystemExit('쓰는 법:  python 보컬가락2.py "…/vocals.wav"')
    경로 = sys.argv[1]
    print("Suno 목소리를 그대로 두고 음 높이만 옮긴다\n")

    sr, x = 화성.read_wav(경로)
    x = x.mean(1) if x.ndim > 1 else x
    if sr != SR:
        raise SystemExit("%d Hz 다" % sr)

    tr = 음높이.재기(x)
    구간 = 보컬가락.줄나누기(tr)
    if len(구간) < len(보컬시험.LINES):
        구간 = 보컬가락.줄맞추기(구간, tr, 목표=len(보컬시험.LINES))
    print("줄 %d 개" % len(구간))

    낸것 = []
    for k, (a, b) in enumerate(구간):
        seg = x[int(a * SR):int(b * SR)]
        r = float(np.sqrt(np.mean(seg ** 2)))
        if r < 3e-3:
            print("  %d줄  비어 있다 (%.1f dB) — 뺀다" % (k + 1, 20 * np.log10(r + 1e-12)))
            continue
        y, 방식 = 줄하나(seg, 보컬가락.음절나누기(seg))
        print("  %d줄  %s" % (k + 1, 방식))
        낸것.append(y)

    out = np.zeros(int((LINE_DUR + 0.5) * SR * len(낸것)))
    for k, y in enumerate(낸것):
        i = int(k * (LINE_DUR + 0.5) * SR)
        out[i:i + len(y)] += y

    p = os.path.join(HERE, "보컬가락2 - %d줄.wav" % len(낸것))
    synth.write_wav(p, np.stack([out, out], 1), bits=24)

    # 잰다 — 가락과 **목소리의 몸통** 둘 다
    s2, y2 = 화성.read_wav(p)
    m = y2.mean(1) if y2.ndim > 1 else y2
    r = 음높이.요약(음높이.재기(m), 최저=65, 가운데=72)
    S = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    g = lambda lo, hi: 100 * S[(f >= lo) & (f < hi)].sum() / S.sum()
    print("\n  최저음(F4) 위 %.1f%%   (우리 선율 100%%)" % r[1])
    print("  목소리 몸통(200~800Hz) %.1f%%   쉭쉭(3.2~6.4k) %.1f%%   (원본 66.2 / 4.3)"
          % (g(200, 800), g(3200, 6400)))
    print("\n→ %s" % os.path.basename(p))


if __name__ == "__main__":
    main()
