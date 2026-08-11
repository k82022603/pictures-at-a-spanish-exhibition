"""
현악 앙상블 (WBS 1.1.2) · 나일론 기타 (1.1.3) · 팔마스·카혼 (1.1.5)
pure numpy / scipy.
"""
import numpy as np
from scipy import signal

SR = 44100


def midi2f(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def _ns(s):
    return int(round(s * SR))


def _saw(freq_env, phase0=0.0):
    ph = phase0 + np.cumsum(freq_env) / SR
    return 2.0 * (ph - np.floor(ph + 0.5))


# ═══════════════════════════════════════════════ 현악 앙상블 (WBS 1.1.2)
_SCACHE = {}


def strings(midi, dur, vel=0.7, voices=8, attack=0.14, release=0.35,
            vib=True, section="full"):
    """8성부 디튠 현악 섹션. 느린 어택, 활 잡음, 보디 포먼트."""
    key = (midi, round(dur, 3), round(vel, 2), voices, round(attack, 3),
           round(release, 3), vib, section)
    if key in _SCACHE:
        return _SCACHE[key]

    n = _ns(dur + release)
    t = np.arange(n) / SR
    f0 = midi2f(midi)
    rng = np.random.default_rng(midi * 613 + voices)
    out = np.zeros(n)

    for v in range(voices):
        # 연주자마다 음정·비브라토·시작 시점이 미세하게 다르다
        cents = rng.normal(0.0, 6.5) / 1200.0
        fv = f0 * 2.0 ** cents
        if vib:
            rate = rng.uniform(4.6, 6.2)
            depth = 0.0038 * np.clip((t - 0.25) / 0.5, 0, 1)   # 지연 비브라토
            fenv = fv * (1.0 + depth * np.sin(2 * np.pi * rate * t + rng.uniform(0, 6.28)))
        else:
            fenv = np.full(n, fv)
        sig = _saw(fenv, rng.uniform(0, 1))
        # 연주자별 어택 편차
        a = _ns(attack * rng.uniform(0.75, 1.3))
        env = np.ones(n)
        env[:a] = np.linspace(0, 1, a) ** 1.7
        out += sig * env * (1.0 / voices)

    # 활 잡음 — 진폭에 비례
    nz = rng.uniform(-1, 1, n)
    bn, an = signal.butter(2, [1800 / (SR / 2), 7000 / (SR / 2)], btype="band")
    out += 0.05 * signal.lfilter(bn, an, nz)

    # 악기 보디 포먼트
    for fc, q, g in [(280, 2.0, 0.35), (620, 2.5, 0.28), (1250, 3.0, 0.18)]:
        b, a2 = signal.iirpeak(min(fc, 0.45 * SR) / (SR / 2), q)
        out += g * signal.lfilter(b, a2, out)
    out = signal.lfilter(*signal.butter(2, 9000 / (SR / 2), btype="low"), out)
    if section == "low":
        out = signal.lfilter(*signal.butter(2, 3000 / (SR / 2), btype="low"), out)

    # 전체 엔벨로프
    e = np.ones(n)
    r = _ns(release)
    e[-r:] = np.linspace(1, 0, r) ** 1.4
    out *= e * vel * 0.36

    _SCACHE[key] = out
    return out


# ═══════════════════════════════════════════ 나일론 기타 (WBS 1.1.3)
_GCACHE = {}


def nylon(midi, dur, vel=0.7, pluck=0.22, damp=0.996, ring=0.8):
    """Karplus-Strong. 나일론현은 강철현보다 감쇠가 빠르고 배음이 부드럽다."""
    key = (midi, round(dur, 3), round(vel, 2), round(pluck, 2), round(ring, 2))
    if key in _GCACHE:
        return _GCACHE[key]

    f0 = midi2f(midi)
    # 루프 필터가 1샘플 지연을 더하므로 그만큼 뺀다
    N = max(3, int(round(SR / f0)) - 1)
    n = _ns(dur + ring)
    rng = np.random.default_rng(midi * 331 + int(vel * 100))

    # 여기 신호 — 손톱이 아니라 손가락 살이라 부드럽다.
    # 차단을 기본주파수에 묶어 배음이 기본음을 이기지 않게 한다
    exc = rng.uniform(-1, 1, N)
    fc = float(np.clip(f0 * 7.0, 400.0, 4500.0))
    exc = signal.lfilter(*signal.butter(2, fc / (SR / 2), btype="low"), exc)
    # 뜯는 위치 = 콤 필터
    pp = max(1, int(N * pluck))
    exc = exc - np.concatenate([np.zeros(pp), exc[:-pp]])

    x = np.zeros(n)
    x[:N] = exc
    # 지연선 + 3탭 저역통과 되먹임 (나일론은 고배음이 빨리 죽는다)
    # 3탭 합이 1이므로 damp가 곧 루프 이득.
    # 루프는 초당 f0회 도므로, 목표 감쇠시간에서 역산해야 음역에 무관하게 일정하다
    tau = 1.2 + 3.0 * np.exp(-f0 / 200.0)      # 저음 약 4초, 고음 약 1.3초
    d = float(np.clip(damp * np.exp(-1.0 / (tau * f0)), 0.0, 0.9995))
    a = np.zeros(N + 3)
    a[0] = 1.0
    a[N] = -d * 0.25
    a[N + 1] = -d * 0.50
    a[N + 2] = -d * 0.25
    y = signal.lfilter([1.0], a, x)

    # 몸통 공명 (헬름홀츠 ~100Hz, 상판 ~200Hz)
    for fc, q, g in [(98, 9.0, 0.16), (203, 7.0, 0.11), (430, 5.5, 0.07)]:
        b, a2 = signal.iirpeak(fc / (SR / 2), q)
        y += g * signal.lfilter(b, a2, y)
    y = signal.lfilter(*signal.butter(2, 8000 / (SR / 2), btype="low"), y)

    m = np.abs(y).max()
    if m > 0:
        y = y / m
    e = np.ones(n)
    r0 = _ns(dur)
    if r0 < n:
        e[r0:] = np.exp(-np.arange(n - r0) / (SR * max(ring, 0.05) * 0.35))
    y *= e * vel * 0.55
    _GCACHE[key] = y
    return y



def flamenco(midi, dur, vel=0.7, pluck=0.14, damp=0.996, ring=0.34, nail=1.0):
    """플라멩코 기타. `nylon()` 과 **세 곳**이 다르다 — 밝기 · 손톱 · 몸통.

    **2026-08-11 검수자 판정 — "내 귀에는 가야금 뜯는 소리로 들림."**

    맞는 지적이었고 원인이 셋이었다.

    ① **여기 신호를 4.5kHz 에서 잘라** 어두웠다 → **9kHz 까지 연다.**
       플라멩코는 손가락 살이 아니라 **손톱**으로 친다.
    ② **어택에 손톱 소리가 없었다** → 3ms 짜리 광대역 「긁힘」을 더한다.
    ③ **몸통 공명이 약했다**(0.16 / 0.11 / 0.07) → **두 배로 올리고 한 모드 더.**

    **줄만 있고 몸통과 손톱이 없으면 「판에 얹힌 줄」이 된다. 가야금이 실제로
    그런 악기다** — 공명통이 얕고 뜯는 소리가 그대로 난다. 진단이 정확했다.

    `nylon()` 은 그대로 둔다 — 2악장은 클래식 주법이고 그쪽은 이 소리가 아니다.
    """
    key = ("fla", midi, round(dur, 3), round(vel, 2), round(pluck, 2), round(ring, 2))
    if key in _GCACHE:
        return _GCACHE[key]

    f0 = midi2f(midi)
    N = max(3, int(round(SR / f0)) - 1)
    n = _ns(dur + ring)
    rng = np.random.default_rng(midi * 337 + int(vel * 100) + 7)

    # ① 여기 신호 — 손톱이라 훨씬 밝다 (나일론은 f0*7 · 상한 4.5kHz)
    exc = rng.uniform(-1, 1, N)
    fc = float(np.clip(f0 * 14.0, 900.0, 9000.0))
    exc = signal.lfilter(*signal.butter(2, fc / (SR / 2), btype="low"), exc)
    pp = max(1, int(N * pluck))                 # 뜯는 위치 — 브리지 쪽
    exc = exc - np.concatenate([np.zeros(pp), exc[:-pp]])

    x = np.zeros(n)
    x[:N] = exc
    tau = 1.0 + 2.6 * np.exp(-f0 / 200.0)       # 나일론보다 조금 짧다. 타악적이다
    d = float(np.clip(damp * np.exp(-1.0 / (tau * f0)), 0.0, 0.9995))
    a = np.zeros(N + 3)
    a[0] = 1.0
    a[N] = -d * 0.25
    a[N + 1] = -d * 0.50
    a[N + 2] = -d * 0.25
    y = signal.lfilter([1.0], a, x)

    # ③ 몸통 — 헬름홀츠 · 상판 · 고차 모드. 나일론의 약 두 배
    for fc2, q2, g in [(98, 9.0, 0.30), (203, 7.0, 0.24),
                       (430, 5.5, 0.16), (620, 4.5, 0.10)]:
        b, a2 = signal.iirpeak(fc2 / (SR / 2), q2)
        y += g * signal.lfilter(b, a2, y)

    # ② 손톱 — 줄에 걸려 긁히는 3ms. **이것이 「기타다」를 만든다**
    if nail > 0:
        nl = _ns(0.006)
        cl = rng.uniform(-1, 1, nl) * np.exp(-np.arange(nl) / (SR * 0.0011))
        cl = signal.lfilter(*signal.butter(2, 2600 / (SR / 2), btype="high"), cl)
        y[:nl] += 0.42 * nail * cl

    y = signal.lfilter(*signal.butter(2, 11000 / (SR / 2), btype="low"), y)

    m = np.abs(y).max()
    if m > 0:
        y = y / m
    e = np.ones(n)
    r0 = _ns(dur)
    if r0 < n:
        e[r0:] = np.exp(-np.arange(n - r0) / (SR * max(ring, 0.05) * 0.35))
    y *= e * vel * 0.55
    _GCACHE[key] = y
    return y


def golpe(vel=0.8):
    """골페 — 기타 **상판을 손가락으로 두드린다.** 플라멩코 특유의 타격.

    카혼과 다르다. 카혼은 상자를 치는 저역 붐이고, 골페는 **기타 몸통**이
    울리는 소리다 — 그래서 이 소리가 있으면 **「저기 기타가 있다」가 확실해진다.**
    """
    n = _ns(0.16)
    rng = np.random.default_rng(90911)
    x = rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / (SR * 0.012))
    y = np.zeros(n)
    for fc, q2, g in [(92, 7.0, 1.00), (190, 6.0, 0.55), (410, 4.0, 0.22)]:
        b, a = signal.iirpeak(fc / (SR / 2), q2)
        y += g * signal.lfilter(b, a, x)
    cl = rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / (SR * 0.0018))
    y += 0.35 * signal.lfilter(*signal.butter(2, 2200 / (SR / 2), btype="high"), cl)
    m = np.abs(y).max()
    return (y / m * vel * 0.50) if m > 0 else y


# ═══════════════════════════════════════ 팔마스 · 카혼 (WBS 1.1.5)
def palma(vel=0.8, kind="clara"):
    """플라멩코 박수. clara = 손바닥 마주쳐 날카롭게, sorda = 오므려 둔탁하게."""
    n = _ns(0.13)
    rng = np.random.default_rng(int(vel * 977) + (0 if kind == "clara" else 7))
    nz = rng.uniform(-1, 1, n)
    if kind == "clara":
        b, a = signal.butter(2, [1100 / (SR / 2), 8000 / (SR / 2)], btype="band")
        tau = 0.010
    else:
        b, a = signal.butter(2, [320 / (SR / 2), 2200 / (SR / 2)], btype="band")
        tau = 0.020
    y = signal.lfilter(b, a, nz) * np.exp(-np.arange(n) / (SR * tau))
    # 손바닥 사이 공기 = 짧은 슬랩
    d = _ns(0.0035)
    y[d:] += 0.35 * y[:-d]
    return y * vel * 0.7


def cajon(vel=0.8, kind="bass"):
    """카혼. bass = 판 중앙 저음, slap = 모서리 고음."""
    n = _ns(0.32)
    t = np.arange(n) / SR
    rng = np.random.default_rng(int(vel * 313) + (0 if kind == "bass" else 5))
    if kind == "bass":
        f = np.concatenate([np.geomspace(150, 82, _ns(0.03)),
                            np.full(n - _ns(0.03), 82.0)])
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.075)
        nz = rng.uniform(-1, 1, n) * np.exp(-t / 0.006) * 0.25
        y = y + nz
    else:
        nz = rng.uniform(-1, 1, n)
        b, a = signal.butter(2, [1600 / (SR / 2), 9500 / (SR / 2)], btype="band")
        y = signal.lfilter(b, a, nz) * np.exp(-t / 0.028)
        y += 0.3 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.020)
    return np.tanh(y * 1.4) * vel * 0.8


def tacon(vel=0.8):
    """무희의 발 굽 — 짧고 단단한 타격."""
    n = _ns(0.18)
    t = np.arange(n) / SR
    rng = np.random.default_rng(int(vel * 555))
    nz = rng.uniform(-1, 1, n)
    b, a = signal.butter(2, [200 / (SR / 2), 5200 / (SR / 2)], btype="band")
    y = signal.lfilter(b, a, nz) * np.exp(-t / 0.014)
    y += 0.5 * np.sin(2 * np.pi * 110 * t) * np.exp(-t / 0.035)
    return np.tanh(y * 1.6) * vel * 0.75


# ═════════════════════════════════ 리켄배커 베이스 (Jon Camp 톤)
_RCACHE = {}


def rick(midi, dur, vel=0.75, pick=0.13, ring=0.6, growl=1.0):
    """Rickenbacker 4001 계열. Karplus-Strong 강철현 + 픽 어택 +
    브릿지 픽업의 미드 그로울. 신스 베이스가 아니라 진짜 현 모델."""
    key = (midi, round(dur, 3), round(vel, 2), round(pick, 2),
           round(ring, 2), round(growl, 2))
    if key in _RCACHE:
        return _RCACHE[key]

    f0 = midi2f(midi)
    N = max(4, int(round(SR / f0)) - 1)
    n = _ns(dur + ring)
    rng = np.random.default_rng(midi * 719 + int(vel * 137))

    # 픽으로 뜯는다 — 손가락보다 훨씬 밝다
    exc = rng.uniform(-1, 1, N)
    exc = signal.lfilter(*signal.butter(2, min(6500, 0.45 * SR) / (SR / 2),
                                        btype="low"), exc)
    exc = signal.lfilter(*signal.butter(1, 90 / (SR / 2), btype="high"), exc)
    pp = max(1, int(N * pick))          # 브릿지 쪽 = 밝음
    exc = exc - np.concatenate([np.zeros(pp), exc[:-pp]])

    x = np.zeros(n)
    x[:N] = exc
    # 강철현은 나일론보다 오래 울린다
    tau = 2.2 + 2.6 * np.exp(-f0 / 90.0)
    d = float(np.clip(0.999 * np.exp(-1.0 / (tau * f0)), 0, 0.9997))
    a = np.zeros(N + 3)
    a[0] = 1.0
    a[N] = -d * 0.30
    a[N + 1] = -d * 0.44
    a[N + 2] = -d * 0.26
    y = signal.lfilter([1.0], a, x)

    # 픽업·프리앰프 성격
    b1, a1 = signal.iirpeak(1150 / (SR / 2), 1.1)
    y = y + 0.85 * growl * signal.lfilter(b1, a1, y)          # 미드 그로울
    b2, a2 = signal.iirpeak(330 / (SR / 2), 1.3)
    y = y - 0.28 * signal.lfilter(b2, a2, y)                  # 로우미드 스쿱
    b3, a3 = signal.iirpeak(2900 / (SR / 2), 1.6)
    y = y + 0.30 * signal.lfilter(b3, a3, y)                  # 픽 프레즌스
    y = signal.lfilter(*signal.butter(2, 5500 / (SR / 2), btype="low"), y)
    y = signal.lfilter(*signal.butter(2, 45 / (SR / 2), btype="high"), y)

    # 픽 어택 클릭
    nc = _ns(0.004)
    y[:nc] += 0.22 * vel * rng.uniform(-1, 1, nc) * np.exp(
        -np.arange(nc) / (SR * 0.0009))

    m = np.abs(y).max()
    if m > 0:
        y = y / m
    e = np.ones(n)
    r0 = _ns(dur)
    if r0 < n:
        e[r0:] = np.exp(-np.arange(n - r0) / (SR * max(ring, 0.05) * 0.30))
    y = np.tanh(y * (1.1 + 0.5 * vel)) * vel * 0.62
    y *= e
    _RCACHE[key] = y
    return y


def humanize(rng, t, vel, tj=0.010, vj=0.13):
    """연주자는 격자 위에 정확히 놓지 않는다. 타이밍과 세기를 흔든다."""
    return t + rng.normal(0, tj), float(np.clip(vel * (1 + rng.normal(0, vj)), 0.05, 1.0))
