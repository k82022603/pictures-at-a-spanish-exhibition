# -*- coding: utf-8 -*-
"""7악장 아르페지오가 「뭉치는가 흩어지는가」를 잰다 (BL-36 ①, 2026-08-13).

    python 물소리대조.py "기준선-7악장 피아노 (v4.19).wav" 전곡화성.wav

**RMS 로는 이 판단이 안 된다.** 피아노와 챔발로는 음량이 다른 것이 아니라
**에너지가 시간축에 놓이는 방식**이 다르다. 그래서 셋을 잰다.

| 무엇 | 무엇을 보나 | 풀어쓰면 |
|---|---|---|
| **어택 밀도** | 초당 몇 번 새 소리가 시작되는가 | **물방울이 몇 개인가** |
| **골 깊이** | 소리와 소리 **사이가 얼마나 비는가** | **방울 사이가 보이는가, 이어져 있는가** |
| **밝기 (스펙트럴 센트로이드)** | 에너지의 무게중심 주파수 | **또랑또랑한가 먹먹한가** |

**골 깊이가 핵심이다.** 뭉친다는 것은 여운이 다음 음까지 이어져 **사이가
안 빈다**는 뜻이다. 흩어진다는 것은 그 반대다. 이것이 검수자가 챔발로를
꺼낸 이유이고, 숫자로 보이는 자리도 여기다.

**스템으로 잰다** — 마스터로 재면 베이스·해먼드·무그가 섞여 물만 못 본다.
`스템/스템-kb.wav` 가 건반 성부다. **다만 페이더 전이므로**(`05` 9.21절)
절대값은 마스터와 다르고, 이 도구가 보는 것은 **두 렌더의 차이**다.
"""
import io
import os
import sys

import numpy as np
from scipy import signal

import 화성

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
M7 = (325.0, 425.0)                       # 7악장 구간


def mono(x):
    return x.mean(1) if x.ndim > 1 else x


def envelope(x, sr, win=0.02):
    """짧은 창의 실효값 — 소리의 「굵기」가 시간에 따라 어떻게 변하나."""
    n = int(sr * win)
    e = np.sqrt(np.convolve(x ** 2, np.ones(n) / n, mode="same"))
    return e


def measure(path, sr_hint=None):
    sr, a = 화성.read_wav(path)
    x = mono(a)[int(M7[0] * sr):int(M7[1] * sr)]
    e = envelope(x, sr)
    e = e / (e.max() + 1e-12)

    # ① 어택 — 포락선이 갑자기 솟는 자리. 0.08초 안에 두 번 세지 않는다
    d = np.diff(e, prepend=e[0])
    thr = np.percentile(d, 99.0)
    pk, _ = signal.find_peaks(d, height=max(thr, 1e-6), distance=int(sr * 0.08))
    dens = len(pk) / (M7[1] - M7[0])

    # ② 골 깊이 — 위 10% 와 아래 25% 의 차. **사이가 비는가**
    hi = np.percentile(e, 90)
    lo = np.percentile(e, 25)
    dip = 20 * np.log10((hi + 1e-12) / (lo + 1e-12))

    # ③ 밝기 — 에너지의 무게중심
    f, t, S = signal.spectrogram(x, sr, nperseg=2048)
    P = S.sum(0) + 1e-20
    cen = float((S * f[:, None]).sum() / S.sum()) if S.sum() > 0 else 0.0

    rms = 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)
    return dens, dip, cen, rms


def word(a, b, hi_is):
    """숫자만 주지 않는다 — 어느 쪽이 어떻다고 말한다 (`CLAUDE.md` 8절)."""
    if abs(b - a) < 1e-9:
        return "같다"
    return hi_is[0] if b > a else hi_is[1]


A, B = sys.argv[1], sys.argv[2]
STEM = os.path.join(HERE, "스템", "스템-kb.wav")
tgt = [("마스터 (전부 섞인 것)", A, B)]
if os.path.exists(STEM):
    tgt.append(("건반 스템 (물소리만) — 새 렌더", None, STEM))

print("7악장 %.0f~%.0f초 · 물이 뭉치는가 흩어지는가" % M7)
print()
for title, pa, pb in tgt:
    print("── %s" % title)
    if pa:
        da, pa_dip, ca, ra = measure(pa)
        db_, pb_dip, cb, rb = measure(pb)
        print("%-22s %10s %10s %10s" % ("", "A 피아노", "B 챔발로", "판정"))
        print("%-22s %10.2f %10.2f   %s" % ("어택 밀도 (개/초)", da, db_,
              word(da, db_, ("B 가 방울이 잦다", "A 가 방울이 잦다"))))
        print("%-22s %10.1f %10.1f   %s" % ("골 깊이 (dB)", pa_dip, pb_dip,
              word(pa_dip, pb_dip, ("★ B 가 사이가 빈다 = 흩어진다",
                                    "A 가 사이가 빈다"))))
        print("%-22s %10.0f %10.0f   %s" % ("밝기 (Hz)", ca, cb,
              word(ca, cb, ("B 가 또랑또랑하다", "A 가 또랑또랑하다"))))
        print("%-22s %10.1f %10.1f   %s" % ("RMS (dB)", ra, rb,
              word(ra, rb, ("B 가 크다", "A 가 크다"))))
    else:
        d, dip, c, r = measure(pb)
        print("  어택 밀도 %.2f 개/초 · 골 깊이 %.1f dB · 밝기 %.0f Hz · RMS %.1f dB"
              % (d, dip, c, r))
    print()

print("**골 깊이가 이 판정의 핵심이다** — 뭉친다는 것은 여운이 다음 음까지")
print("이어져 사이가 안 빈다는 뜻이고, 흩어진다는 것은 그 반대다.")
