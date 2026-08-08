# -*- coding: utf-8 -*-
"""
BL-24b 검증 — 무그 라더가 실제로 자기발진하는가.

이 프로젝트는 음악을 귀가 아니라 숫자로 먼저 판정한다. 이 스크립트는
"비명이 난다"는 주장을 다음 네 가지로 확인한다.

  1. 입력 0에서 소리가 나는가        — 자기발진의 정의. 안 나면 발진이 아니다
  2. 발진 음정이 컷오프를 따라가는가  — 컷오프 Hz ↔ 음높이 대응 정확도 (센트)
  3. 진폭이 발산하지 않는가          — tanh 포화가 리미트 사이클을 만드는가
  4. 옛 필터와의 대조                — ladder_sweep 은 같은 조건에서 침묵해야 한다

실행:  PYTHONUTF8=1 python 검증무그.py
"""
import time

import numpy as np

import synth

SR = synth.SR
FAIL = []


def peak_freq(y, sr=SR):
    """정상상태 구간의 기본 주파수. 앞 40%는 과도상태라 버린다.

    FFT 빈 폭은 110Hz에서 22센트나 되므로 최대 빈을 그대로 쓰면
    측정 해상도가 판정하려는 오차보다 크다. 로그 크기 스펙트럼의
    최대점 좌우에 포물선을 맞춰 빈 사이를 보간한다.
    """
    seg = y[int(len(y) * 0.4):]
    if len(seg) < 4096:
        return 0.0
    w = seg * np.hanning(len(seg))
    sp = np.abs(np.fft.rfft(w))
    i = int(np.argmax(sp))
    if i <= 0 or i >= len(sp) - 1:
        return float(np.fft.rfftfreq(len(w), 1.0 / sr)[i])
    # 포물선 보간 — 빈 사이 참 최대점의 위치를 찾는다
    a, b, c = (np.log(max(sp[i + d], 1e-30)) for d in (-1, 0, 1))
    delta = 0.5 * (a - c) / (a - 2 * b + c)
    return (i + delta) * sr / len(w)


def rms(y):
    return float(np.sqrt(np.mean(y ** 2))) if len(y) else 0.0


def check(cond, msg):
    print(("  OK    " if cond else "  FAIL  ") + msg)
    if not cond:
        FAIL.append(msg)


# ------------------------------------------------------------------ 1. 발진
print("=== 1. 입력 0에서 자기발진하는가 ===")
dur = 1.5
n = synth.n_samples(dur)
silence = np.zeros(n)

for fc in (220.0, 440.0, 880.0):
    ce = np.full(n, fc)
    y = synth.ladder_nl(silence, ce, res=1.0)
    r = rms(y)
    fp = peak_freq(y)
    cents = 1200.0 * np.log2(fp / fc) if fp > 0 else float("nan")
    print("    컷오프 %6.1f Hz  →  RMS %.4f · 발진 %7.1f Hz · 오차 %+7.1f 센트"
          % (fc, r, fp, cents))
    check(r > 0.01, "컷오프 %.0f Hz 에서 발진했다 (RMS %.4f)" % (fc, r))

# ------------------------------------------------- 2. 임계 아래에서는 조용한가
print("\n=== 2. 임계 아래(res=0.5)에서는 발진하지 않는가 ===")
y_q = synth.ladder_nl(silence, np.full(n, 440.0), res=0.5)
r_q = rms(y_q)
print("    res=0.50  →  RMS %.6f" % r_q)
check(r_q < 0.005, "임계 아래에서는 침묵한다 (RMS %.6f)" % r_q)

y_o = synth.ladder_nl(silence, np.full(n, 440.0), res=1.0)
print("    res=1.00  →  RMS %.6f  (%.0f배)" % (rms(y_o), rms(y_o) / max(r_q, 1e-9)))
check(rms(y_o) > r_q * 20, "임계를 넘으면 확실히 갈라진다")

# ------------------------------------------------------------- 3. 음정 정확도
print("\n=== 3. 발진 음정이 컷오프를 따라가는가 ===")
errs = []
for fc in (110.0, 220.0, 440.0, 880.0, 1760.0):
    y = synth.ladder_nl(np.zeros(synth.n_samples(1.2)),
                        np.full(synth.n_samples(1.2), fc), res=1.0)
    fp = peak_freq(y)
    c = 1200.0 * np.log2(fp / fc) if fp > 0 else 9999.0
    errs.append(abs(c))
    print("    %7.1f Hz  →  %7.1f Hz   %+7.1f 센트" % (fc, fp, c))
worst = max(errs)
print("    최대 오차 %.1f 센트" % worst)
check(worst < 50, "발진 음정이 컷오프에 맞는다 (최대 %.1f 센트)" % worst)

# ------------------------------------------------------------- 4. 진폭 안정성
print("\n=== 4. 진폭이 발산하지 않는가 (tanh 리미트 사이클) ===")
y_long = synth.ladder_nl(np.zeros(synth.n_samples(4.0)),
                         np.full(synth.n_samples(4.0), 440.0), res=1.0)
q = len(y_long) // 4
seg_rms = [rms(y_long[i * q:(i + 1) * q]) for i in range(4)]
print("    4등분 RMS: " + " · ".join("%.4f" % s for s in seg_rms))
print("    절대 최대값 %.3f" % float(np.max(np.abs(y_long))))
check(np.isfinite(y_long).all(), "발산하지 않는다 (NaN/Inf 없음)")
check(np.max(np.abs(y_long)) < 12.0, "진폭이 묶여 있다 (최대 %.2f)"
      % float(np.max(np.abs(y_long))))
check(seg_rms[3] > seg_rms[1] * 0.5, "발진이 꺼지지 않고 유지된다")

# --------------------------------------------------------- 5. 옛 필터와 대조
print("\n=== 5. 옛 ladder_sweep 은 같은 조건에서 침묵하는가 ===")
y_old = synth.ladder_sweep(silence, np.full(n, 440.0), res=1.0)
print("    ladder_sweep res=1.0  →  RMS %.8f" % rms(y_old))
print("    ladder_nl    res=1.0  →  RMS %.8f" % rms(y_o))
check(rms(y_old) < 1e-4, "옛 필터는 발진하지 못한다 — 되먹임이 없기 때문")

# ------------------------------------------- 6. 레조넌스가 스윕을 따라가는가
print("\n=== 6. 레조넌스 봉우리가 컷오프 스윕을 따라가는가 ===")
# 화이트 노이즈를 넣고 컷오프를 쓸어내리며, 앞/뒤 구간의 스펙트럼 무게중심을 본다.
nn = synth.n_samples(2.0)
noise = np.random.default_rng(7).normal(0, 0.2, nn)
ce_sweep = np.geomspace(4000.0, 400.0, nn)
for label, fn in (("옛 ladder_sweep", synth.ladder_sweep),
                  ("새 ladder_nl", synth.ladder_nl)):
    y = fn(noise, ce_sweep, res=0.8)
    a, b = y[:nn // 4], y[-nn // 4:]
    fa, fb = peak_freq(a), peak_freq(b)
    print("    %-16s 앞구간 피크 %7.1f Hz → 뒷구간 %7.1f Hz  (비 %.2f)"
          % (label, fa, fb, fb / max(fa, 1e-9)))

# ------------------------------------------------------------------ 7. 속도
print("\n=== 7. 속도 ===")
t0 = time.perf_counter()
synth.ladder_nl(np.zeros(SR), np.full(SR, 1000.0), res=0.9)
el = time.perf_counter() - t0
print("    1초 오디오 처리에 %.3f초  (2배 오버샘플링 포함)" % el)
print("    무그 캐시 260개 × 평균 0.8초 기준 전곡 렌더 추가분 ≈ %.1f초" % (el * 260 * 0.8))

print("\n" + "=" * 52)
if FAIL:
    print("%d건 실패:" % len(FAIL))
    for f in FAIL:
        print("  - " + f)
    raise SystemExit(1)
print("BL-24b 자기발진 검증 통과.")
