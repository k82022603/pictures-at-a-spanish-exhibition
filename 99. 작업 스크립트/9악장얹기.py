# -*- coding: utf-8 -*-
"""**목소리를 9악장 반주에 얹는다.**

2026-08-20. 검수자 지시. 목소리만 따로 들려드리는 것이 여덟 번 실패했다 —
**내 측정은 「원본과 같은 크기」라고 찍는데 검수자 귀에는 안 들렸다.**

**반주에 얹으면 그 어긋남이 그 자리에서 드러난다.** 반주는 검수자가 이미
잘 듣고 있는 소리이므로, **거기 얹었을 때 목소리가 안 들리면 얼마나 작은지가
바로 보인다.** 내가 못 잰 것을 반주가 대신 재 주는 셈이다.

네 줄이 들어갈 자리는 곡에서 **8:47 · 8:58 · 9:09 · 9:16** 이고, 9악장 구간
(8:45~9:40)에서 **2.0 · 13.0 · 24.0 · 31.0초**다(`05` 9.31절).

**승인 음원은 안 건드린다.** 읽어서 위에 얹은 새 파일을 만든다(R9).

    python 9악장얹기.py "보컬가락3 - 3줄.wav" "낼이름"
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
T0, T1 = 525.0, 580.0                            # 9악장 8:45~9:40
자리 = [2.0, 13.0, 24.0, 31.0]                    # 8:47 · 8:58 · 9:09 · 9:16
줄길이 = 8.571 + 0.5                              # 낸 파일에서 줄 간격


def 상위레벨(m, pct=90):
    """**소리가 울릴 때의 윗선.** 쉬는 자리를 안 섞는다 — 그게 오늘의 실수였다."""
    w = int(0.05 * SR)
    fr = np.array([np.sqrt(np.mean(m[i:i + w] ** 2))
                   for i in range(0, len(m) - w, w)])
    return float(np.percentile(fr, pct))


def main():
    목소리파일 = sys.argv[1] if len(sys.argv) > 1 else "보컬가락3 - 3줄.wav"
    이름 = sys.argv[2] if len(sys.argv) > 2 else "9악장에 얹은 것"
    더 = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0   # 반주보다 몇 dB 크게

    sr, mst = 화성.read_wav(MASTER)
    if mst.ndim == 1:
        mst = np.stack([mst, mst], 1)
    반주 = mst[int(T0 * SR):int(T1 * SR)].copy()

    sr2, v = 화성.read_wav(os.path.join(HERE, 목소리파일))
    v = v.mean(1) if v.ndim > 1 else v

    반 = 상위레벨(반주.mean(1))
    목 = 상위레벨(v)
    이득 = (반 / max(1e-9, 목)) * 10.0 ** (더 / 20.0)
    print("반주 %.1f dB · 목소리 %.1f dB  →  목소리에 %.2f 배 (%+.1f dB)"
          % (20 * np.log10(반), 20 * np.log10(목), 이득, 20 * np.log10(이득)))

    out = 반주.copy()
    n = int(줄길이 * SR)
    쓴줄 = 0
    for k, t in enumerate(자리):
        a = k * n
        조각 = v[a:a + int(8.571 * SR)]
        if len(조각) < SR // 2 or np.sqrt(np.mean(조각 ** 2)) < 1e-3:
            print("  %d줄  없음 — 건너뛴다" % (k + 1))
            continue
        조각 = 조각 * 이득
        i = int(t * SR)
        m = min(len(조각), len(out) - i)
        out[i:i + m, 0] += 조각[:m] * 0.95        # 왼쪽 살짝 (무그가 오른쪽)
        out[i:i + m, 1] += 조각[:m] * 0.80
        print("  %d줄  %4.1f초 에 놓았다 (곡에서 %d:%02d)"
              % (k + 1, t, int(T0 + t) // 60, int(T0 + t) % 60))
        쓴줄 += 1

    p = np.abs(out).max()
    if p > 0.99:
        무릎 = 0.8
        큰 = np.abs(out) > 무릎
        out[큰] = np.sign(out[큰]) * (
            무릎 + (0.99 - 무릎) * np.tanh((np.abs(out[큰]) - 무릎) / (0.99 - 무릎)))

    낼곳 = os.path.join(HERE, "..", "산출물", "20260820 - 가락은 내가 입힌다",
                        "%s.wav" % 이름)
    synth.write_wav(낼곳, out, bits=24)
    s3, z = 화성.read_wav(낼곳)
    print("\n  %d 줄을 얹었다 · %.2f초 · 최대 %.3f · %d Hz"
          % (쓴줄, len(z) / s3, np.abs(z).max(), s3))
    print("→ %s.wav" % 이름)


if __name__ == "__main__":
    main()
