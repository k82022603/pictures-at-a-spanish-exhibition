# -*- coding: utf-8 -*-
"""두 wav 를 악장별로 대조한다. T-07 규칙 — 고친 악장만 보지 않는다.

    python 악장대조.py "기준선.wav" 전곡화성.wav

**대조는 반드시 같은 도구로 양쪽을 잰다.** 2026-08-08 에 이 스크립트와
`검증화성.py` 의 절대값을 견주다 7악장이 1.8 dB 떨어진 줄 알았는데,
스테레오를 다루는 방식이 달랐을 뿐이고 실제로는 불변이었다 (`05` 9.17.5절).
"""
import sys, io, numpy as np, scipy.io.wavfile as wf
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

MOV = [("0 프롬나드", 0, 50), ("1 마드리드", 50, 90), ("2 변주 I", 90, 105),
       ("3 세고비아", 105, 160), ("4 세비야", 160, 260), ("5 변주 II", 260, 275),
       ("6 론다", 275, 325), ("7 그라나다", 325, 425),
       ("8 바르셀로나", 425, 525), ("9 대문", 525, 580)]

a_path, b_path = sys.argv[1], sys.argv[2]
sr, a = wf.read(a_path)
sr, b = wf.read(b_path)
a = a.astype(np.float64) / 32768
b = b.astype(np.float64) / 32768
n = min(len(a), len(b))

def db(x):
    r = np.sqrt((x ** 2).mean()) if len(x) else 0.0
    return 20 * np.log10(max(r, 1e-12))

# **스테레오 전체 RMS 다.** 검증화성.py 의 모노 합산과 1 dB 안팎 다르므로
# 이 표의 절대값을 문서에 옮기지 않는다. 이 도구가 보는 것은 **두 렌더의 차이**다.
print("(스테레오 RMS — 절대값의 정본은 검증화성.py 의 모노 합산)")
print("%-12s %10s %10s %8s %12s" % ("악장", "기준선", "새 렌더", "차이", "차이 RMS"))
print("-" * 58)
for nm, s, e in MOV:
    i, j = int(s * sr), min(int(e * sr), n)
    x, y = a[i:j], b[i:j]
    d = x - y
    print("%-12s %9.1f  %9.1f  %+7.2f %11.1f" % (nm, db(x), db(y), db(y) - db(x), db(d)))

d = a[:n] - b[:n]
print("-" * 58)
print("%-12s %9.1f  %9.1f  %+7.2f %11.1f" % ("전곡", db(a[:n]), db(b[:n]),
                                             db(b[:n]) - db(a[:n]), db(d)))
rms = [db(b[int(s*sr):min(int(e*sr), n)]) for _, s, e in MOV]
print()
print("새 렌더 RMS 폭  %.1f dB   (최대 %s %.1f · 최소 %s %.1f)" % (
    max(rms) - min(rms),
    MOV[int(np.argmax(rms))][0], max(rms),
    MOV[int(np.argmin(rms))][0], min(rms)))
