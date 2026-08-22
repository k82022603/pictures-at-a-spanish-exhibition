# -*- coding: utf-8 -*-
"""**Suno 판 전곡의 악장별 표를 음원에서만 낸다.**

2026-08-22. `악장표.py` 는 `전곡화성.py` 의 악보에서 값을 뽑는다.
**Suno 판에는 악보가 없다** — 소리밖에 없다. 그래서 전부 실측한다.

빠르기는 **저역 타격의 자기상관**에서 뽑는다. 화성 리듬은 크로마가 바뀌는 간격이다.
**「들을 지점」 후보도 음원에서 찾는다** — 음량이 가장 크게 움직이는 자리.
"""
import os
import sys

import numpy as np
from scipy import signal as sg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 화성

sys.stdout.reconfigure(encoding="utf-8")
N = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]


def 분초(t):
    return "%d:%05.2f" % (int(t) // 60, t % 60)


def 크로마(seg, SR):
    n = 1 << 14
    if len(seg) < n:
        return np.full(12, 1 / 12)
    f, t, Z = sg.stft(seg, SR, nperseg=n, noverlap=n // 2)
    P = (np.abs(Z) ** 2).mean(axis=1)
    ok = (f > 55) & (f < 4200)
    f, P = f[ok], P[ok]
    pc = np.rint(12 * np.log2(f / 440.0) + 69).astype(int) % 12
    c = np.array([P[pc == i].sum() for i in range(12)])
    return c / (c.sum() + 1e-20)


def 빠르기(seg, SR):
    """저역 타격 봉투의 자기상관 → 분당 박. 40~200 사이만 본다."""
    sos = sg.butter(4, [40, 200], "band", fs=SR, output="sos")
    y = np.abs(sg.sosfiltfilt(sos, seg))
    h = 256
    n = (len(y) // h) * h
    e = y[:n].reshape(-1, h).mean(axis=1)
    e = e - e.mean()
    if e.std() < 1e-9:
        return 0.0
    r = np.correlate(e, e, "full")[len(e) - 1:]
    fps = SR / h
    lo, hi = int(fps * 60 / 200), int(fps * 60 / 40)
    if hi >= len(r):
        return 0.0
    k = lo + int(np.argmax(r[lo:hi]))
    return 60.0 * fps / k


def 화성리듬(seg, SR, 창=0.5):
    """크로마가 「바뀌었다」고 볼 만큼 갈리는 횟수 → 몇 초마다 색이 바뀌나."""
    h = int(창 * SR)
    n = (len(seg) // h) * h
    cs = [크로마(seg[i:i + h], SR) for i in range(0, n, h)]
    ch = 0
    for i in range(1, len(cs)):
        a, b = cs[i - 1], cs[i]
        s = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
        if s < 0.90:
            ch += 1
    return (len(seg) / SR) / max(1, ch)


def 큰변화(seg, SR, 시작, 창=2.0):
    """악장 안에서 음량이 가장 크게 오르는 자리와 가장 조용한 자리."""
    h = int(창 * SR)
    n = (len(seg) // h) * h
    q = 20 * np.log10(np.sqrt((seg[:n].reshape(-1, h) ** 2).mean(axis=1)) + 1e-12)
    if len(q) < 3:
        return None, None, 0.0
    d = np.diff(q)
    up = int(np.argmax(d))
    quiet = int(np.argmin(q))
    return 시작 + (up + 1) * 창, 시작 + quiet * 창, q.max() - q.min()


if __name__ == "__main__":
    C = "../산출물/20260822 - 0악장을 다시 만든다"
    sr, x = 화성.read_wav(C + "/이어붙인 것/전곡 A - 그대로 이은 것.wav")
    SR = sr
    m = x.mean(axis=1).astype(np.float64)
    B = np.load("악장경계_Suno.npy")
    이름 = ["0 Promenade 제시", "1 마드리드", "2 변주 I", "3 세고비아", "4 세비야",
            "5 변주 II", "6 론다", "7 그라나다", "8 바르셀로나", "9 The Great Gate"]
    우리 = [50, 40, 15, 55, 100, 15, 50, 100, 100, 55]
    전체 = 20 * np.log10(np.sqrt((m ** 2).mean()) + 1e-12)
    print("전곡 %s   RMS %.1f dB\n" % (분초(len(m) / SR), 전체))
    print("악장                구간                길이    우리   빠르기   음량      색바뀜   상위음        F♯     가장 커지는  가장 조용")
    print("-" * 132)
    for i, nm in enumerate(이름):
        a, b = B[i], B[i + 1]
        seg = m[int(a * SR):int(b * SR)]
        r = 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12)
        c = 크로마(seg, SR)
        top = " ".join(N[j] for j in np.argsort(-c)[:3])
        up, quiet, pol = 큰변화(seg, SR, a)
        print("%-18s %s~%s %6.1f초 %5d  %6.1f  %6.1f dB  %5.1f초  %-12s %.3f  %s  %s"
              % (nm, 분초(a), 분초(b), b - a, 우리[i], 빠르기(seg, SR), r,
                 화성리듬(seg, SR), top, c[6],
                 분초(up) if up else "-", 분초(quiet) if quiet else "-"))
