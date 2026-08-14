# -*- coding: utf-8 -*-
"""부를 사람에게 주는 **안내용 반주.**

2026-08-14. 검수자가 음역을 **F4~F5 그대로** 확정했다.

9악장 구간(8:45~9:40)에 두 가지를 얹는다.

  ① **딸깍 넷** — 각 줄이 들어오기 직전에 박을 세어 준다
  ② **길잡이 음** — 부를 선율을 아주 작게. 음을 못 찾을 때만 들으면 된다

두 판을 낸다. **길잡이 음이 있는 판**으로 익히고, **딸깍만 있는 판**으로
실제로 부른다 — 길잡이가 녹음에 새어 들어가면 안 된다.

**승인판은 안 건드린다.** 읽어서 위에 얹기만 한다.

    python 가이드반주.py
"""
import os
import sys

import numpy as np

import 화성
import synth

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(HERE, "전곡화성.wav")

# 주제 A — 부를 선율. **적힌 그대로 F4~F5 다** (`CLAUDE.md` 6절)
TH_A = [(67, 1.0), (65, 1.0), (70, 1.0), (72, .5), (77, .5), (74, 1.0),
        (72, .5), (77, .5), (74, 1.0), (70, 1.0), (72, 1.0)]
BT9 = 60.0 / 63.0                                # 9악장 ♩=63

LINES = [(527.0, "4행"), (538.0, "6행"), (549.0, "7행"), (556.0, "8행")]


def hz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def click(hi=False):
    """딸깍. 넷째(=들어오기 직전)만 높게 해서 「다음이 시작」을 알린다."""
    n = int(0.035 * SR)
    t = np.arange(n) / SR
    e = np.exp(-t * 90.0)
    return np.sin(2 * np.pi * (1800.0 if hi else 1200.0) * t) * e * 0.5


def guide(m, dur):
    """길잡이 음. 맑고 작게 — 반주에 묻히지 않되 시끄럽지 않게."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * hz(m) * t) +
         0.22 * np.sin(4 * np.pi * hz(m) * t))
    a = np.clip(t / 0.02, 0, 1) * np.clip((dur - t) / 0.05, 0, 1)
    return y * a


def build(with_guide):
    sr, x = 화성.read_wav(MASTER)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    out = x.copy()
    for t0, name in LINES:
        # 딸깍 넷 — 한 박씩 앞에서부터
        for k in range(4):
            i = int((t0 - (4 - k) * BT9) * SR)
            c = click(hi=(k == 3))
            out[i:i + len(c), 0] += c
            out[i:i + len(c), 1] += c
        if not with_guide:
            continue
        t = t0
        for m, b in TH_A:
            g = guide(m, b * BT9 * 0.92) * 0.055
            i = int(t * SR)
            out[i:i + len(g), 0] += g
            out[i:i + len(g), 1] += g
            t += b * BT9
    seg = out[int(525 * SR):int(580 * SR)]
    return seg / max(1.0, np.abs(seg).max() / 0.98)


def main():
    lo = min(m for m, _ in TH_A)
    hi = max(m for m, _ in TH_A)
    print("안내용 반주 — 9악장 8:45~9:40 (55초)")
    print("음역 %s ~ %s  (%.0f~%.0f Hz)\n" %
          (["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"][lo % 12] + str(lo // 12 - 1),
           ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"][hi % 12] + str(hi // 12 - 1),
           hz(lo), hz(hi)))
    for t0, name in LINES:
        print("  %s  %d:%02d 에 들어온다 — 딸깍 넷이 %d:%04.1f 부터" %
              (name, int(t0) // 60, int(t0) % 60,
               int(t0 - 4 * BT9) // 60, (t0 - 4 * BT9) % 60))
    for wg, nm in ((True, "안내반주 길잡이음 있음"), (False, "안내반주 딸깍만")):
        synth.write_wav(os.path.join(HERE, "%s.wav" % nm), build(wg), bits=24)
        print("→ %s.wav" % nm)
    print("\n**길잡이 음이 있는 판으로 익히고, 딸깍만 있는 판으로 부른다.**")


if __name__ == "__main__":
    main()
