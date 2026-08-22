# -*- coding: utf-8 -*-
"""**사그라드는 끝을 더 길게 — 잔향 여운을 이어 붙인다.**

2026-08-22. 검수자 요청 — *"앞부분 꼬리가 조금 더 길면 좋을 것 같음."*

## 왜 「뒤를 더 쓰기」가 아닌가

0악장 Extend 판의 사그라듦은 **1:05.25 에 시작해 1:08.00 에 바닥**(−31.3 dB)이고,
**1:08.25 부터 새 악구가 다시 올라온다**(−26 → −18.6). 그러니 자르는 지점을
뒤로 밀면 **사그라듦이 길어지는 게 아니라 다음 악구가 섞인다.**

**그래서 없는 시간을 만든다 — 마지막 몇 초를 잔향에 통과시켜 그 꼬리만 뒤에 잇는다.**
원음은 한 표본도 안 바뀌고 **뒤에 여운만 붙는다.**

## 왜 `화성.plate` 를 안 쓰나

**그 모듈의 `SR` 은 44100 이고 Suno 음원은 48000 이다.** 그대로 쓰면 `rt60` 이
44.1/48 배로 짧아진다 — **숫자는 맞는데 소리가 다른** 종류의 사고다.
그래서 표본율을 인자로 받는 판을 여기 둔다. 설계(감쇠 잡음을 임펄스 응답으로
삼는다·고역을 늦게 깎는다)는 `화성.plate` 와 같다.
"""
import os
import sys

import numpy as np
from scipy import signal as sg
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 화성

sys.stdout.reconfigure(encoding="utf-8")


def 읽기(p):
    """**`화성.read_wav` 가 자료형을 본다.** 직접 `/ 32768` 하지 않는다 — 마스터가
    float32 로 바뀐 날 도구 여섯이 전부 −110 dB 를 찍은 적이 있다(`검증.py` 7번)."""
    sr, x = 화성.read_wav(p)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    return sr, x


def 쓰기(p, sr, x):
    """**float32 로 쓴다. `int16` 으로 떨어뜨리지 않는다.**

    2026-08-22 에 `납품.py` 가 경고를 찍어 발견했다 — *"마스터가 s16 이다.
    32비트로 못 간다."* **Suno 원본이 16비트라 정보를 깎은 것은 아니지만,
    우리가 더한 것**(잔향 꼬리 · 크로스페이드 · 페이드)**은 계산이 더 정밀한데
    16비트로 양자화됐다.** 꼬리 끝이 **−85 dB** 인데 16비트 잡음 바닥이
    **−96 dB** 라 **여유가 11 dB 뿐**이었다.

    **이 프로젝트가 같은 모양을 세 번째 겪었다** — ① `write_wav` 가 마스터만
    16비트로(넉 달) ② `ffmpeg -sample_fmt s32` 가 24비트로 ③ 여기.
    **셋 다 「이름이 값과 다르다」이고, 셋 다 도구가 찍어줘서 알았다.**
    """
    wavfile.write(p, sr, np.clip(x, -1, 1).astype(np.float32))


def plate(x, sr, rt60=3.0, damp=7600.0, hp=190.0, seed=0):
    """감쇠하는 잡음을 임펄스 응답으로 삼는 플레이트 잔향. 좌우 씨앗이 다르다."""
    n = int(rt60 * 1.15 * sr)
    t = np.arange(n) / sr
    감쇠 = np.exp(-6.91 * t / rt60)
    lo = sg.butter(2, min(damp, sr / 2 * 0.98), "low", fs=sr, output="sos")
    hi = sg.butter(2, hp, "high", fs=sr, output="sos")
    out = np.zeros((len(x) + n - 1, 2))
    for c in range(2):
        rng = np.random.default_rng(7311 + seed + c * 101)
        ir = rng.standard_normal(n) * 감쇠
        ir = sg.sosfilt(hi, sg.sosfilt(lo, ir))
        ir = ir / (np.sqrt((ir ** 2).sum()) + 1e-12)
        out[:, c] = sg.fftconvolve(x[:, c], ir)[: len(x) + n - 1]
    return out


def 꼬리(x, sr, rt60, 재료=4.0, 세기=1.0):
    """마지막 `재료` 초를 잔향에 넣고 **꼬리 부분만** 돌려준다.

    원음 뒤에 그대로 이어 붙이면 여운이 자연스럽게 이어진다.
    세기는 원음 끝 부분의 크기에 맞춰 정규화한다 — 손으로 dB 를 고르지 않는다.
    """
    src = x[-int(재료 * sr):]
    wet = plate(src, sr, rt60=rt60)
    t = wet[len(src):]                       # 원음과 겹치는 부분을 뺀 순수 꼬리
    끝 = np.sqrt((src[-int(0.3 * sr):] ** 2).mean())
    지금 = np.sqrt((t[: int(0.3 * sr)] ** 2).mean()) + 1e-12
    return t * (끝 / 지금) * 세기


if __name__ == "__main__":
    B = "../산출물/20260822 - 0악장을 다시 만든다/받은 것 - 0악장 Extend"
    sr, ext = 읽기(B + "/0악장 Extend-01 (43초부터).wav")
    본편 = ext[: int(68.00 * sr)]             # 검수자 채택 — 긴판 68초
    M1 = "../산출물/20260821 - 전곡을 Suno 에 넘긴다/Suno 전곡 맡기기/받은 것 - 1부b/1부b Suno-03.wav"
    _, m1 = 읽기(M1)

    def 잇기(a, b, ms=20):
        n = int(ms / 1000 * sr)
        f = np.linspace(0, 1, n)[:, None]
        a = a.copy()
        a[-n:] = a[-n:] * (1 - f) + b[:n] * f
        return np.vstack([a, b[n:]])

    def dbv(a):
        return 20 * np.log10(np.sqrt((a ** 2).mean()) + 1e-12)

    # ── 1부b 도 여기서 만든다 (2026-08-22) ────────────────────
    #
    # **처음에는 즉석 스크립트로 만들었다.** 그러면 다시 만들 수가 없고,
    # 실제로 16비트 사고 뒤 다시 만들어야 했을 때 그 코드가 없었다.
    # **검수자가 채택한 값은 도구에 박아 둔다.**
    M1 = ("../산출물/20260821 - 전곡을 Suno 에 넘긴다/Suno 전곡 맡기기"
          "/받은 것 - 1부b/1부b Suno-03.wav")
    _, m1 = 읽기(M1)
    쓰기("../산출물/20260822 - 0악장을 다시 만든다/받은 것 - 1부b Extend"
         "/1부b - 꼬리 3.5초.wav", sr, np.vstack([m1, 꼬리(m1, sr, 3.05)]))
    print("1부b     %.2f초 + 꼬리 3.51초  (검수자 채택 「꼬리 3.5초」)" % (len(m1) / sr))

    print("원본 68.00초 · 끝 0.5초 %.1f dB" % dbv(본편[-int(0.5 * sr):]))
    for 이름, rt in [("짧게 +2초", 2.2), ("보통 +3.5초", 4.0), ("길게 +5초", 5.6)]:
        t = 꼬리(본편, sr, rt)
        판 = np.vstack([본편, t])
        쓰기("%s/0악장 - 꼬리 %s.wav" % (B, 이름), sr, 판)
        발췌 = 잇기(판[-int(12 * sr):], m1[: int(12 * sr)])   # 이음매를 늘 0:12 에 둔다
        쓰기("%s/발췌 - 꼬리 %s 에서 1악장으로.wav" % (B, 이름), sr, 발췌)
        print("  %-12s  총 %5.2f초 (꼬리 %4.2f초) · 꼬리 끝 %6.1f dB"
              % (이름, len(판) / sr, len(t) / sr, dbv(판[-int(0.5 * sr):])))
