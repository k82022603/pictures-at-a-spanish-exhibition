"""
Piano synthesiser — WBS 1.1.1
Additive synthesis with string inharmonicity, per-partial decay,
hammer noise and soundboard colouring. Pure numpy/scipy.
"""
import numpy as np
from scipy import signal

SR = 44100


def midi2f(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def _ns(sec):
    return int(round(sec * SR))


_CACHE = {}


def note(midi, dur, vel=0.75, ring=1.0):
    """One piano note. `dur` = key held; `ring` = extra tail after release
    (sustain pedal). Cached on the rounded parameter tuple."""
    key = (midi, round(dur, 3), round(vel, 2), round(ring, 2))
    if key in _CACHE:
        return _CACHE[key]

    f0 = midi2f(midi)
    total = _ns(dur + ring)
    t = np.arange(total) / SR

    # --- string inharmonicity: bass strings are stiffer, so B is larger
    B = 4.0e-5 * (1.0 + 600.0 / max(f0, 25.0))

    # --- decay: bass rings for many seconds, treble dies fast
    tau0 = 0.55 + 13.0 * np.exp(-f0 / 300.0)

    # --- brightness follows velocity (harder strike = more upper partials)
    bright = 8.0 + 24.0 * vel

    npart = int(min(40, max(4, 0.44 * SR / f0)))
    out = np.zeros(total)
    rng = np.random.default_rng(midi * 977 + int(vel * 100))

    for k in range(1, npart + 1):
        fk = f0 * k * np.sqrt(1.0 + B * k * k)
        if fk > 0.46 * SR:
            break
        amp = (k ** -1.05) * np.exp(-k / bright)
        # slight detune between the 2-3 strings of a unison
        det = 1.0 + rng.normal(0.0, 0.00035)
        tau = tau0 / (1.0 + 0.42 * (k - 1) ** 0.9)
        env = np.exp(-t / tau)
        # secondary faster component -> the characteristic double decay
        env = 0.72 * env + 0.28 * np.exp(-t / (tau * 0.16))
        out += amp * env * np.sin(2 * np.pi * fk * det * t + rng.uniform(0, 6.28))

    out /= npart ** 0.40

    # --- hammer: broadband thump, low-passed around the note's register
    nh = _ns(0.012)
    nz = rng.uniform(-1, 1, nh)
    b, a = signal.butter(2, min(0.45 * SR, f0 * 9) / (SR / 2), btype="low")
    out[:nh] += 0.10 * vel * signal.lfilter(b, a, nz) * np.exp(-np.arange(nh) / (SR * 0.0022))

    # --- attack smoothing (a piano is not an instantaneous onset)
    na = _ns(0.0035)
    out[:na] *= np.linspace(0, 1, na) ** 0.6

    # --- damper: without pedal the tone is cut when the key is released
    if ring < 0.12:
        r0, r1 = _ns(dur), _ns(dur) + _ns(0.09)
        r1 = min(r1, total)
        if r1 > r0:
            out[r0:r1] *= np.linspace(1, 0, r1 - r0)
        out[r1:] = 0.0

    out *= vel * (0.55 + 0.45 * np.exp(-f0 / 900.0))
    _CACHE[key] = out
    return out


def _soundboard(x):
    """Body colouring: cut deep rumble, gentle presence lift, air roll-off."""
    x = signal.lfilter(*signal.butter(2, 32 / (SR / 2), btype="high"), x)
    pk = signal.iirpeak(2400 / (SR / 2), 1.1)
    x = x + 0.30 * signal.lfilter(pk[0], pk[1], x)
    x = signal.lfilter(*signal.butter(2, 15000 / (SR / 2), btype="low"), x)
    return x


def _room(x, seed=0, amount=0.20):
    rng = np.random.default_rng(90210 + seed)
    y = np.zeros(len(x))
    for dl, g in [(0.0193, .50), (0.0291, .42), (0.0411, .34),
                  (0.0623, .27), (0.0891, .21), (0.1277, .15), (0.1811, .10)]:
        d = _ns(dl * (1 + 0.02 * rng.standard_normal()))
        if d >= len(x):
            continue
        acc = np.zeros(len(x))
        for k in range(1, 7):
            s = d * k
            if s >= len(x):
                break
            acc[s:] += (0.60 ** k) * x[:-s]
        y += g * acc
    y = signal.lfilter(*signal.butter(2, 4200 / (SR / 2), btype="low"), y)
    y = signal.lfilter(*signal.butter(2, 160 / (SR / 2), btype="high"), y)
    return amount * y * 0.5


class Score:
    """Places notes on a stereo timeline. Pan follows pitch, as heard
    from the player's seat."""

    def __init__(self, seconds):
        n = _ns(seconds) + SR * 8
        self.L = np.zeros(n)
        self.R = np.zeros(n)

    def add(self, midi, at, dur, vel=0.75, ring=1.0):
        sig = note(midi, dur, vel, ring)
        i = _ns(at)
        j = i + len(sig)
        if j > len(self.L):
            pad = j - len(self.L) + 1
            self.L = np.pad(self.L, (0, pad))
            self.R = np.pad(self.R, (0, pad))
        pan = np.clip((midi - 60) / 42.0, -1, 1) * 0.42
        gl = np.cos((pan + 1) * np.pi / 4) * 1.414
        gr = np.sin((pan + 1) * np.pi / 4) * 1.414
        self.L[i:j] += sig * gl
        self.R[i:j] += sig * gr

    def chord(self, midis, at, dur, vel=0.75, ring=1.0, roll=0.0):
        for n, m in enumerate(sorted(midis)):
            self.add(m, at + n * roll, dur, vel * (1.0 - 0.03 * n), ring)

    def render(self, trim=None, peak=0.90):
        L, R = self.L, self.R
        if trim:
            k = _ns(trim)
            L, R = L[:k], R[:k]
        L, R = _soundboard(L), _soundboard(R)
        L = L + _room(L, 0)
        R = R + _room(R, 1)
        # gentle bus compression for glue
        det = np.maximum(np.abs(L), np.abs(R))
        blk = 128
        pk = np.array([det[i:i + blk].max() for i in range(0, len(det), blk)])
        e, out = 0.0, np.zeros(len(pk))
        ac, rc = np.exp(-1 / (0.008 * SR / blk)), np.exp(-1 / (0.25 * SR / blk))
        for i, p in enumerate(pk):
            c = ac if p > e else rc
            e = c * e + (1 - c) * p
            out[i] = e
        env = np.interp(np.arange(len(det)), np.arange(len(out)) * blk, out)
        g = np.maximum(env / 0.42, 1.0) ** (1 / 2.6 - 1)
        L, R = L * g, R * g
        m = max(np.abs(L).max(), np.abs(R).max(), 1e-9)
        return np.stack([L / m * peak, R / m * peak], axis=1)


def write_wav(path, stereo, bits=32):
    """마스터를 쓴다.

    **기본이 32비트 float 다** (2026-08-12, 검수자 "24bit 올릴 방법은? 더 높여도 좋고").

    믹스는 내부적으로 float32 이므로 **float 로 쓰면 양자화가 아예 없다** —
    24비트 정수보다도 정확하다. 스템은 `Desk.save_stems` 가 이미 float32 로
    쓰고 있었고, **최종 마스터만 16비트로 떨어뜨리고 있었다.**

    옛 경로에 결함이 하나 더 있었다 — `(x * 32767).astype(np.int16)` 은
    **반올림이 아니라 0 쪽으로 자른다.** 잘라낸 오차는 신호와 상관을 갖기
    때문에 같은 크기의 무작위 잡음보다 나쁘다. float 로 가면 사라진다.

    bits=16 은 옛 동작을 남긴 것이다(반올림으로 고쳤다). 지우지 않는다.
    """
    from scipy.io import wavfile
    x = np.clip(stereo, -1.0, 1.0)
    if bits == 16:
        wavfile.write(path, SR, np.rint(x * 32767.0).astype(np.int16))
    elif bits == 24:
        # scipy 는 24비트를 못 쓴다. 32비트 정수로 쓰되 하위 8비트를 비운다
        wavfile.write(path, SR, (np.rint(x * 8388607.0).astype(np.int32) << 8))
    else:
        wavfile.write(path, SR, x.astype(np.float32))
