# -*- coding: utf-8 -*-
"""**재즈판을 도시 단위로 잇는다 — 사이에 무음을 넣는다.**

2026-08-29. 검수자 지시 — *"음원 파일 단위로 도시 나누기 ... 세비아는 명확하니까
세비아 중심으로 잘 나누면 될듯. 나중에 사진 붙일지도 모르니까 미리 염두에 두고
작업해야 함. 음원 파일 단위로 mute 1초 내지 2초 삽입하도록 하고."*

## 앞의 판과 무엇이 다른가

| | 앞의 판 | 이 판 |
|---|---|---|
| 잇는 법 | **0.8초 크로스페이드** — 두 토막이 겹친다 | **무음 1.5초** — 겹치지 않는다 |
| 음량 | 토막마다 다르게 곱했다 | **안 곱한다.** 여섯 토막이 −13.9 ~ −15.4 LUFS 로 **1.5 dB 안에 있다** |
| 론다 | `jz2-2-latin-bass` 꼬리에 묻혀 있었다 | **따로 지은 `ronda-walking C (1)`** (검수자 채택) |

**음량을 안 곱하므로 원본이 한 표본도 안 바뀐다.** 자검사가 그것을 확인한다.

## 세비야를 어디서 끊나 — **재서 정했다**

`jz2-2-latin-bass` 는 세비야 · 변주 II · 론다를 한 파일에 담고 있다.
**136.40초에 −35.1 dB 의 빈 자리**가 있고 **136.60초에 새 악구가 −14.8 dB 로 들어온다.**
그 뒤(136.6~164.8)는 저역이 44~49% 로 올라가는 **베이스 구간**이고,
**새 론다가 그 자리를 대신하므로 잘라낸다.**

**짐작이 아니라 0.2초 창으로 재서 가장 조용한 자리를 골랐다** — 2026-08-29 에
악구 한가운데를 잘라 「엉망이 되었다」는 말을 들은 뒤에 세운 방법이다.

## 뚝 끊기는 끝에는 잔향 꼬리를 붙인다

`jz2-1a-piano` 와 `jz2-3-miles-trane` 은 **뒤 무음이 0.00초**다 — 소리가 마지막
표본까지 울리다 끊긴다. **그 뒤에 무음을 넣으면 잘린 소리가 된다.**
`꼬리늘리기.꼬리` 로 여운만 뒤에 잇는다 — **원음은 안 바뀐다.**

## 자검사 — 답을 아는 문제 셋

| 넣는 것 | 나와야 하는 값 |
|---|---|
| 아는 신호 둘을 잇는다 | **총 길이 = 두 길이 합 + 무음** (±1 표본) |
| 같은 결과에서 원본을 찾는다 | **최대 차이 0.0** — 한 표본도 안 바뀐다 |
| 이음매의 무음 길이 | **1.5초** (±0.02초) |

**미달이면 `sys.exit`.**
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 화성
from 꼬리늘리기 import plate, 꼬리, 읽기, 쓰기

sys.stdout.reconfigure(encoding="utf-8")

무음 = 1.5                    # 검수자 「1초 내지 2초」의 가운데
잔향 = 2.6                    # rt60 — 꼬리 약 3초 (2026-08-29 검수자 — "여운은 3초면 됨")
무음문턱 = -50.0

밑 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  "..", "산출물", "20260829 - 재즈 2판")

# 도시 · 파일 · 끝을 자를 시각(초, None 이면 전체) · 끝 처리
구간표 = [
    # **2026-08-29 검수자 지시 — *"여러 소리 말고 원본 그대로 갖다 붙여라."***
    # 자르지 않고 · 페이드 걸지 않고 · 꼬리 붙이지 않고 · 뒤 무음도 안 걷는다.
    # **파일 여섯을 통째로 놓고 사이에 무음만 넣는다.**
    ("프롬나드",              "0악장 완결/0악장 완결 - 앞을 원본 파일로.wav", None, "생"),
    ("마드리드 · 세고비아",   "jz2-1b-bebop.wav",                            None, "생"),
    ("세비야",                "jz2-2-latin-bass.wav",                        None, "생"),
    ("론다",                  "론다/ronda-walking C (1).wav",                None, "생"),
    # **여기만 잔향 꼬리를 붙인다** (2026-08-29 검수자 —
    # *"여기에 잔향 남길 방법은? 곡이 줄어드는 것은 원하지 않음"*).
    # 이 판은 **마지막 표본까지 −19 dB** 로 연주 도중 끊긴다.
    # `꼬리늘리기.꼬리` 는 **원음을 안 바꾸고 뒤에 여운만 잇는다** — 곡이 안 줄어든다.
    ("그라나다 · 바르셀로나", "jz2-3-miles-trane.wav",                       None, "끝페이드"),
    ("위대한 문",             "9악장 페이드/jz2-4-finale - 페이드 5초.wav",  None, "생"),
]


def 뒤무음자르기(x, sr, th=무음문턱):
    """**끝에 남은 무음만 걷어낸다.** 소리는 한 표본도 안 건드린다."""
    m = x.mean(1)
    W = int(0.02 * sr)
    n = len(m) // W
    r = np.array([20 * np.log10(max(np.sqrt((m[i * W:(i + 1) * W] ** 2).mean()), 1e-12))
                  for i in range(n)])
    on = np.where(r > th)[0]
    if not len(on):
        return x, 0.0
    끝 = min(len(x), (on[-1] + 1) * W)
    return x[:끝], (len(x) - 끝) / sr


def 짧은페이드(x, sr, 초=0.35):
    n = int(초 * sr)
    y = x.copy()
    y[-n:] *= np.linspace(1, 0, n)[:, None]
    return y


def 시각(t):
    return "%d:%05.2f" % (int(t // 60), t % 60)


def 자검사():
    """**답을 아는 문제 셋.** 파일에 안 기댄다."""
    sr = 48000
    rng = np.random.default_rng(20051212)
    a = np.stack([rng.standard_normal(sr * 3) * 0.2] * 2, 1)
    b = np.stack([rng.standard_normal(sr * 2) * 0.2] * 2, 1)
    빈 = np.zeros((int(무음 * sr), 2), np.float64)
    out = np.vstack([a, 빈, b])

    실패 = []
    기대 = len(a) + len(빈) + len(b)
    if abs(len(out) - 기대) > 1:
        실패.append("① 총 길이 %d (기대 %d)" % (len(out), 기대))
    if float(np.abs(out[:len(a)] - a).max()) != 0.0:
        실패.append("② 앞 토막이 안 그대로다")
    if float(np.abs(out[len(a) + len(빈):] - b).max()) != 0.0:
        실패.append("② 뒤 토막이 안 그대로다")
    m = out.mean(1)
    조용 = np.abs(m) < 1e-9
    길이 = 조용[len(a):len(a) + len(빈)].sum() / sr
    if abs(길이 - 무음) > 0.02:
        실패.append("③ 이음매 무음이 %.3f초 (기대 %.2f초)" % (길이, 무음))
    return 실패


if __name__ == "__main__":
    실패 = 자검사()
    print("자검사")
    if 실패:
        for s in 실패:
            print("   " + s)
        sys.exit("\n자검사 미달 — 이 도구로 잇지 않는다.")
    print("   → 통과 3/3\n")

    조각, 표 = [], []
    sr = None
    t = 0.0
    for 도시, 파일, 끝, 처리 in 구간표:
        p = os.path.join(밑, 파일)
        s, x = 읽기(p)
        if sr is None:
            sr = s
        elif s != sr:
            sys.exit("표본율이 다르다 — %s 가 %d" % (파일, s))
        원길이 = len(x) / sr
        if 끝 is not None:
            x = x[:int(끝 * sr)]
        if 처리 == "생":
            잘린무음 = 0.0
        else:
            x, 잘린무음 = 뒤무음자르기(x, sr)
        본체 = len(x)
        if 처리 == "꼬리":
            x = np.vstack([x, 꼬리(x, sr, 잔향)])
        elif 처리 == "끝페이드":
            # **잔향이 어색하다는 지적 뒤의 대안** (2026-08-29).
            # 여운을 더하는 대신 **연주 자체를 3초에 걸쳐 줄인다.**
            # 그 3초는 원본과 달라지므로 `본체` 에서 뺀다.
            nf = int(3.0 * sr)
            x = x.copy()
            x[-nf:] *= np.linspace(1, 0, nf)[:, None]
            본체 = len(x) - nf
        elif 처리 == "페이드":
            x = 짧은페이드(x, sr)
            본체 = 0                       # 페이드를 걸었으므로 그대로가 아니다
        조각.append((도시, x, 본체))
        표.append((도시, 파일, 원길이, 끝, 잘린무음, 처리, t, t + len(x) / sr))
        t += len(x) / sr + 무음

    빈 = np.zeros((int(무음 * sr), 2), np.float64)
    붙임 = []
    for i, (_, x, _) in enumerate(조각):
        if i:
            붙임.append(빈)
        붙임.append(x)
    out = np.vstack(붙임)

    낼곳 = os.path.join(밑, "전곡 재즈 2판 - 원본 그대로 · 7-8악장 페이드 3초.wav")
    쓰기(낼곳, sr, out)

    print("%-24s %-10s %-10s %8s %8s" % ("도시", "시작", "끝", "길이", "끝 처리"))
    print("-" * 66)
    for 도시, 파일, 원길이, 끝, 잘린무음, 처리, a, b in 표:
        print("%-24s %-10s %-10s %7.2f초 %8s" % (도시, 시각(a), 시각(b), b - a, 처리))
    print("-" * 66)
    print("총 %s  (%.2f초) · 무음 %.1f초 × %d" % (시각(len(out) / sr), len(out) / sr,
                                                  무음, len(조각) - 1))

    # ── 사진을 붙일 때 쓸 구간표 ────────────────────────────
    #
    # **손으로 안 적는다.** 이 파일에서 나온 값 그대로다 —
    # `뼈대.py` 가 사진을 놓을 때 이것을 읽으면 시각을 다시 세지 않아도 된다.
    구간 = [{"도시": 도시, "시작": round(a, 3), "끝": round(b, 3),
             "길이": round(b - a, 3), "출처": 파일}
            for 도시, 파일, _, _, _, _, a, b in 표]
    with open(os.path.join(밑, "도시 구간.json"), "w", encoding="utf-8") as f:
        json.dump({"파일": os.path.basename(낼곳), "표본율": sr,
                   "총길이": round(len(out) / sr, 3), "무음": 무음,
                   "구간": 구간}, f, ensure_ascii=False, indent=2)

    # ── 원본 보존 확인 ─────────────────────────────────────
    print("\n원본이 그대로 들어 있는가 — 최대 차이가 0.0 이어야 한다")
    off = 0
    for (도시, x, 본체), (_, 파일, _, 끝, _, 처리, _, _) in zip(조각, 표):
        if 본체:
            s, src = 읽기(os.path.join(밑, 파일))
            if 끝 is not None:
                src = src[:int(끝 * sr)]
            d = float(np.abs(out[off:off + 본체] - src[:본체]).max())
            print("   %-24s %s  최대 차이 %.1e" % (도시, "OK " if d == 0 else "★틀림", d))
        else:
            print("   %-24s (페이드를 걸어 원본과 다르다 — 의도)" % 도시)
        off += len(x) + len(빈)
