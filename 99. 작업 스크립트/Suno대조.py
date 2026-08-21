# -*- coding: utf-8 -*-
"""**Suno 가 낸 것이 우리 곡인가** — 올린 것과 나온 것을 화성으로 대조한다.

2026-08-21. `17` 9절의 판정표 중 **2번(우리 화성이 남았는가)**을 숫자로 만든다.
귀로 「같은 곡인가」를 보는 것이 정본이고, 이 도구는 **그 판정을 도울 숫자**를 낸다.

무엇을 하나 — 두 음원을 **8초 창**으로 썰어 창마다 크로마(어느 음이 얼마나
울리는가)를 재고, 같은 시각의 두 크로마가 얼마나 닮았는지 본다.

  | 값 | 뜻 |
  |---|---|
  | **0.90 이상** | 같은 화성을 연주한다 |
  | 0.75~0.90 | 진행은 따라가되 색을 바꿨다 |
  | **0.60 아래** | **딴 곡이다** |

**자기검사가 있다** — 돌리기 전에 ① 자기 자신과 대조하면 1.000 이 나오는가
② 반음 올린 것과 대조하면 뚝 떨어지는가 를 확인한다. 안 맞으면 멈춘다.

    python Suno대조.py 올린것.wav 나온것.wav [나온것2.wav ...]
"""
import sys

import numpy as np
from scipy import signal as sg

import 화성

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
NAMES = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]
음집합 = [10, 0, 2, 3, 5, 7, 9]                    # B♭ C D E♭ F G A
창 = 8.0                                           # 초


def 읽기(path):
    sr, x = 화성.read_wav(path)
    mono = x.mean(axis=1) if x.ndim > 1 else x
    if sr != SR:                                   # Suno 는 48000 으로 낸다
        n = int(round(len(mono) * SR / sr))
        mono = sg.resample(mono, n)
    return mono.astype(np.float64)


def 크로마(seg):
    n = 1 << 14
    if len(seg) < n:
        return np.full(12, 1 / 12)
    f, t, Z = sg.stft(seg, SR, nperseg=n, noverlap=n // 2)
    P = (np.abs(Z) ** 2).mean(axis=1)
    ok = (f > 55) & (f < 4200)
    f, P = f[ok], P[ok]
    pc = np.rint(12 * np.log2(f / 440.0) + 69).astype(int) % 12
    c = np.array([P[pc == i].sum() for i in range(12)])
    s = c.sum()
    return c / s if s > 0 else np.full(12, 1 / 12)


def 창별크로마(mono):
    h = int(창 * SR)
    return [크로마(mono[i:i + h]) for i in range(0, len(mono) - h // 2, h)]


def 닮음(a, b):
    """두 크로마열의 창별 코사인 닮음. 짧은 쪽에 맞춘다."""
    n = min(len(a), len(b))
    v = [float(np.dot(a[i], b[i]) /
               (np.linalg.norm(a[i]) * np.linalg.norm(b[i]) + 1e-12))
         for i in range(n)]
    return np.array(v)


def 밖(c):
    """음집합 밖 음의 비율."""
    return float(1.0 - sum(c[i] for i in 음집합))


def 자검사(mono):
    """**아는 답 둘.** 자기 자신 = 1.000 · 반음 올린 것은 뚝 떨어져야 한다."""
    a = 창별크로마(mono)
    s1 = 닮음(a, a).mean()
    b = [np.roll(c, 1) for c in a]                 # 반음 올린 것과 같다
    s2 = 닮음(a, b).mean()
    print("자검사  자기 자신 %.3f (1.000 이어야)   반음 올림 %.3f (낮아야)"
          % (s1, s2))
    if abs(s1 - 1.0) > 1e-6 or s2 > 0.85:
        sys.exit("자검사 실패 — 자가 틀렸다. 재지 않는다")


def 표(이름, mono, 기준크로마, 기준길이):
    c = 창별크로마(mono)
    v = 닮음(기준크로마, c)
    상위 = np.argsort(-np.mean(c, axis=0))[:5]
    print("\n[%s]" % 이름)
    print("  길이 %.2f초 (올린 것 %.2f초 · 차이 %+.2f초)"
          % (len(mono) / SR, 기준길이, len(mono) / SR - 기준길이))
    print("  ★ 화성 닮음  평균 %.3f   최저 %.3f   0.90 넘는 창 %d/%d (%.0f%%)"
          % (v.mean(), v.min(), (v >= 0.90).sum(), len(v),
             100 * (v >= 0.90).mean()))
    print("  음집합 밖 %.3f   많이 울린 음 %s"
          % (밖(np.mean(c, axis=0)), " ".join(NAMES[i] for i in 상위)))
    print("  창별(8초): " + " ".join("%.2f" % x for x in v))
    return v


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    올린 = 읽기(sys.argv[1])
    print("올린 것  %s  %.2f초" % (sys.argv[1], len(올린) / SR))
    자검사(올린)
    기준 = 창별크로마(올린)
    for p in sys.argv[2:]:
        표(p, 읽기(p), 기준, len(올린) / SR)
