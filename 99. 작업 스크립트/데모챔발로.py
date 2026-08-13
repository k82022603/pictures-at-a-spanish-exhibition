# -*- coding: utf-8 -*-
"""챔발로 청취 데모 (BL-36 ①, 2026-08-13).

**전곡을 굽기 전에 악기 하나만 들어본다.** 209초짜리 렌더를 돌려놓고
「소리가 이상한데」를 발견하면 그 시간이 통째로 버려진다.

세 구간을 잇는다.

  ① 피아노      — 지금 7악장이 내는 소리
  ② 챔발로      — 바꾸려는 소리
  ③ 챔발로 해부 — 8피트만 · 4피트 겹침 · 잭 소리 뺀 것

**③ 이 있는 이유** — 「챔발로답다」가 어디서 오는지 귀로 가른다. 4피트 현과
잭 소리 중 무엇이 그 일을 하는지 모르면 나중에 조정을 못 한다.

    python 데모챔발로.py

산출 — `데모챔발로.wav`
"""
import numpy as np

import ensemble as ens
import piano
import 화성 as H

SR = 44100

# 7악장 실제 진행에서 넉 줄만 가져온다. 화음도 아르페지오 모양도 같다
PROG = [("Dm7", 6), ("Bbmaj7", 6), ("Gm7", 6), ("Ebmaj7", 6)]
PAT = [0, 1, 2, 3, 2, 1]
BT = 60.0 / (3 * 60)                      # ♩.=60 → 8분음표 0.333초


def _bed(n):
    return np.zeros(n, dtype=np.float64)


def arpeggio(kind, gap=0.0):
    """넉 마디를 아르페지오로 깐다. `kind` 만 다르고 악보는 같다."""
    dur = len(PROG) * 6 * BT + 1.6
    out = _bed(int(dur * SR))
    t = 0.0
    for sym, _ in PROG:
        v = H.voice_lead(sym, None, 57, 79, 4)
        for k in range(6):
            vel = 1.00 if k == 0 else 0.80
            m = v[PAT[k] % len(v)]
            if kind == "piano":
                y = piano.note(int(m), BT * 1.7, vel, 1.3)
            elif kind == "hps":
                y = ens.harpsichord(int(m), BT * 1.7, vel, ring=0.55)
            elif kind == "hps8":                      # 8피트만 — 4피트 없음
                y = ens.harpsichord(int(m), BT * 1.7, vel, ring=0.55, four=0.0)
            elif kind == "hpsnj":                     # 잭 소리 없음
                y = ens.harpsichord(int(m), BT * 1.7, vel, ring=0.55, jack=0.0)
            else:
                raise ValueError(kind)
            i = int((t + k * BT) * SR)
            out[i:i + len(y)] += y[:len(out) - i]
        t += 6 * BT
    return np.concatenate([out, _bed(int(gap * SR))]) if gap else out


def say(txt):
    print(txt)


BLOCKS = [
    ("① 피아노 — 지금의 7악장", "piano"),
    ("② 챔발로 — 바꾸려는 소리", "hps"),
    ("③ 챔발로, 8피트 현만 (옥타브 현 없음)", "hps8"),
    ("④ 챔발로, 잭 소리 없음", "hpsnj"),
]

parts, marks, t = [], [], 0.0
for label, kind in BLOCKS:
    y = arpeggio(kind, gap=1.2)
    r = float(np.sqrt(np.mean(y ** 2)))
    say("%-34s  %5.1f초부터   RMS %6.1f dB" %
        (label, t, 20 * np.log10(r + 1e-12)))
    marks.append((t, label))
    parts.append(y)
    t += len(y) / SR

mix = np.concatenate(parts)
mix = mix / (np.abs(mix).max() + 1e-9) * 0.85
piano.write_wav("데모챔발로.wav", np.stack([mix, mix], 1))
say("")
say("데모챔발로.wav  —  %.1f초" % (len(mix) / SR))
