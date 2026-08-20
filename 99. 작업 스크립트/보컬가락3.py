# -*- coding: utf-8 -*-
"""**늘이고 줄이는 처리를 아예 빼고 음만 옮긴다** — 세 번째 방식.

2026-08-20. 검수자가 **여섯 번** *"안 들린다"* 고 했다. 마지막에는 같은 파일
안에 Suno 원본과 우리 것을 번갈아 넣어 견주게 했고, **네 토막이 전부 정확히
−12.0 dB** 인데도 *"A는 크고 B는 작게 들린다"* 였다.

**모든 측정이 「B가 더 크고 더 끊김 없다」고 나왔다** — 중간값 −13.1 대
−12.8 dB, 소리 나는 시간 95% 대 80%, A가중까지 재도 마찬가지. **즉 크기
문제가 아니다.**

**남은 것은 소리의 질이다.** 앞의 두 방식은 둘 다 `stretch()` 를 쓴다 —
조각을 겹쳐 이어 붙여 길이만 바꾸는 것인데, **위상을 안 맞추고 겹치므로
소리가 뭉개진다.** 크기는 남고 **실체가 사라진다** — 벽 너머에서 나는 소리
같아진다. 그것이 「개미 지나가는 소리」의 정체로 보인다.

**그래서 이 방식은 늘이고 줄이는 것을 안 한다.**

  ① 음절마다 지금 부르는 높이를 잰다
  ② **소리를 통째로 빨리/느리게 돌려** 목표 음으로 옮긴다 (테이프와 같다)
  ③ **길이는 안 맞춘다.** 옮긴 그대로 우리 격자 자리에 놓는다

빨리 돌리면 짧아지므로 **음이 제 자리보다 일찍 끝난다.** 그 대신 **소리는
원본 그대로**다 — 뭉개는 처리가 한 번도 안 들어간다.

**세 방식을 나란히 두고 검수자가 고른다.** 어느 것도 지우지 않는다(R11).

    python 보컬가락3.py "…/vocals.wav"
"""
import os
import sys

import numpy as np

import 화성
import synth
import 음높이
import 보컬시험
import 보컬가락
from 보컬시험 import TH_A, BT9, midi_hz

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
LINE_DUR = sum(b for _, b in TH_A) * BT9


def 속도바꿈(x, 비):
    """**테이프를 빨리 돌리듯** 통째로 속도를 바꾼다. 뭉개는 처리가 없다."""
    n = max(8, int(len(x) / 비))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def 줄하나(x, 음절):
    """음절마다 목표 음으로 옮겨 격자에 **그냥 놓는다.**"""
    n = int(LINE_DUR * SR)
    y = np.zeros(n)
    if len(음절) != len(TH_A):
        return None, "음절 %d 개(11 아님) — 건너뛴다" % len(음절)
    경계 = [0.0] + 음절[1:] + [len(x) / SR]
    t0 = 0.0
    옮긴수 = 0
    for k, (m, b) in enumerate(TH_A):
        a, z = int(경계[k] * SR), int(경계[k + 1] * SR)
        조각 = x[a:z]
        if len(조각) < 256:
            t0 += b * BT9
            continue
        tr = 음높이.재기(조각)
        v = tr[tr > 0]
        if len(v) >= 3:
            비 = float(np.clip(midi_hz(m) / float(np.median(v)), 0.5, 2.6))
            조각 = 속도바꿈(조각, 비)
            옮긴수 += 1
        # 자리에 놓는다. 길면 자르고, 짧으면 그대로 둔다
        칸 = int(b * BT9 * SR)
        조각 = 조각[:칸]
        # 양끝만 아주 짧게 여닫는다 — 딱 끊기는 소리를 막는다
        e = min(int(0.006 * SR), len(조각) // 4)
        if e > 2:
            조각 = 조각.copy()
            조각[:e] *= np.linspace(0, 1, e)
            조각[-e:] *= np.linspace(1, 0, e)
        i = int(t0 * SR)
        y[i:i + len(조각)] += 조각
        t0 += b * BT9
    return y, "음절 11 개 중 %d 개를 옮겼다 — 늘이지 않음" % 옮긴수


def main():
    if len(sys.argv) < 2:
        raise SystemExit('쓰는 법:  python 보컬가락3.py "…/vocals.wav"')
    경로 = sys.argv[1]
    print("늘이고 줄이는 처리 없이 음만 옮긴다\n")

    sr, x = 화성.read_wav(경로)
    x = x.mean(1) if x.ndim > 1 else x
    if sr != SR:
        raise SystemExit("%d Hz 다" % sr)

    tr = 음높이.재기(x)
    구간 = 보컬가락.줄나누기(tr)
    if len(구간) < len(보컬시험.LINES):
        구간 = 보컬가락.줄맞추기(구간, tr, 목표=len(보컬시험.LINES))

    낸것 = []
    for k, (a, b) in enumerate(구간):
        seg = x[int(a * SR):int(b * SR)]
        r = float(np.sqrt(np.mean(seg ** 2)))
        if r < 3e-3:
            print("  %d줄  비어 있다 — 뺀다" % (k + 1))
            continue
        y, 방식 = 줄하나(seg, 보컬가락.음절나누기(seg))
        print("  %d줄  %s" % (k + 1, 방식))
        if y is not None:
            낸것.append(y)
    if not 낸것:
        raise SystemExit("낸 것이 없다")

    out = np.zeros(int((LINE_DUR + 0.5) * SR * len(낸것)))
    for k, y in enumerate(낸것):
        i = int(k * (LINE_DUR + 0.5) * SR)
        out[i:i + len(y)] += y

    p = os.path.join(HERE, "보컬가락3 - %d줄.wav" % len(낸것))
    synth.write_wav(p, np.stack([out, out], 1), bits=24)

    s2, y2 = 화성.read_wav(p)
    m = y2.mean(1) if y2.ndim > 1 else y2
    r = 음높이.요약(음높이.재기(m), 최저=65, 가운데=72)
    S = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    g = lambda lo, hi: 100 * S[(f >= lo) & (f < hi)].sum() / S.sum()
    print("\n  최저음(F4) 위 %.1f%%   목소리 몸통 %.1f%%   쉭쉭 %.1f%%"
          % (r[1], g(200, 800), g(3200, 6400)))
    print("→ %s" % os.path.basename(p))


if __name__ == "__main__":
    main()
