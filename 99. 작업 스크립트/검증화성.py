# -*- coding: utf-8 -*-
"""전곡 화성 검증 — 크로마 · 대역 균형 · 러프니스 · 클리핑"""
import sys
import numpy as np

import 화성
from scipy import signal as sg
from scipy.io import wavfile

SR = 44100
NAMES = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]
MOV = [("0 프롬나드 제시", 0, 50, "Bb"), ("1 마드리드", 50, 90, "Bb"),
       ("2 변주 I", 90, 105, "Bb"), ("3 세고비아", 105, 160, "Gm"),
       ("4 세비야", 160, 260, "D프리지안"), ("5 변주 II", 260, 275, "전이"),
       ("6 론다", 275, 325, "Eb"), ("7 그라나다", 325, 425, "Dm/♭II"),
       ("8 바르셀로나", 425, 525, "Dm"), ("9 대문", 525, 580, "Bb")]

path = sys.argv[1] if len(sys.argv) > 1 else "전곡화성.wav"
sr, x = 화성.read_wav(path)        # **자료형을 보고 나눈다** — float32 마스터를
                                   # int16 으로 읽어 −110 dB 를 찍은 적이 있다
mono = x.mean(axis=1)
print("파일 %s  %.1f초  peak %.3f  RMS %.4f  DC %.2e" %
      (path, len(x) / sr, np.abs(x).max(), np.sqrt((mono ** 2).mean()), mono.mean()))
clip = int((np.abs(x) > 0.999).sum())
print("클리핑 샘플 %d   좌우 상관 %.3f" % (clip, np.corrcoef(x[:, 0], x[:, 1])[0, 1]))

# ── 크로마 (반음 12개 대역 에너지, 옥타브 접기) ─────────────────
def chroma(seg):
    n = 1 << 15
    f, t, Z = sg.stft(seg, sr, nperseg=n, noverlap=n // 2)
    P = (np.abs(Z) ** 2).mean(axis=1)
    ok = (f > 55) & (f < 4200)
    f, P = f[ok], P[ok]
    pc = np.rint(12 * np.log2(f / 440.0) + 69).astype(int) % 12
    c = np.zeros(12)
    for i in range(12):
        c[i] = P[pc == i].sum()
    return c / c.sum()


print("\n[악장별 크로마 — 상위 5음]")
for name, a, b, key in MOV:
    c = chroma(mono[a * sr:b * sr])
    top = np.argsort(c)[::-1][:5]
    print("  %-14s %-10s %s" % (name, key,
          "  ".join("%s %.3f" % (NAMES[i], c[i]) for i in top)))

# ── 조성 밖 음 검사 : B♭장조/D프리지안은 같은 음집합 {B♭ C D E♭ F G A}
IN = {10, 0, 2, 3, 5, 7, 9}
print("\n[조성 밖 음 비중 — F♯이 이 곡의 유일한 조성 밖 음이어야 한다]")
for name, a, b, key in MOV:
    c = chroma(mono[a * sr:b * sr])
    out = {NAMES[i]: c[i] for i in range(12) if i not in IN}
    tot = sum(out.values())
    big = sorted(out.items(), key=lambda kv: -kv[1])[:3]
    print("  %-14s 합 %.3f   %s" % (name, tot,
          "  ".join("%s %.3f" % kv for kv in big)))

# ── 대역 균형 ────────────────────────────────────────────────
BANDS = [(30, 90, "초저역"), (90, 250, "저역"), (250, 700, "로우미드"),
         (700, 2000, "미드"), (2000, 5000, "프레즌스"), (5000, 11000, "고역"),
         (11000, 18000, "에어")]
print("\n[대역 에너지 · 전곡 / dB]")
tot = np.sqrt((mono ** 2).mean())
for lo, hi, nm in BANDS:
    sos = sg.butter(4, [lo / (sr / 2), min(hi, 0.49 * sr) / (sr / 2)],
                    btype="band", output="sos")
    y = sg.sosfilt(sos, mono)
    print("  %-8s %6.1f dB" % (nm, 20 * np.log10(max(np.sqrt((y ** 2).mean()) / tot, 1e-9))))

# ── 러프니스 : 2~4kHz 대역의 순간 진폭 변동 (조잡함의 정량 지표) ──
sos = sg.butter(4, [2000 / (sr / 2), 4200 / (sr / 2)], btype="band", output="sos")
h = np.abs(sg.hilbert(sg.sosfilt(sos, mono)[::4]))
h = h / (h.mean() + 1e-12)
print("\n[경직됨 지표] 2~4kHz 포락선 변동계수 %.3f  (낮을수록 부드럽다)" % h.std())

# ── 악장별 RMS (밀도 설계 확인) ──────────────────────────────
# **모노 합산 (L+R)/2 기준이다.** 악장대조.py 는 스테레오 전체를 재므로 같은
# 파일이라도 1 dB 안팎 높게 나온다 — 좌우가 넓은 악장일수록 더 벌어진다.
# `05` 9.x 의 악장별 RMS 는 **이 값**이 정본이다.
print("\n[악장별 RMS / dB · 모노 합산]")
for name, a, b, key in MOV:
    seg = mono[a * sr:b * sr]
    print("  %-14s %6.1f dB" % (name, 20 * np.log10(np.sqrt((seg ** 2).mean()))))

# ── 9악장 F♯→F 해소 구간 확인 ────────────────────────────────
print("\n[피날레 F♯ → F 검사]")
for lab, a, b in [("D장3화음 (F♯)", 566, 569), ("Dm (F)", 569, 572),
                  ("B♭ 종결", 572, 579)]:
    c = chroma(mono[a * sr:b * sr])
    print("  %-14s F♯ %.3f   F %.3f   B♭ %.3f   D %.3f" %
          (lab, c[6], c[5], c[10], c[2]))
