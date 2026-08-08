"""
ELP-style progressive rock synth engine (pure numpy/scipy).
Hammond organ (drawbar additive + Leslie), Moog lead (ladder filter sweep),
bass, and a synthesized drum kit.
"""
import numpy as np
from scipy import signal

SR = 44100


def midi2f(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def n_samples(dur):
    return int(round(dur * SR))


def env_adsr(n, a=0.01, d=0.08, s=0.7, r=0.15):
    a, d, r = max(a, 1e-4), max(d, 1e-4), max(r, 1e-4)
    na, nd, nr = n_samples(a), n_samples(d), n_samples(r)
    ns = max(n - na - nd - nr, 0)
    if na + nd + nr > n:  # short note: scale down
        k = n / float(na + nd + nr)
        na, nd, nr = int(na * k), int(nd * k), int(nr * k)
        ns = 0
    e = np.concatenate([
        np.linspace(0, 1, na, endpoint=False) if na else np.array([]),
        np.linspace(1, s, nd, endpoint=False) if nd else np.array([]),
        np.full(ns, s),
        np.linspace(s, 0, nr) if nr else np.array([]),
    ])
    if len(e) < n:
        e = np.pad(e, (0, n - len(e)))
    return e[:n]


def exp_decay(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


# ---------------------------------------------------------------- filter bank
_CUTS = np.geomspace(120.0, 16000.0, 96)
_BANK = [signal.butter(4, min(c, 0.45 * SR) / (SR / 2), btype="low", output="ba")
         for c in _CUTS]


def ladder_sweep(x, cut_env, res=0.0, block=192):
    """Time-varying 4-pole lowpass. Blockwise lfilter with carried state,
    plus a resonance peak to emulate the Moog ladder's self-oscillating bite."""
    y = np.zeros_like(x)
    zi = None
    prev = -1
    for i in range(0, len(x), block):
        seg = x[i:i + block]
        c = float(np.clip(np.mean(cut_env[i:i + block]), _CUTS[0], _CUTS[-1]))
        idx = int(np.argmin(np.abs(_CUTS - c)))
        b, a = _BANK[idx]
        if zi is None or idx != prev:
            zi_new = signal.lfilter_zi(b, a) * (seg[0] if len(seg) else 0.0)
            zi = zi_new if zi is None else zi[:len(zi_new)]
            prev = idx
        out, zi = signal.lfilter(b, a, seg, zi=zi)
        y[i:i + block] = out
    if res > 0:
        # resonant peak tracking the average cutoff
        fc = float(np.clip(np.mean(cut_env), 150, 12000))
        q = 1.0 + res * 9.0
        bq = signal.iirpeak(fc / (SR / 2), q)
        y = y + res * 1.2 * signal.lfilter(bq[0], bq[1], y)
    return y


# ------------------------------------------- 비선형 라더 필터 (BL-24b, v1.9)
# ladder_sweep() 은 되먹임이 없다. 레조넌스를 병렬 피크 EQ로 "더해서" 흉내내므로
# 극점이 움직이지 않고, 따라서 res 를 아무리 올려도 자기발진이 원리적으로 불가능하다.
# 게다가 피크 주파수를 컷오프 포락선의 평균 하나로 고정해 스윕을 따라가지도 못한다.
#
# 아래는 진짜 트랜지스터 사다리다. 1극 저역통과 4단을 직렬로 걸고 출력을 입력에서
# 빼되(되먹임 이득 k), 각 단에 tanh 포화를 넣는다. k가 임계(선형 모델에서 4)를
# 넘으면 극점이 단위원 밖으로 나가 필터가 입력 없이 스스로 컷오프 주파수에서
# 발진한다 — ELP의 그 비명이다. tanh 가 이득을 진폭에 따라 떨어뜨려 발진이
# 발산하지 않고 일정 크기의 리미트 사이클로 안정된다. 실제 무그에서 그 일을
# 하는 것이 사다리 트랜지스터의 비선형성이고, 그래서 발진음이 순수한 사인이
# 아니라 살짝 찌그러진 우는 소리가 된다.

K_OSC = 4.0          # 선형 모델의 자기발진 임계
K_MAX = 4.5          # res=1.0 이 대응하는 되먹임 이득

# 옛 ladder_sweep 과 출력 레벨을 맞추는 계수.
# 필터를 바꾸면서 무그 스템이 3.8 dB 조용해졌다 — 전곡 렌더 두 벌의 lead 스템
# RMS 실측이 −26.6 dB(옛) 대 −30.4 dB(새)였다. 그대로 두면 7악장이 0.5 dB,
# 9악장이 0.2 dB 내려앉고, 무엇보다 9:26 F♯→F 해소의 F♯ 비중이 0.149에서
# 0.089로 떨어져 **곡의 결론이 흐려진다.** 승인받은 믹스를 지키는 것이 맞으므로
# 페이더가 아니라 악기 쪽에서 되돌린다.
#
# 주의 — 이 계수는 3.8 dB(=1.549)가 아니다. moog() 가 필터 **뒤에**
# tanh(y*1.6) 으로 포화를 걸기 때문에, 포화 앞에서 밀어 넣은 이득은 압축돼
# 그대로 나오지 않는다. 실제로 1.549 를 넣었더니 2.6 dB 만 나왔다(-1.2 dB 부족).
# 그래서 최종 출력이 옛 필터와 같아지는 값을 이분 탐색으로 풀었다. 포화를
# 앞이 아니라 뒤에서 보정하면 이 문제가 없지만, 그러면 tanh 를 때리는 세기가
# 달라져 포화량 자체가 변한다 — 음색을 지키려면 포화 앞에서 맞추는 쪽이 맞다.
# 대표 표본 48음(cut 3400~5400 · res 0.24~0.50 · midi 60~84)으로 실측. (2026-08-06)
LEVEL_MATCH = 2.0151


def _ladder_g(fc, sr):
    """되먹임 루프가 정확히 fc 에서 발진하도록 1극 계수를 정한다.

    흔히 쓰는 `g = 1 - exp(-2πfc/sr)` 는 1극의 컷오프를 근사한 값일 뿐,
    4단을 직렬로 걸고 되먹인 루프가 실제로 발진하는 주파수가 아니다.
    그대로 쓰면 저역에서 34센트 낮고 고역에서 27센트 높게 운다 — 실측값이다.
    무그가 7악장에서 그녀의 목소리를 맡는다면 그 목소리는 음정이 맞아야 한다.

    그래서 근사 대신 위상 조건을 직접 푼다. 발진은 루프 위상이 180°일 때
    일어나고, 4단이 각각 φ 만큼, 되먹임의 반 샘플 지연이 ω/2 만큼 늦추므로

        4·φ(ω, g) + 1.5ω = π,   φ = atan((1-g)·sinω / (1 - (1-g)·cosω))

    이다. a = 1-g 로 두고 정리하면 닫힌 형태로 풀린다.

        a = tanφ / (sinω + tanφ·cosω)

    보정 계수가 아니라 구현된 차분식의 해다.

    지연이 1.5샘플인 것에 주의 — 되먹임 경로는 0.5·(y4[n-1] + y4[n-2]) 이다.
    평균이 반 샘플을 늦추고, 루프 자체가 이미 한 샘플을 늦춘다. 처음에 이
    한 샘플을 빼먹고 0.5ω 로 계산했더니 오차가 34센트에서 138센트로 나빠졌다.
    """
    w = 2.0 * np.pi * np.asarray(fc, dtype=float) / sr
    w = np.clip(w, 1e-6, 0.95 * np.pi)
    tp = np.tan(np.clip((np.pi - 1.5 * w) / 4.0, 1e-4, np.pi / 2 - 1e-4))
    a = tp / (np.sin(w) + tp * np.cos(w))
    return np.clip(1.0 - a, 1e-5, 0.995)


# 위 선형 해가 남기는 잔차 — tanh 포화가 발진 진폭에서 실효 이득을 낮추는 몫이다.
# 진폭 의존이라 선형 이론으로는 안 나오므로 실측해서 표로 박는다.
# 측정 조건: 입력 0 · res=1.0 · 2.5초 · FFT 포물선 보간. (2026-08-06)
# 무그 음역(262~1047Hz)과 비명 자리(그 2옥타브 위)를 덮는 100~4400Hz 구간이다.
_TUNE_HZ = np.array([100.0, 137.1, 187.9, 257.6, 353.0, 483.9, 663.3,
                     909.2, 1246.3, 1708.4, 2341.8, 3210.0, 4400.0])
_TUNE_CENTS = np.array([-41.7, -41.6, -40.9, -40.2, -39.4, -38.0, -36.2,
                        -33.7, -30.2, -25.3, -18.5, -9.0, -6.5])


def _tune(fc):
    """실측 잔차를 상쇄하도록 요청 컷오프를 미리 밀어 둔다.

    발진하지 않는 구간에서는 컷오프가 음높이가 아니므로 이 보정이
    들리지 않는다(최대 2.4% 이동). 발진할 때만 의미를 갖는다.
    """
    fc = np.asarray(fc, dtype=float)
    c = np.interp(np.log2(np.clip(fc, 1.0, 20000.0)),
                  np.log2(_TUNE_HZ), _TUNE_CENTS)
    return fc * 2.0 ** (-c / 1200.0)


def ladder_nl(x, cut_env, res=0.5, oversample=2, noise=3e-6, seed=None):
    """무그 라더 — 되먹임 + 단별 tanh 포화. 자기발진한다.

    res 0~1 을 되먹임 이득 k 0~K_MAX 로 매핑한다. res ≳ 0.89 에서 발진이 시작된다.
    res 는 스칼라 또는 x 와 같은 길이의 배열 — 배열로 주면 한 음 안에서
    비명이 피어오르게 할 수 있다.

    되먹임 경로에 반 샘플 지연을 둔 것은 발진 음정을 맞추기 위해서다.
    자기발진 중에는 컷오프 주파수가 곧 들리는 음높이가 되므로, 이 필터를
    선율 악기로 쓰려면 컷오프 Hz ↔ 음높이 대응이 정확해야 한다.

    벡터화할 수 없다 — y4[n] 이 다음 샘플의 입력으로 되돌아간다. 샘플 단위
    파이썬 루프이므로 tanh 는 math 쪽(스칼라 C 함수)을 쓰고, 포락선은
    미리 계산해 list 로 바꿔 둔다. numpy 스칼라 인덱싱보다 그쪽이 빠르다.
    """
    import math

    n = len(x)
    if n == 0:
        return x.copy()

    # 오버샘플링 — tanh 가 만드는 고조파의 앨리어싱을 막는다
    if oversample > 1:
        xs = signal.resample_poly(x, oversample, 1)
        ce = np.interp(np.linspace(0, 1, len(xs)),
                       np.linspace(0, 1, n), cut_env)
        rs = (np.interp(np.linspace(0, 1, len(xs)),
                        np.linspace(0, 1, n), np.asarray(res, dtype=float))
              if np.ndim(res) else None)
        sr = SR * oversample
    else:
        xs, ce, rs, sr = np.asarray(x, dtype=float), np.asarray(cut_env, dtype=float), \
            (np.asarray(res, dtype=float) if np.ndim(res) else None), SR

    m = len(xs)
    # 1극 계수. 컷오프가 나이퀴스트에 너무 붙으면 발산하므로 묶는다
    fc = np.clip(_tune(ce), 20.0, 0.45 * sr)
    g_env = _ladder_g(fc, sr)
    k_env = (rs * K_MAX) if rs is not None else np.full(m, float(res) * K_MAX)

    # 열잡음 — 실제 아날로그 발진기를 깨우는 것이 바로 이것이다.
    # 입력이 완전한 0이면 수치적으로 0에 머물러 발진이 시작되지 않는다.
    #
    # BL-30 — 씨앗을 받는다. 예전에는 `np.random`(전역·무씨앗)을 써서
    # **렌더할 때마다 다른 소리가 나왔다.** 잡음이 있어야 발진이 시작되는 것은
    # 맞지만, 그것이 매번 달라야 할 이유는 없다.
    if noise > 0:
        rng = np.random.default_rng(20260807 if seed is None else int(seed))
        xs = xs + rng.uniform(-noise, noise, m)

    xl = xs.tolist()
    gl = g_env.tolist()
    kl = k_env.tolist()
    out = [0.0] * m

    tanh = math.tanh
    y1 = y2 = y3 = y4 = 0.0
    t1 = t2 = t3 = t4 = 0.0     # 각 단의 직전 tanh (재계산 회피)
    y4_prev = 0.0               # 되먹임 반 샘플 지연용

    for i in range(m):
        g = gl[i]
        # 되먹임 — 반 샘플 지연을 걸어 발진 음정을 컷오프에 맞춘다
        fb = 0.5 * (y4 + y4_prev)
        y4_prev = y4
        u = tanh(xl[i] - kl[i] * fb)
        y1 += g * (u - t1);  t1 = tanh(y1)
        y2 += g * (t1 - t2); t2 = tanh(y2)
        y3 += g * (t2 - t3); t3 = tanh(y3)
        y4 += g * (t3 - t4); t4 = tanh(y4)
        out[i] = y4

    y = np.asarray(out)
    if oversample > 1:
        y = signal.resample_poly(y, 1, oversample)[:n]
        if len(y) < n:
            y = np.pad(y, (0, n - len(y)), mode="edge")
    # 4극 통과 시 저역이 얇아진 것을 되돌리고(되먹임이 클수록 많이 깎인다),
    # 옛 필터와 출력 레벨을 맞춘다
    return y * LEVEL_MATCH * (1.0 + 0.9 * float(np.mean(k_env)) / K_MAX)


def saw(freq_env, phase0=0.0):
    ph = phase0 + np.cumsum(freq_env) / SR
    return 2.0 * (ph - np.floor(ph + 0.5))


def square(freq_env, duty=0.5, phase0=0.0):
    ph = (phase0 + np.cumsum(freq_env) / SR) % 1.0
    return np.where(ph < duty, 1.0, -1.0)


# ------------------------------------------------------------- hammond organ
# Drawbar registration: 16', 5 1/3', 8', 4', 2 2/3', 2', 1 3/5', 1 1/3', 1'
DRAWBARS = [0.5, 1.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
REG_FULL = [8, 6, 8, 6, 4, 5, 3, 2, 6]      # full organ, Emerson-ish scream
REG_SOFT = [8, 3, 7, 4, 2, 2, 1, 0, 2]      # mellower


def hammond(midi, dur, reg=REG_FULL, gain=1.0, drive=2.2, leslie=6.6, click=0.5,
            seed=None):
    n = n_samples(dur)
    t = np.arange(n) / SR
    f0 = midi2f(midi)
    out = np.zeros(n)
    # slight Leslie pitch wobble
    vib = 1.0 + 0.0016 * np.sin(2 * np.pi * leslie * t)
    for mult, amt in zip(DRAWBARS, reg):
        if amt <= 0:
            continue
        f = f0 * mult
        if f > 0.45 * SR:
            continue
        out += (amt / 8.0) * np.sin(2 * np.pi * np.cumsum(f * vib) / SR)
    out /= max(sum(1 for a in reg if a > 0), 1) ** 0.5
    # key click — BL-30: 씨앗을 받는다. 예전에는 전역·무씨앗 난수라 매번 달랐다
    if click > 0:
        nc = n_samples(0.006)
        rng = np.random.default_rng(int(midi) * 7919 + 13 if seed is None else int(seed))
        out[:nc] += click * rng.uniform(-1, 1, nc) * exp_decay(nc, 0.0015)
    e = env_adsr(n, a=0.004, d=0.02, s=0.95, r=0.05)
    out *= e
    # tube overdrive + Leslie amplitude tremolo
    out = np.tanh(out * drive) / np.tanh(drive)
    out *= 1.0 - 0.22 * (0.5 + 0.5 * np.sin(2 * np.pi * leslie * t + 1.1))
    return gain * out


def organ_chord(midis, dur, reg=REG_FULL, gain=1.0, drive=2.2):
    n = n_samples(dur)
    out = np.zeros(n)
    for m in midis:
        out += hammond(m, dur, reg=reg, gain=1.0, drive=1.0, click=0.35)
    out /= len(midis) ** 0.6
    out = np.tanh(out * drive) / np.tanh(drive)
    return gain * out


# ------------------------------------------------------------------ moog lead
def moog(midi, dur, gain=1.0, cut_hi=5200, cut_lo=420, res=0.55,
         glide_from=None, detune=0.012, sub=0.35, scream=0.0, scream_oct=2,
         vib=0.0, vib_hz=5.4, vib_wait=0.45, seed=None):
    """무그 리드. v1.9부터 되먹임 라더(`ladder_nl`)를 쓴다.

    vib — 벨팅 비브라토의 **반음 단위 최대 폭** (WBS 1.4.8). 0 이면 없다.
    지속음의 앞 `vib_wait` 비율 동안은 곧게 내다가 그 뒤로 폭이 차오른다.
    사람이 긴 음을 지탱할 때 일어나는 일이고, 처음부터 일정한 기본 비브라토가
    기계처럼 들리는 이유이기도 하다.

    scream 0~1 — 되먹임을 자기발진 임계 너머로 밀어 올린다. 0이면 종전처럼
    레조넌스만 걸린 소리이고, 1이면 필터가 스스로 운다.

    자기발진 중에는 **컷오프 주파수가 곧 들리는 음높이**가 되므로, scream>0 이면
    컷오프 꼬리를 연주 음의 scream_oct 옥타브 위에 앉힌다. 그래야 비명이
    조성 안에 있다. 이 처리를 안 하면 필터는 울되 음악과 무관한 음높이로 운다.
    """
    n = n_samples(dur)
    f = midi2f(midi)
    if glide_from is not None:
        gl = n_samples(min(0.07, dur * 0.4))
        fenv = np.concatenate([np.geomspace(midi2f(glide_from), f, gl),
                               np.full(n - gl, f)])[:n]
    else:
        fenv = np.full(n, f)
    if vib > 0:
        # 벨팅 비브라토 (WBS 1.4.8) — 지속음의 뒤로 갈수록 폭이 넓어진다.
        #
        # 사람이 긴 음을 지탱할 때 일어나는 일이다. 처음에는 곧게 내다가
        # 숨이 길어지면 흔들림이 커진다. 신디사이저의 기본 비브라토는 처음부터
        # 일정해서 기계처럼 들리는데, 그 차이가 여기 있다.
        #
        # `vib` 는 **반음 단위 최대 폭**이다. 0.25 면 사분음쯤 흔들린다.
        # 앞 `vib_wait` 비율 동안은 0 이고 그 뒤로 선형으로 차오른다.
        tv = np.arange(n) / SR
        grow = np.clip((tv / max(dur, 1e-6) - vib_wait) / max(1e-6, 1 - vib_wait), 0, 1)
        depth = (2.0 ** (vib / 12.0) - 1.0) * grow
        fenv = fenv * (1.0 + depth * np.sin(2 * np.pi * vib_hz * tv))
    x = saw(fenv) + 0.75 * saw(fenv * (1 + detune), 0.31) + \
        0.5 * square(fenv * 0.5, 0.5) * sub / 0.35 * 0.7
    # filter envelope: snap down then hold (classic Moog "wow")
    na = n_samples(min(0.02, dur * 0.2))
    nd = n_samples(min(0.28, dur * 0.6))
    tail = max(cut_lo, 300.0)
    if scream > 0:
        # 발진 음정을 연주 음에 묶는다 — 컷오프가 곧 음높이이므로
        tail = float(f) * (2.0 ** scream_oct)
    ce = np.concatenate([np.linspace(cut_lo, cut_hi, na),
                         np.geomspace(cut_hi, tail, nd),
                         np.full(max(n - na - nd, 0), tail)])[:n]
    if len(ce) < n:
        ce = np.pad(ce, (0, n - len(ce)), mode="edge")

    if scream > 0:
        # 임계(K_OSC/K_MAX ≈ 0.889) 아래에서 시작해 넘어간다 — 비명이 피어오른다
        top = K_OSC / K_MAX + (1.0 - K_OSC / K_MAX) * float(np.clip(scream, 0, 1))
        nr = n_samples(min(0.18, dur * 0.35))
        rv = np.concatenate([np.linspace(res, top, nr),
                             np.full(max(n - nr, 0), top)])[:n]
        if len(rv) < n:
            rv = np.pad(rv, (0, n - len(rv)), mode="edge")
    else:
        rv = res

    y = ladder_nl(x, ce, res=rv, seed=seed)
    y *= env_adsr(n, a=0.012, d=0.06, s=0.85, r=min(0.12, dur * 0.5))
    y = np.tanh(y * 1.6)
    return gain * y * 0.5


# ---------------------------------------------------------------------- bass
def bass(midi, dur, gain=1.0, cut=900, res=0.25):
    n = n_samples(dur)
    f = np.full(n, midi2f(midi))
    x = saw(f) * 0.8 + square(f, 0.42) * 0.5 + np.sin(2 * np.pi * np.cumsum(f * 0.5) / SR) * 0.6
    ce = np.concatenate([np.geomspace(cut * 3.2, cut, n_samples(min(0.06, dur))),
                         np.full(max(n - n_samples(min(0.06, dur)), 0), cut)])[:n]
    if len(ce) < n:
        ce = np.pad(ce, (0, n - len(ce)), mode="edge")
    y = ladder_sweep(x, ce, res=res)
    y *= env_adsr(n, a=0.004, d=0.05, s=0.8, r=min(0.08, dur * 0.4))
    # pick attack
    nc = n_samples(0.004)
    y[:nc] += 0.25 * np.random.uniform(-1, 1, nc) * exp_decay(nc, 0.001)
    return gain * np.tanh(y * 1.4) * 0.55


# ---------------------------------------------------------------------- drums
def kick(gain=1.0):
    n = n_samples(0.42)
    fe = np.concatenate([np.geomspace(150, 48, n_samples(0.055)),
                         np.full(n - n_samples(0.055), 48.0)])
    y = np.sin(2 * np.pi * np.cumsum(fe) / SR) * exp_decay(n, 0.085)
    nc = n_samples(0.004)
    y[:nc] += 0.6 * np.random.uniform(-1, 1, nc) * exp_decay(nc, 0.0012)
    return gain * np.tanh(y * 1.8) * 0.95


def snare(gain=1.0, tau=0.11):
    n = n_samples(0.30)
    nz = np.random.uniform(-1, 1, n)
    b, a = signal.butter(2, [180 / (SR / 2), 8200 / (SR / 2)], btype="band")
    nz = signal.lfilter(b, a, nz) * exp_decay(n, tau)
    t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * 186 * t) + 0.7 * np.sin(2 * np.pi * 274 * t)) * exp_decay(n, 0.045)
    y = 0.78 * nz + 0.42 * tone
    return gain * np.tanh(y * 1.5) * 0.8


def hat(open_=False, gain=1.0):
    tau = 0.26 if open_ else 0.035
    n = n_samples(tau * 4 + 0.02)
    nz = np.random.uniform(-1, 1, n)
    b, a = signal.butter(4, 7200 / (SR / 2), btype="high")
    y = signal.lfilter(b, a, nz) * exp_decay(n, tau)
    return gain * y * 0.60


def tom(midi=48, gain=1.0):
    n = n_samples(0.45)
    f0 = midi2f(midi)
    fe = np.concatenate([np.geomspace(f0 * 1.6, f0, n_samples(0.04)),
                         np.full(n - n_samples(0.04), f0)])
    y = np.sin(2 * np.pi * np.cumsum(fe) / SR) * exp_decay(n, 0.13)
    nz = np.random.uniform(-1, 1, n) * exp_decay(n, 0.012) * 0.18
    return gain * np.tanh((y + nz) * 1.5) * 0.7


def crash(gain=1.0, tau=1.1):
    n = n_samples(2.6)
    nz = np.random.uniform(-1, 1, n)
    b, a = signal.butter(2, 3600 / (SR / 2), btype="high")
    y = signal.lfilter(b, a, nz)
    t = np.arange(n) / SR
    y *= exp_decay(n, tau) * (1 + 0.25 * np.sin(2 * np.pi * 7.3 * t))
    return gain * y * 0.55


# ------------------------------------------------------------------ mix bus
class Mix:
    def __init__(self, dur):
        self.L = np.zeros(n_samples(dur) + SR * 4)
        self.R = np.zeros_like(self.L)

    def add(self, sig, at, gain=1.0, pan=0.0):
        i = n_samples(at)
        j = i + len(sig)
        if j > len(self.L):
            pad = j - len(self.L) + 1
            self.L = np.pad(self.L, (0, pad))
            self.R = np.pad(self.R, (0, pad))
        gl = gain * np.cos((pan + 1) * np.pi / 4)
        gr = gain * np.sin((pan + 1) * np.pi / 4)
        self.L[i:j] += sig * gl * 1.414
        self.R[i:j] += sig * gr * 1.414

    def stereo(self, trim=None, reverb=0.16, peak=0.89, master_eq=True,
               glue=True):
        L, R = self.L.copy(), self.R.copy()
        if trim:
            k = n_samples(trim)
            L, R = L[:k], R[:k]
        if reverb > 0:
            L = L + reverb * _reverb(L, 0)
            R = R + reverb * _reverb(R, 1)
        if master_eq:
            L, R = _master_eq(L), _master_eq(R)
            # mid/side width: widen the sides, keep bass centred
            M, S = (L + R) / 2, (L - R) / 2
            S = signal.lfilter(*signal.butter(2, 180 / (SR / 2), btype="high"), S)
            L, R = M + 1.85 * S, M - 1.85 * S
        if glue:
            L, R = _glue(L, R)
        m = max(np.abs(L).max(), np.abs(R).max(), 1e-9)
        L, R = L / m * peak, R / m * peak
        return np.stack([L, R], axis=1)


def _shelf(x, fc, gain_db, kind="high"):
    """First-order shelving EQ."""
    g = 10 ** (gain_db / 20.0)
    b, a = signal.butter(2, min(fc, 0.45 * SR) / (SR / 2),
                         btype="high" if kind == "high" else "low")
    return x + (g - 1.0) * signal.lfilter(b, a, x)


def _master_eq(x):
    x = signal.lfilter(*signal.butter(2, 28 / (SR / 2), btype="high"), x)  # rumble
    x = _shelf(x, 55, -3.0, "low")        # tighten the very bottom
    x = _shelf(x, 2400, 6.0, "high")      # organ/cymbal presence
    x = _shelf(x, 8500, 1.5, "high")      # air
    # scoop a little boxy low-mid
    bq = signal.iirpeak(340 / (SR / 2), 1.1)
    x = x - 0.16 * signal.lfilter(bq[0], bq[1], x)
    return x


def _glue(L, R, thresh=0.38, ratio=3.0, atk=0.004, rel=0.14):
    """Soft bus compression on the stereo sum, then tape-ish saturation."""
    det = np.maximum(np.abs(L), np.abs(R))
    a_c = np.exp(-1.0 / (atk * SR))
    r_c = np.exp(-1.0 / (rel * SR))
    # fast envelope follower (blockwise for speed)
    blk = 64
    n = len(det)
    env = np.zeros(n // blk + 1)
    e = 0.0
    peaks = np.array([det[i:i + blk].max() for i in range(0, n, blk)])
    for i, p in enumerate(peaks):
        c = a_c if p > e else r_c
        e = c * e + (1 - c) * p
        env[i] = e
    env = np.interp(np.arange(n), np.arange(len(env)) * blk, env[:len(env)])
    over = np.maximum(env / thresh, 1.0)
    gain = over ** (1.0 / ratio - 1.0)
    L, R = L * gain, R * gain
    drive = 1.25
    return np.tanh(L * drive) / drive, np.tanh(R * drive) / drive


def _reverb(x, seed=0):
    rng = np.random.default_rng(1234 + seed)
    y = np.zeros(len(x))
    for dl, g in [(0.031, 0.55), (0.047, 0.45), (0.071, 0.38), (0.097, 0.30),
                  (0.131, 0.24), (0.173, 0.18)]:
        d = n_samples(dl * (1 + 0.03 * rng.standard_normal()))
        buf = np.zeros(len(x))
        buf[d:] = x[:-d]
        # simple feedback comb
        a = np.zeros(len(x))
        fb = 0.62
        step = d
        cur = buf.copy()
        for k in range(1, 6):
            sh = step * k
            if sh >= len(x):
                break
            a[sh:] += (fb ** k) * x[:-sh]
        y += g * (buf + 0.6 * a)
    b, aa = signal.butter(2, 5200 / (SR / 2), btype="low")
    y = signal.lfilter(b, aa, y)
    b, aa = signal.butter(2, 220 / (SR / 2), btype="high")
    return signal.lfilter(b, aa, y) * 0.5


def write_wav(path, stereo):
    from scipy.io import wavfile
    wavfile.write(path, SR, (np.clip(stereo, -1, 1) * 32767).astype(np.int16))
