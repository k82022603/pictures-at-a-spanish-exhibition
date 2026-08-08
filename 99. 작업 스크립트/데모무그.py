# -*- coding: utf-8 -*-
"""
BL-24b 청취 데모 — 무그 자기발진 전후 대조.

숫자 검증(`검증무그.py`)이 통과한 뒤 귀로 확인하는 단계다.
같은 악구(주제 B — 그녀의 주제)를 셋으로 들려준다.

  A. 옛 필터            — 지금까지 승인받은 소리 (되먹임 없음)
  B. 새 필터 · 비명 없음 — 필터만 바뀐 상태. 이 차이가 7·9악장 전체에 걸린다
  C. 새 필터 · 비명      — BL-24b 가 새로 얻은 것

무그를 주제 B로 들려주는 이유는 7악장에서 무그가 그녀의 목소리를 맡기
때문이다. 비명이 음악이 되는지는 그 배역 안에서 판단해야 한다.

실행:  PYTHONUTF8=1 python 데모무그.py
"""
import numpy as np

import piano
import synth

SR = synth.SR

# 주제 B — 그녀. 주제 A와 같은 도수를 D 프리지안에 얹은 것 (CLAUDE.md 6절)
THEME_B = [(70, 1.0), (69, 1.0), (74, 1.0), (75, .5), (81, .5), (77, 1.0),
           (75, .5), (81, .5), (77, 1.0), (74, 1.0), (75, 2.6)]

BEAT = 0.46          # 7악장 6/8 ♩.=50 을 느슨하게 옮긴 것
GAP = 1.1            # 셋 사이 여백


def phrase(scream=0.0, old=False):
    """주제 B 한 번. old=True 면 옛 ladder_sweep 경로로 렌더한다."""
    total = sum(d for _, d in THEME_B) * BEAT + 1.2
    buf = np.zeros(synth.n_samples(total))
    t = 0.0
    prev = None
    for i, (m, d) in enumerate(THEME_B):
        dur = d * BEAT
        # 마지막 긴 음에서 비명이 피어오르게 한다 — 고전적인 무그 어법이다
        sc = scream if i == len(THEME_B) - 1 else scream * 0.35
        y = synth.moog(m, dur + 0.35, gain=0.62, cut_hi=4600, res=0.5,
                       glide_from=prev, scream=sc)
        s = synth.n_samples(t)
        buf[s:s + len(y)] += y[:max(len(buf) - s, 0)]
        prev = m
        t += dur
    return buf


print("BL-24b 청취 데모를 만듭니다. 30초 정도 걸립니다.")

# A — 옛 필터. moog() 본체는 그대로 두고 필터만 옛것으로 갈아끼운다.
# ladder_sweep 의 인자 규약이 ladder_nl 과 호환되므로(스칼라 res) 이렇게 대조할 수 있다.
_new = synth.ladder_nl
synth.ladder_nl = lambda x, ce, res=0.5, **kw: _new.__globals__["ladder_sweep"](
    x, ce, res=float(np.mean(res)))
print("  A. 옛 필터 …")
a = phrase(scream=0.0)
synth.ladder_nl = _new

print("  B. 새 필터 · 비명 없음 …")
b = phrase(scream=0.0)

print("  C. 새 필터 · 비명 …")
c = phrase(scream=0.9)

gap = np.zeros(synth.n_samples(GAP))
mono = np.concatenate([a, gap, b, gap, c])
mono = mono / max(np.max(np.abs(mono)), 1e-9) * 0.89

# 좁은 스테레오 — 판단에 방해되지 않을 만큼만
st = np.stack([mono, mono], axis=1)
out = "../무그 자기발진 데모 - BL-24b.wav"
piano.write_wav(out, st)

def seg_rms(y):
    return float(np.sqrt(np.mean(y ** 2)))

print("\n=== 구간별 실측 ===")
for name, y in (("A 옛 필터        ", a), ("B 새 필터 비명없음", b), ("C 새 필터 비명   ", c)):
    print("  %s  RMS %.4f · 최대 %.3f" % (name, seg_rms(y), float(np.max(np.abs(y)))))

print("\n저장: %s" % out)
print("길이 %.1f초 (A %.1f초 · B %.1f초 · C %.1f초, 사이 %.1f초 여백)"
      % (len(mono) / SR, len(a) / SR, len(b) / SR, len(c) / SR, GAP))
