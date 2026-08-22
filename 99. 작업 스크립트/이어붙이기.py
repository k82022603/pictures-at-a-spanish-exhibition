# -*- coding: utf-8 -*-
"""**다섯 조각을 한 곡으로 잇는다.**

2026-08-22. 조각들은 서로를 모른 채 따로 만들어졌다. **이음매가 들리는지가 관건**이므로
**먼저 크로스페이드 없이 잇고**, 이음매만 잘라낸 발췌를 함께 낸다 —
페이드를 먼저 걸면 어긋남이 가려진다.

**48 kHz 를 유지한다.** Suno 가 48 로 내주고 최종 목적지가 유튜브(48)다.
44.1 로 내렸다 올리면 두 번 손해다.
"""
import os
import sys

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 화성

sys.stdout.reconfigure(encoding="utf-8")
SR = 48000
B = "../산출물/20260821 - 전곡을 Suno 에 넘긴다/Suno 전곡 맡기기"
C = "../산출물/20260822 - 0악장을 다시 만든다"

조각 = [
    ("0악장",  C + "/받은 것 - 0악장/0악장 Suno-02.wav"),
    ("1~3악장", B + "/받은 것 - 1부b/1부b Suno-03.wav"),
    ("4~6악장", B + "/받은 것 - 2부/2부 Suno-03.wav"),
    ("7~8악장", B + "/받은 것 - 3부/3부 Suno-04.wav"),
    ("9악장",  B + "/받은 것 - 4부/4부 Suno-03.wav"),
]

XF = 0.020          # 20 ms — 클릭만 막는다. 어긋남은 가리지 않는다


def 읽기(p):
    """**`화성.read_wav` 가 자료형을 본다.** 직접 `/ 32768` 하지 않는다 — 마스터가
    float32 로 바뀐 날 도구 여섯이 전부 −110 dB 를 찍은 적이 있다(`검증.py` 7번)."""
    sr, x = 화성.read_wav(p)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    return sr, x


def 잇기(조각들, xf=XF):
    n = int(xf * SR)
    out = None
    경계 = []
    for _, p in 조각들:
        m = 읽기(p)
        if out is None:
            out = m.copy()
        else:
            경계.append(len(out) / SR)
            f = np.linspace(0, 1, n)[:, None]
            out[-n:] = out[-n:] * (1 - f) + m[:n] * f
            out = np.vstack([out, m[n:]])
    return out, 경계


if __name__ == "__main__":
    전곡, 경계 = 잇기(조각)
    print("이은 길이  %.2f초  (%d:%02d)" % (len(전곡)/SR, int(len(전곡)/SR)//60, int(len(전곡)/SR)%60))
    print("이음매     " + " · ".join("%d:%05.2f" % (int(t)//60, t % 60) for t in 경계))
    print()

    os.makedirs(C + "/이어붙인 것", exist_ok=True)
    def 쓰기(path, x):
        wavfile.write(path, SR, np.clip(x, -1, 1).astype(np.float32))

    쓰기(C + "/이어붙인 것/전곡 A - 그대로 이은 것.wav", 전곡)

    # 이음매 발췌 — 각 이음매 앞뒤 8초, 사이에 1.5초 무음
    앞뒤 = 8.0
    쉼 = np.zeros((int(1.5 * SR), 2))
    조각들 = []
    for i, t in enumerate(경계):
        a = int((t - 앞뒤) * SR)
        b = int((t + 앞뒤) * SR)
        조각들.append(전곡[max(0, a):min(len(전곡), b)])
        if i < len(경계) - 1:
            조각들.append(쉼)
    발췌 = np.vstack(조각들)
    쓰기(C + "/이어붙인 것/이음매 넷 - 앞뒤 8초씩.wav", 발췌)
    print("이음매 발췌  %.1f초 — 네 자리, 사이에 1.5초 쉼" % (len(발췌)/SR))
    print()
    for i, t in enumerate(경계):
        s = i * (앞뒤 * 2 + 1.5)
        print("  발췌 %4.1f~%4.1f초  =  전곡 %d:%05.2f  (%s → %s)"
              % (s, s + 앞뒤*2, int(t)//60, t % 60, 조각[i][0], 조각[i+1][0]))
