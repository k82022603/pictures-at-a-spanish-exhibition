# -*- coding: utf-8 -*-
"""**저역 타격(킥·큰북)이 있는가 · 끝이 사그라드는가** — 2부 실험 점검용.

2026-08-22. 처음 판은 `butter(...)+lfilter` 로 60~150 Hz 를 걸렀고 **필터가
발산해 nan 을 냈다.** 좁은 대역 IIR 을 직접형으로 돌리면 늘 이렇다. **sos 로
바꾸고 자기검사를 붙였다** — 아는 소리 셋을 넣어 본다.
"""
import os
import sys

import numpy as np
from scipy import signal as sg

import 화성

sys.stdout.reconfigure(encoding="utf-8")
SR = 44100


def 읽기(p):
    sr, x = 화성.read_wav(p)
    m = x.mean(axis=1) if x.ndim > 1 else x
    if sr != SR:
        m = sg.resample(m, int(round(len(m) * SR / sr)))
    return m.astype(np.float64)


def 킥(m):
    """60~150 Hz 저역 타격 횟수(초당). 킥·큰북·카혼 저음."""
    sos = sg.butter(4, [60, 150], "band", fs=SR, output="sos")
    y = sg.sosfiltfilt(sos, m)
    h = 512
    n = (len(y) // h) * h
    e = np.abs(y[:n]).reshape(-1, h).mean(axis=1)
    if not np.isfinite(e).all() or e.max() <= 0:
        sys.exit("저역 봉투가 이상하다 — 재지 않는다")
    e = e / e.max()
    pk, _ = sg.find_peaks(e, height=0.25, distance=int(0.12 * SR / h),
                          prominence=0.12)
    return len(pk) / (len(m) / SR)



def 심벌(m):
    """6~12 kHz 잡음 타격 횟수(초당) — 하이햇·스네어. **베이스는 여기 못 온다.**

    저역만 재면 킥과 걷는 베이스를 못 가린다. 고역 잡음 트랜지언트는
    금속 타악과 스네어 줄만 낸다 — 나일론 기타·피아노·팔마스와도
    봉투 모양이 다르다(팔마스는 넓은 대역이라 일부 잡힌다)."""
    sos = sg.butter(4, [6000, 12000], "band", fs=SR, output="sos")
    y = sg.sosfiltfilt(sos, m)
    h = 256
    n = (len(y) // h) * h
    e = np.abs(y[:n]).reshape(-1, h).mean(axis=1)
    if not np.isfinite(e).all() or e.max() <= 0:
        return 0.0
    e = e / e.max()
    pk, _ = sg.find_peaks(e, height=0.20, distance=int(0.08 * SR / h),
                          prominence=0.10)
    return len(pk) / (len(m) / SR)


def 끝(m, 초=8.0):
    seg = m[-int(초 * SR):]
    r = np.sqrt((seg ** 2).mean())
    w = np.sqrt((m ** 2).mean())
    return 20 * np.log10(r + 1e-12), 20 * np.log10(r / (w + 1e-12) + 1e-12)


def 자검사():
    """**아는 소리 셋.** ① 무음 0 ② 2 Hz 저역 맥박 ≈2 ③ 순음 0."""
    t = np.arange(int(20 * SR)) / SR
    맥 = (np.sin(2 * np.pi * 80 * t) *
          (np.exp(-((t % 0.5) * 18)) if True else 1))
    쌍 = [("무음", np.zeros(int(20 * SR)) + 1e-9, 0.0, 0.1),
          ("2회/초 맥박", 맥, 1.7, 2.3),
          ("고음 순음", np.sin(2 * np.pi * 1000 * t), 0.0, 0.1)]
    for 이름, x, lo, hi in 쌍:
        try:
            v = 킥(x)
        except SystemExit:
            v = 0.0
        ok = lo <= v <= hi
        print("  자검사 %-10s %5.2f회/초  기대 %.1f~%.1f  %s"
              % (이름, v, lo, hi, "OK" if ok else "★실패"))
        if not ok:
            sys.exit("자검사 실패 — 자가 틀렸다. 재지 않는다")


if __name__ == "__main__":
    print("[자검사]")
    자검사()
    print("\n[실측]")
    for p in sys.argv[1:]:
        m = 읽기(p)
        r, rel = 끝(m)
        print("%-30s  저역타격 %5.2f   고역타격 %5.2f 회/초   끝8초 %6.1f dB (%+5.1f dB)"
              % (os.path.basename(p), 킥(m), 심벌(m), r, rel))
