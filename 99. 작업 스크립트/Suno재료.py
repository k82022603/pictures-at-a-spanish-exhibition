# -*- coding: utf-8 -*-
"""**Suno 에 올릴 재료 — 선율이 주인공인 55초.**

2026-08-20. 검수자 확정 — *"Suno로 진행할거야. 다른 선택지 없음"* ·
*"Suno 로 작업해서 결과가 미진한 것은 Opus 5 네가 채워야 하는거다."*

**어제 무엇이 안 됐나** — 8-19 에 올린 것은 **열 몇 성부의 총주**였고,
Suno 는 그 안의 주제 A 를 못 찾아 **한 옥타브 아래에서 제 마음대로 불렀다**
(`14` 10.2절 — 우리 선율의 최저음 위가 4.7~12.5%). Suno 에는 「이 음을
불러라」를 넣는 자리가 없으므로 **올리는 소리 안에서 선율이 주인공이어야
한다.**

**8-14 에 만든 `안내반주 길잡이음 있음.wav` 는 이 용도가 아니다.**
그것은 **부를 사람**에게 주는 것이라 길잡이 음을 일부러 아주 작게(0.055)
깔았고 반주는 총주 그대로다. **Suno 에 올리면 어제와 거의 같아진다.**
오늘 세운 계획에 「선율만 든 파일이 이미 있다」고 적었는데 **그게 틀렸다.**

**그래서 두 판을 낸다.**

  ① **`Suno 재료 A - 목소리 앞.wav`** — 목소리를 크게, **반주를 −14 dB**.
     박자와 조성의 맥락은 남는다. **이것을 먼저 올린다**
  ② **`Suno 재료 B - 목소리만.wav`** — 반주 없이 목소리 + 딸깍 넷.
     A 가 안 되면 이것을 올린다

**한 번에 하나만 바꾼다**(`13` 문서). 어제 대비 바뀌는 것은 **올리는 파일**
하나이고, 설정값은 어제 판 1 을 그대로 쓴다.

**목소리는 `보컬시험.py` 것을 그대로 쓴다.** 로봇에 가깝지만 상관없다 —
**Suno 에게 「무엇을 부를지」만 알려주면 되고, 「어떻게 부를지」는 Suno 가
한다.** 우리가 받을 것은 Suno 의 목소리뿐이다.

**승인판은 안 건드린다.** 읽어서 섞기만 한다.

    python Suno재료.py
"""
import os
import sys

import numpy as np

import 화성
import synth
import 보컬시험
import 가이드반주

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(HERE, "전곡화성.wav")

T0, T1 = 525.0, 580.0                            # 9악장 8:45~9:40
BAND = -14.0                                     # 판 A 반주 감쇠 (dB)


def db(x):
    return 20.0 * np.log10(max(1e-12, x))


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, float) ** 2)))


def 목소리():
    """네 줄을 우리 가락·우리 가사로 부른 것. 55초 스테레오 버퍼."""
    buf = np.zeros((int((T1 - T0) * SR), 2))
    for t0, name, syls in 보컬시험.LINES:
        v = 보컬시험.line(syls, third=(name == "8행"))
        wet = 화성.plate(v, seed=20260814)
        mix = v + 0.34 * wet[:len(v)]
        mix *= 0.62 / max(1e-9, np.abs(mix).max())
        i = int((t0 + 0.045 - T0) * SR)
        n = min(len(mix), len(buf) - i)
        buf[i:i + n, 0] += mix[:n] * 0.92
        buf[i:i + n, 1] += mix[:n] * 0.72
    return buf


def 딸깍():
    """각 줄 직전에 박을 넷 세어 준다. 판 B 에만 쓴다."""
    buf = np.zeros((int((T1 - T0) * SR), 2))
    for t0, name, _ in 보컬시험.LINES:
        for k in range(4):
            i = int((t0 - (4 - k) * 가이드반주.BT9 - T0) * SR)
            c = 가이드반주.click(hi=(k == 3))
            buf[i:i + len(c), 0] += c
            buf[i:i + len(c), 1] += c
    return buf


def 정규화(x, peak=0.98):
    return x / max(1.0, np.abs(x).max() / peak)


def main():
    print("Suno 에 올릴 재료 — 9악장 8:45~9:40 (55초)\n")

    sr, mst = 화성.read_wav(MASTER)
    if mst.ndim == 1:
        mst = np.stack([mst, mst], 1)
    반주 = mst[int(T0 * SR):int(T1 * SR)].copy()

    v = 목소리()

    판 = [
        ("Suno 재료 A - 목소리 앞", 정규화(v + 반주 * 10.0 ** (BAND / 20.0)),
         "반주를 %.0f dB 낮췄다. 박자·조성의 맥락은 남는다" % BAND),
        ("Suno 재료 B - 목소리만", 정규화(v + 딸깍()),
         "반주 없음. 딸깍 넷이 박을 센다"),
    ]

    print("  %-26s %8s %8s %8s" % ("", "길이", "목소리", "반주"))
    for name, y, _ in 판:
        p = os.path.join(HERE, "%s.wav" % name)
        synth.write_wav(p, y, bits=24)
        # **굽고 되돌려 읽는다** (`납품.py` 와 같은 방식)
        s2, y2 = 화성.read_wav(p)
        if s2 != SR:
            raise SystemExit("갈래가 어긋난다 — %d Hz" % s2)
        n = abs(len(y2) / SR - (T1 - T0))
        if n > 0.001:
            raise SystemExit("길이가 어긋난다 — %.3f초" % (len(y2) / SR))
        print("  %-26s %7.3f초" % (name, len(y2) / SR))

    # **선율이 정말 주인공인가** — 목소리가 있는 구간에서 둘을 견준다
    i = int((527.0 - T0) * SR)
    j = i + int(9.0 * SR)
    a = db(rms(v[i:j])) - db(rms(반주[i:j] * 10.0 ** (BAND / 20.0)))
    b = db(rms(v[i:j])) - db(rms(반주[i:j]))
    print("\n  선율이 반주보다 —  판 A  %+.1f dB   (어제 올린 것 %+.1f dB)" % (a, b))
    print("\n**판 A 를 먼저 올린다.** 설정값은 어제 판 1 그대로.")


if __name__ == "__main__":
    main()
