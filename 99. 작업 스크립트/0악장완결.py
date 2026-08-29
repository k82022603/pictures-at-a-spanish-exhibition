# -*- coding: utf-8 -*-
"""**0악장에 마무리를 붙인다 — 원본은 한 표본도 안 바꾸고.**

2026-08-29. 검수자 — *"suno 에게 `jz2-1a-piano.wav` 완결 버전 더 만들어달라고 해줘 ...
`jz2-1a-piano.wav` 과 완벽하게 일치해야 한다고 분명히 말해주고."*

## 왜 Suno 에게 다 못 맡기나

**Suno `Extend` 는 「일치」를 못 지킨다.** 전체를 `KEEP` 으로 두고 재 봤더니
**상관 0.998742 · 표본 대 표본 최대 0.35** 였다 — 같은 연주지만 **다시 렌더한 파일**이다.
경위는 [`30`](<../30. 재즈판을 만든다 — 프롬프트와 설계.md>) 11절.

**그리고 「10초 안에 끝내라」가 안 먹었다.** 뒷부분이 0:52·0:52·4:00·4:00 로 나왔고
**4분 51초를 끝까지 들어도 곡이 안 내려앉는다.**

## 그래서 이렇게 한다

| | |
|---|---|
| 앞 | **우리 `jz2-1a-piano.wav` 그대로** (0 → 갈라지는 시각) |
| 이음매 | 40 ms 크로스페이드 — 다시 렌더된 소리로 넘어가는 자리를 감춘다 |
| 뒤 | **Suno Full Song 의 새 연주**를 「조용한 자리」까지 |
| 끝 | 페이드 + 잔향 꼬리 |

**갈라지는 시각은 짐작하지 않고 잰다** — 0.5초 창으로 상관을 훑어 0.999 아래로
떨어지는 첫 자리를 쓴다.

## 자검사 — 답을 아는 문제 셋

| 넣는 것 | 나와야 하는 값 |
|---|---|
| 아는 신호 둘로 만든 판 | **앞부분이 최대 차이 0.0** (크로스페이드 앞까지) |
| 같은 신호를 앞뒤로 | **갈라지는 시각을 못 찾는다**(= 끝까지 같다) |
| 1초 뒤부터 다른 신호 | **갈라지는 시각 ≈ 1.0초** (±0.5) |

**미달이면 `sys.exit`.**
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 꼬리늘리기 import 꼬리, 읽기, 쓰기

sys.stdout.reconfigure(encoding="utf-8")

밑 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  "..", "산출물", "20260829 - 재즈 2판")
낼곳 = os.path.join(밑, "0악장 완결")
겹침 = 0.040          # 이음매 크로스페이드

# 어느 커버에서 나온 판인가에 따라 짝이 다르다.
# **원본과 Suno 판은 반드시 같은 커버에서 나온 것끼리 짝지어야 한다** —
# 2026-08-29 에 커버 둘을 헷갈려 엉뚱한 짝으로 만든 적이 있다.
짝 = {
    "채택본": (os.path.join(밑, "jz2-1a-piano.wav"),
               os.path.join(낼곳, "Suno Full Song 4m51 - 채택본에서.wav"),
               [("가 - 15.8초", 66.70, 1.2), ("나 - 18.6초", 69.50, 1.5)]),
    "(1)": (os.path.join(밑, "jz2-1a-piano (1).wav"),
            os.path.join(낼곳, "Suno Full Song 1m44 - (1) 커버에서.wav"),
            None),          # 자를 자리를 재서 정한다
}


def 갈라지는곳(A, B, sr, 창=0.5, 문턱=0.999):
    """A 와 B 가 몇 초부터 달라지나. **짐작하지 않는다.**"""
    W = int(창 * sr)
    a = A.mean(1) if A.ndim == 2 else A
    b = B.mean(1) if B.ndim == 2 else B
    n = min(len(a), len(b))
    for i in range(0, n - W, W):
        x, y = a[i:i + W], b[i:i + W]
        if np.std(x) < 1e-9 or np.std(y) < 1e-9:
            continue
        if np.corrcoef(x, y)[0, 1] < 문턱:
            return i / sr
    return None


def 잇기(앞, 뒤, sr):
    n = int(겹침 * sr)
    f = np.linspace(0, 1, n)[:, None]
    앞 = 앞.copy()
    앞[-n:] = 앞[-n:] * (1 - f) + 뒤[:n] * f
    return np.vstack([앞, 뒤[n:]])


def 자검사():
    sr = 48000
    rng = np.random.default_rng(20051212)
    a = np.stack([rng.standard_normal(sr * 3) * 0.2] * 2, 1)
    b = a.copy()
    실패 = []
    if 갈라지는곳(a, b, sr) is not None:
        실패.append("① 같은 신호인데 갈라지는 곳을 찾았다")
    c = a.copy()
    c[sr:] = np.stack([rng.standard_normal(sr * 2) * 0.2] * 2, 1)
    t = 갈라지는곳(a, c, sr)
    if t is None or abs(t - 1.0) > 0.5:
        실패.append("② 1초부터 다른 신호에서 %s (기대 1.0초)" % t)
    붙인 = 잇기(a[:sr], b[sr:sr * 2], sr)
    n = int(겹침 * sr)
    if float(np.abs(붙인[:sr - n] - a[:sr - n]).max()) != 0.0:
        실패.append("③ 앞부분이 안 그대로다")
    return 실패


if __name__ == "__main__":
    실패 = 자검사()
    print("자검사")
    if 실패:
        for s in 실패:
            print("   " + s)
        sys.exit("\n자검사 미달 — 이 도구로 안 만든다.")
    print("   → 통과 3/3\n")

    어느 = sys.argv[1] if len(sys.argv) > 1 else "채택본"
    if 어느 not in 짝:
        sys.exit("모르는 짝: %s  (%s 중 하나)" % (어느, " · ".join(짝)))
    원본, 새판, 후보 = 짝[어느]
    print("짝: %s" % 어느)
    print()

    sr, O = 읽기(원본)
    s2, F = 읽기(새판)
    if sr != s2:
        sys.exit("표본율이 다르다")

    t = 갈라지는곳(O, F, sr)
    print("원본 %.2f초 · Suno 판 %.2f초" % (len(O) / sr, len(F) / sr))
    if t is None:
        # **끝까지 안 갈라졌다** — Suno 가 원본 전체를 그대로 두고 뒤에만 붙였다는 뜻이다.
        t = len(O) / sr
        print("갈라지는 자리가 없다 — 원본 전체가 그대로 들어 있다")
    print("갈라지는 시각 %.2f초  ← 여기까지가 우리 원본이다\n" % t)
    자름 = int(t * sr)

    if 후보 is None:
        # **이 판은 Suno 가 스스로 끝을 맺었다** — 자를 것이 없다.
        # 끝 3초가 −33 → −63 dB 로 사그라드는지 재서 확인하고 그대로 쓴다.
        m = F.mean(1)
        def db(a):
            return 20 * np.log10(max(np.sqrt((a ** 2).mean()), 1e-12))
        끝dB = db(m[-int(0.3 * sr):])
        if 끝dB > -40:
            sys.exit("이 판도 끝이 안 맺힌다 (끝 %.1f dB) — 자를 자리를 찾아야 한다" % 끝dB)
        판 = 잇기(O, F[자름:], sr)
        n = int(겹침 * sr)
        d = float(np.abs(판[:len(O) - n] - O[:len(O) - n]).max())
        p2 = os.path.join(낼곳, "0악장 완결 - 앞을 원본 파일로.wav")
        쓰기(p2, sr, 판)
        print("앞을 원본 파일로  총 %6.2f초 (원본 %.2f + Suno 마무리 %.2f)  "
              "원본 최대 차이 %.1e  끝 %6.1f dB"
              % (len(판) / sr, t, len(F) / sr - t, d, 끝dB))
        sys.exit(0)

    for 이름, 끝, 페이드 in 후보:
        뒤 = F[자름:int(끝 * sr)].copy()
        nf = int(페이드 * sr)
        뒤[-nf:] *= np.linspace(1, 0, nf)[:, None]
        판 = 잇기(O[:자름], 뒤, sr)
        판 = np.vstack([판, 꼬리(판, sr, 3.0)])
        p = os.path.join(낼곳, "0악장 완결 %s.wav" % 이름)
        쓰기(p, sr, 판)
        d = float(np.abs(판[:자름 - int(겹침 * sr)] - O[:자름 - int(겹침 * sr)]).max())
        끝dB = 20 * np.log10(np.sqrt((판[-int(0.3 * sr):] ** 2).mean()) + 1e-12)
        print("%-12s  총 %6.2f초 (원본 %.2f + 새 연주 %.2f + 꼬리)  "
              "원본 최대 차이 %.1e  끝 %6.1f dB"
              % (이름, len(판) / sr, t, 끝 - t, d, 끝dB))
