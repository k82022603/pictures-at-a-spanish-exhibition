# -*- coding: utf-8 -*-
"""음원의 **바닥**을 훑어 구멍을 찾는다.

    python 무음구간.py 전곡화성.wav [기준 dB]

**평균 RMS 는 「조용해졌다」와 「일찍 끝났다」를 구분하지 못한다** — 2026-08-10
에 5악장이 15초 슬롯에 8.7초만 채우고 4:30 에 완전 무음 4.8초를 내고 있었는데,
악장 평균만 보고 통과시켰다. 그날 이 검사를 손으로 했고, 오늘 스크립트로 남긴다.

기준값은 −35 dB 다. 그 아래로 0.4초 넘게 내려가면 **구멍**으로 본다.
4악장에는 설계된 정적이 셋 있으므로 (`05` 9.15절) 그 셋은 표에 남되 구멍이
아니다 — 자동 판정하지 않고 사람이 본다.
"""
import sys, io, numpy as np, scipy.io.wavfile as wf
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

MOV = [("0 프롬나드", 0, 50), ("1 마드리드", 50, 90), ("2 변주 I", 90, 105),
       ("3 세고비아", 105, 160), ("4 세비야", 160, 260), ("5 변주 II", 260, 275),
       ("6 론다", 275, 325), ("7 그라나다", 325, 425),
       ("8 바르셀로나", 425, 525), ("9 대문", 525, 580)]

path = sys.argv[1]
FLOOR = float(sys.argv[2]) if len(sys.argv) > 2 else -35.0
WIN, HOP, MINLEN = 0.10, 0.05, 0.40

sr, x = wf.read(path)
x = x.astype(np.float64) / 32768
if x.ndim > 1:
    x = x.mean(axis=1)

n = int(WIN * sr)
h = int(HOP * sr)
lv, tm = [], []
for i in range(0, len(x) - n, h):
    w = x[i:i + n]
    lv.append(20 * np.log10(max(np.sqrt((w ** 2).mean()), 1e-12)))
    tm.append(i / sr)
lv, tm = np.array(lv), np.array(tm)


def mov(t):
    for nm, s, e in MOV:
        if s <= t < e:
            return nm
    return "?"


print("파일 %s   기준 %.0f dB   %.1f초 이상만" % (path, FLOOR, MINLEN))
print("%-12s %8s %8s %8s  %s" % ("악장", "시작", "길이", "최저", "구간"))
print("-" * 56)
low = lv < FLOOR
i, found = 0, 0
while i < len(low):
    if low[i]:
        j = i
        while j < len(low) and low[j]:
            j += 1
        dur = tm[min(j, len(tm) - 1)] - tm[i]
        if dur >= MINLEN:
            found += 1
            print("%-12s %7.1fs %7.2fs %7.1f  %d:%02d~%d:%02d" %
                  (mov(tm[i]), tm[i], dur, lv[i:j].min(),
                   int(tm[i]) // 60, int(tm[i]) % 60,
                   int(tm[i] + dur) // 60, int(tm[i] + dur) % 60))
        i = j
    else:
        i += 1
print("-" * 56)
print("구멍 후보 %d 곳" % found)

print("\n[악장별 바닥 — 하위 5%%]")
for nm, s, e in MOV:
    m = (tm >= s) & (tm < e)
    if m.any():
        print("  %-12s 하위5%% %6.1f dB   최저 %6.1f dB" %
              (nm, np.percentile(lv[m], 5), lv[m].min()))
