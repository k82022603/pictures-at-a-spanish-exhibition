# -*- coding: utf-8 -*-
"""**들리는 크기로 맞춰서 낸다.**

2026-08-20. 검수자가 네 번 *"안 들린다"* 고 했다. 원인이 셋이었다.

  ① 파일이 실제로 작았다 (−36.6 dB)
  ② **에너지의 55%가 50 Hz 아래**였다 — 자는 그것까지 합쳐 재서 「충분히
     크다」고 찍었고, 키울수록 **안 들리는 진동만** 커졌다
  ③ 키운 뒤 **「넘치면 전체를 줄이는」** 코드가 그 이득을 도로 깎았다

**그래서 이 도구는 「들리는 대역(200~5000 Hz)이 울릴 때」만 재서 맞춘다.**
통째로 재지 않는다 — 쉬는 자리와 안 들리는 저역이 섞여 들어가기 때문이다.

    python 크게내기.py <들어온파일> <낼파일> [목표dB]
"""
import os
import subprocess
import sys

import numpy as np
from scipy.signal import butter, sosfilt

import 화성
import synth

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
목표 = -12.0                                      # 들리는 대역이 울릴 때


def 들리는크기(m, sr=SR):
    """**200~5000 Hz 가 울리는 동안**의 크기. 쉬는 자리는 안 센다."""
    v = sosfilt(butter(4, [200, 5000], "bandpass", fs=sr, output="sos"), m)
    w = int(0.05 * sr)
    fr = np.array([np.sqrt(np.mean(v[i:i + w] ** 2))
                   for i in range(0, len(v) - w, w)])
    if not len(fr) or fr.max() <= 0:
        return 0.0
    울릴때 = fr[fr > fr.max() * 0.1]
    return float(np.sqrt(np.mean(울릴때 ** 2)))


def db(x):
    return 20.0 * np.log10(max(1e-12, x))


def main():
    if len(sys.argv) < 3:
        raise SystemExit("쓰는 법:  python 크게내기.py <들어온파일> <낼파일> [목표dB]")
    안, 밖 = sys.argv[1], sys.argv[2]
    t = float(sys.argv[3]) if len(sys.argv) > 3 else 목표

    sr, a = 화성.read_wav(안)
    if a.ndim == 1:
        a = np.stack([a, a], 1)
    m = a.mean(1)
    전 = 들리는크기(m, sr)
    print("들어온 것  들리는 크기 %.1f dB" % db(전))

    이득 = 10.0 ** ((t - db(전)) / 20.0)
    y = a * 이득
    print("  %.1f 배 곱한다 (%+.1f dB)" % (이득, t - db(전)))

    # **넘치는 것을 전체를 줄여서 막지 않는다.** 봉우리만 부드럽게 눕힌다
    무릎 = 0.75
    큰곳 = np.abs(y) > 무릎
    y[큰곳] = np.sign(y[큰곳]) * (
        무릎 + (0.99 - 무릎) * np.tanh((np.abs(y[큰곳]) - 무릎) / (0.99 - 무릎)))

    synth.write_wav(밖, y, bits=24)
    sr2, b = 화성.read_wav(밖)
    뒤 = 들리는크기(b.mean(1) if b.ndim > 1 else b, sr2)
    print("낸 것     들리는 크기 %.1f dB   최대 %.3f   %d Hz"
          % (db(뒤), np.abs(b).max(), sr2))
    if abs(db(뒤) - t) > 2.0:
        print("  ⚠ 목표에서 %.1f dB 벗어났다" % (db(뒤) - t))
    mp3 = os.path.splitext(밖)[0] + ".mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", 밖,
                    "-ar", "44100", "-codec:a", "libmp3lame", "-b:a", "320k",
                    mp3], check=True)
    print("→ %s" % os.path.basename(mp3))


if __name__ == "__main__":
    main()
