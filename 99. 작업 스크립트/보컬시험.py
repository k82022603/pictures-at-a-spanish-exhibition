# -*- coding: utf-8 -*-
"""BL-28 예비 시험 — **가사가 들리는 목소리를 지금 만들 수 있는가.**

2026-08-14. 검수자 질문 —
  *"부족하다 싶은 부분은 싱어 보이스로 채워야 할 것 같음. ELP 전람회의
   그림 노래가 그렇게 되어 있음. 문제는, 지금 상태에서 가사가 있는
   보이스 시뮬레이션 가능한지 모르겠어."*

**답: 된다. 다만 「노래」가 아니라 「말을 노래 높이로 구부린 것」이다.**

이 PC 에 윈도우가 기본으로 갖고 있는 영어 읽어주는 목소리가 하나 있다
(Microsoft Zira). **노래하는 목소리가 아니라 읽어주는 목소리**다. 그래서
이렇게 한다.

  ① 음절을 **하나씩 따로** 말하게 시켜 소리를 받는다
  ② 그 소리의 높이를 재서 **선율의 음 높이로 옮긴다**
  ③ 길이를 **그 음의 박자에 맞춘다**
  ④ 어택을 무르게 하고, 긴 음은 뒤로 갈수록 차오르게 하고, 살짝 늦게
     들어오게 하고, 넓은 울림을 준다 (`07` 11장 「목소리 처리」)

**이것으로 판정할 것은 음색이 아니라 「말이 들리니 장면이 이해되는가」다.**
소리는 로봇에 가깝다. 그걸로 음색을 판정하면 안 된다 — 음색 판정은 노래
전용 도구나 사람 목소리로 해야 하고, 그것이 BL-28 본체다.

**승인된 음원은 건드리지 않는다.** 9악장 구간을 따로 떠서 그 위에 얹은
별도 파일을 만든다.

    python 보컬시험.py            # → 보컬시험 9악장.wav
"""
import io
import os
import subprocess
import sys

import numpy as np
from scipy.signal import resample_poly

import 화성
import synth

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "보컬음절")          # 말한 음절을 모아둔다
MASTER = os.path.join(HERE, "전곡화성.wav")     # 승인판 (읽기만 한다)
VOICE = "Microsoft Zira Desktop"

# ══════════════════════ 노랫말과 선율 ══════════════════════════════════
#
# **9악장 네 자리는 이미 승인돼 있다** (`05` 9.31.3절). 선율은 주제 A 이고
# 지금은 피아노가 한 옥타브 위에서 친다. **목소리는 원래 음역(F4~F5)으로
# 부른다** — 옥타브를 내리지도 올리지도 않는다(`CLAUDE.md` 6절).
#
# 리듬 `1 1 1 ½ ½ 1 ½ ½ 1 1 1` 에서 **넷째·다섯째와 일곱째·여덟째가
# 8분음표로 붙으므로** 그 자리에 짧은 약음절이 온다. 아래 음절 쪼갬이
# 그것과 맞는지 확인한 상태다.
TH_A = [(67, 1.0), (65, 1.0), (70, 1.0), (72, .5), (77, .5), (74, 1.0),
        (72, .5), (77, .5), (74, 1.0), (70, 1.0), (72, 1.0)]

BT9 = 60.0 / 63.0                               # 9악장 ♩=63

LINES = [
    (527.0, "4행", ["I", "count", "out", "ev", "ry", "step",
                    "un", "der", "my", "own", "feet"]),
    (538.0, "6행", ["Now", "we", "walk", "two", "of", "us",
                    "ne", "ver", "in", "one", "step"]),
    (549.0, "7행", ["Now", "the", "light", "in", "the", "old",
                    "pic", "ture", "holds", "you", "too"]),
    (556.0, "8행", ["Look", "ing", "back", "you", "were", "here",
                    "al", "ways", "in", "my", "step"]),
]


# ══════════════════════ ① 음절을 말하게 시킨다 ═════════════════════════
def say(word):
    """윈도우 음성으로 낱말 하나를 말해 파일로 받는다. 한 번 받으면 재사용."""
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "%s.wav" % word)
    if not os.path.exists(p):
        ps = ('Add-Type -AssemblyName System.Speech; '
              '$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
              '$s.SelectVoice("%s"); $s.Rate = -3; '
              '$s.SetOutputToWaveFile("%s"); $s.Speak("%s"); $s.Dispose()'
              % (VOICE, p.replace("\\", "\\\\"), word))
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       check=True, capture_output=True)
    sr, x = 화성.read_wav(p)          # 자료형을 보고 나눈다 (검증.py 7번)
    if x.ndim > 1:
        x = x.mean(1)
    x = x / max(1e-9, np.abs(x).max())
    if sr != SR:                                # 44.1 kHz 로 맞춘다
        g = np.gcd(int(sr), SR)
        x = resample_poly(x, SR // g, int(sr) // g)
    return trim(x)


def trim(x, thr=0.02):
    """앞뒤 무음을 자른다. 말하기 파일은 앞뒤가 길게 비어 있다."""
    e = np.abs(x)
    w = int(0.005 * SR)
    e = np.convolve(e, np.ones(w) / w, "same")
    on = np.where(e > thr * e.max())[0]
    return x[on[0]:on[-1] + 1] if len(on) else x


# ══════════════════════ ② 높이를 잰다 ══════════════════════════════════
def f0(x, lo_hz=80.0, hi_hz=400.0):
    """소리의 높이(Hz).

    **첫 판이 한 옥타브씩 틀렸다.** 자기상관에서 가장 높은 봉우리를 그냥
    집으면 **실제 주기의 절반**을 집는 일이 흔하다(배음이 강할 때). 그러면
    「원래 높이」를 두 배로 재고, 그만큼 덜 올려서 **한 옥타브 낮게 부른다.**
    실제로 열한 음 중 아홉이 −1200 센트로 나왔다.

    **고친 방법 — 봉우리가 여럿이면 그중 가장 긴 주기(=가장 낮은 음)를
    고른다.** 사람 목소리에서 진짜 주기는 언제나 후보들 중 가장 길다.
    """
    seg = x[len(x) // 4: len(x) // 4 + int(0.09 * SR)]
    if len(seg) < 1000:
        seg = x
    seg = seg - seg.mean()
    r = np.correlate(seg, seg, "full")[len(seg) - 1:]
    if r[0] > 0:
        r = r / r[0]
    lo, hi = int(SR / hi_hz), int(SR / lo_hz)
    hi = min(hi, len(r) - 1)
    if hi <= lo + 2:
        return 200.0
    band = r[lo:hi]
    peak = float(band.max())
    if peak <= 0:
        return 200.0
    # 최고봉의 85% 를 넘는 봉우리들 중 **가장 오른쪽(주기가 가장 긴 것)**
    cand = np.where(band > 0.85 * peak)[0]
    grp = [cand[0]]
    for i in cand[1:]:
        if i - grp[-1] > 2:
            grp.append(i)
    k = lo + int(grp[-1])
    return SR / k


def f0_src(x):
    """**말한 음절의 원래 높이.** 창을 여러 개 재서 가운뎃값을 쓴다.

    한 자리만 재면 `s`·`f` 같은 바람소리에 걸린다 — `step` 이 397 Hz,
    `feet` 이 89 Hz 로 나왔고 둘 다 목소리가 아니라 잡음을 잰 것이다.

    **이 목소리(Zira)는 145~170 Hz 로 말한다.** 그 언저리만 본다.
    """
    w = int(0.09 * SR)
    if len(x) < w:
        return f0(x, 120.0, 260.0)
    got = []
    for i in range(0, len(x) - w, w // 2):
        seg = x[i:i + w]
        if np.sqrt(np.mean(seg ** 2)) < 0.05 * np.sqrt(np.mean(x ** 2)):
            continue                            # 너무 조용한 창은 건너뛴다
        got.append(f0(seg, 120.0, 260.0))
    return float(np.median(got)) if got else 165.0


def midi_hz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


# ══════════════════════ ③ 높이와 길이를 맞춘다 ═════════════════════════
def shift(x, ratio):
    """높이를 ratio 배로. 빨리 감기와 같은 원리라 길이도 함께 바뀐다."""
    ratio = float(np.clip(ratio, 0.25, 4.0))
    n = max(1, int(len(x) / ratio))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def stretch(x, n):
    """길이만 n 샘플로. 조각을 겹쳐 이어 붙인다 — 높이는 안 바뀐다."""
    if len(x) < 512:
        return np.pad(x, (0, max(0, n - len(x))))[:n]
    fr = 1024
    hop_o = fr // 4
    hop_n = max(1, int(hop_o * n / len(x)))
    win = np.hanning(fr)
    out = np.zeros(n + fr)
    acc = np.zeros(n + fr)
    i = j = 0
    while i + fr < len(x) and j + fr < n:
        out[j:j + fr] += x[i:i + fr] * win
        acc[j:j + fr] += win
        i += hop_o
        j += hop_n
    acc[acc < 1e-6] = 1.0
    return (out / acc)[:n]


# ══════════════════════ ③′ 높이를 「새로 만들어 넣는다」 ═══════════════
#
# **옮기는 방식이 안 됐다.** 말소리는 한 음절 안에서도 높낮이가 미끄러지고
# (영어는 특히 끝을 내린다), `s`·`f` 같은 바람소리에는 아예 높이가 없다.
# 그래서 「재서 옮기고 다시 재서 고치기」를 세 번 돌려도 **44음 중 16음**만
# 맞았다. 남은 것들도 최대 두 반음이 어긋나 **가락이 비틀렸다.**
#
# **말소리는 두 겹이다** — ① 성대가 만드는 **높이** ② 입·혀가 만드는
# **울림의 모양**. 낱말을 알아듣게 하는 것은 ②이고, 노래의 음정은 ①이다.
#
# **그러므로 ②만 남기고 ①을 버린 뒤, 원하는 높이를 새로 넣는다.**
# 목소리의 「입 모양」은 그대로라 낱말은 그대로 들리고, 높이는 계산으로
# 넣으므로 **어긋날 수가 없다.**
#
# 바람소리 구간(`s`·`t`·`f`)은 **원래 소리를 그대로 쓴다** — 거기에 높이를
# 넣으면 삐 소리가 난다.
FR, HOP = 1024, 256


def envelope(frame):
    """한 조각의 「입 모양」만 뽑는다 (높이 정보는 버린다)."""
    S = np.fft.rfft(frame)
    logm = np.log(np.abs(S) + 1e-9)
    cep = np.fft.irfft(logm)
    cep[36:-36] = 0.0                           # 성대의 잔결을 지운다
    return np.exp(np.fft.rfft(cep).real)


def voiced(frame):
    """이 조각이 목소리인가(True) 바람소리인가(False)."""
    s = frame - frame.mean()
    if np.sqrt(np.mean(s ** 2)) < 1e-5:
        return False
    r = np.correlate(s, s, "full")[len(s) - 1:]
    if r[0] <= 0:
        return False
    lo, hi = int(SR / 400), min(int(SR / 80), len(r) - 1)
    return hi > lo and (r[lo:hi].max() / r[0]) > 0.28


def resynth(x, hz, vib=0.5):
    """말소리의 울림은 두고 **높이만 새로 만들어 넣는다.**

    `vib` 는 비브라토 — 사람은 긴 음을 완전히 곧게 못 낸다. 아주 조금만
    흔들어야 기계 같지 않고, 많으면 취한 것 같다.
    """
    n = len(x)
    t = np.arange(n) / SR
    f = hz * (1.0 + 0.006 * vib * np.sin(2 * np.pi * 5.2 * t) *
              np.clip((t - 0.25) / 0.4, 0, 1))   # 0.25초 뒤부터 서서히
    ph = np.cumsum(f) / SR
    exc = np.zeros(n)
    idx = np.searchsorted(ph, np.arange(1, ph[-1] if n else 1))
    exc[idx[idx < n]] = 1.0                      # 성대 펄스 — 초당 hz 번
    win = np.hanning(FR)
    out = np.zeros(n + FR)
    acc = np.zeros(n + FR)
    for i in range(0, max(1, n - FR), HOP):
        fr = x[i:i + FR] * win
        if voiced(fr):
            E = np.fft.rfft(exc[i:i + FR] * win)
            m = np.abs(E).max()
            y = np.fft.irfft(envelope(fr) * (E / m if m > 0 else E), FR)
        else:
            y = fr                               # 바람소리는 그대로 둔다
        out[i:i + FR] += y * win
        acc[i:i + FR] += win ** 2
    acc[acc < 1e-6] = 1.0
    y = (out / acc)[:n]
    m = np.abs(y).max()
    return y / m * np.abs(x).max() if m > 0 else y


def tune(x, target):
    """**올려놓고 다시 재서 고친다.** 한 번에 맞히려 하지 않는다.

    말소리는 음절마다 높이가 다르고(이 목소리는 145~170 Hz), `s`·`f` 같은
    바람소리가 섞이면 재는 것 자체가 틀린다. **한 번 재서 한 번 올리는
    방식으로는 44음 중 7음밖에 안 맞았다.**

    그래서 올린 뒤에 **목표 음 언저리(±4반음)만 다시 재서** 어긋난 만큼
    다시 옮긴다. 좁은 범위만 보므로 옥타브를 잘못 집을 수가 없다.
    """
    for _ in range(3):
        got = f0(x, target * 0.79, target * 1.26)
        if got <= 0:
            break
        cents = 1200.0 * np.log2(got / target)
        if abs(cents) < 12:                     # 12센트 = 사람이 못 듣는 차이
            break
        x = shift(x, target / got)
    return x


def sing(word, midi, dur, grow=0.0):
    """말 한 음절을 정해진 높이와 길이의 노래 한 음으로."""
    x = say(word)
    n = int(dur * SR)
    # **길이를 먼저 맞춘다** — 늘이고 줄이는 것은 입 모양을 안 바꾼다
    x = stretch(x, n)
    # **그 다음 높이를 새로 넣는다.** 계산으로 넣으므로 정확히 그 음이다
    x = resynth(x, midi_hz(midi), vib=1.0 if dur > 0.7 else 0.0)
    t = np.arange(n) / SR
    # 어택을 무르게 — 25 ms 동안 열린다. 말소리의 딱딱한 시작을 뭉갠다
    a = np.clip(t / 0.025, 0, 1) ** 1.5
    # 끝을 닫는다. 음절끼리 부딪히지 않게
    d = np.clip((dur - t) / 0.04, 0, 1)
    # 긴 음은 뒤로 갈수록 차오른다 (`07` 11장 「지속음 크레셴도」)
    c = 1.0 + grow * np.clip(t / dur, 0, 1)
    return x * a * d * c


# ══════════════════════ ④ 한 행을 부른다 ═══════════════════════════════
def line(syls, third=False):
    """열한 음절을 주제 A 에 얹는다. third=True 면 3도 위를 겹쳐 부른다."""
    total = sum(b for _, b in TH_A) * BT9
    buf = np.zeros(int((total + 1.5) * SR))
    for (m, b), w in zip(TH_A, syls):
        pass
    t = 0.0
    for (m, b), w in zip(TH_A, syls):
        dur = b * BT9
        # 긴 음(4분음표 이상)만 차오르게. 스쳐가는 8분음표는 그냥 둔다
        v = sing(w, m, dur * 0.96, grow=0.35 if b >= 1.0 else 0.0)
        i = int(t * SR)
        buf[i:i + len(v)] += v * (0.9 if b >= 1.0 else 0.7)
        if third:
            # **3도 위가 곧 주제 B 다** (`05` 9.31.4절). 여행자가 자기
            # 목소리를 겹쳐 부르는데 그것이 그녀의 선율이 된다
            v2 = sing(w, m + 3, dur * 0.96, grow=0.35 if b >= 1.0 else 0.0)
            buf[i:i + len(v2)] += v2 * 0.5
        t += dur
    return buf


def main():
    print("BL-28 예비 시험 — 가사가 들리는 목소리")
    print("**노래 목소리가 아니라 읽어주는 목소리를 구부린 것이다.**\n")

    sr, mst = 화성.read_wav(MASTER)
    if mst.ndim == 1:
        mst = np.stack([mst, mst], 1)
    out = mst.copy()

    for t0, name, syls in LINES:
        v = line(syls, third=(name == "8행"))
        # **살짝 늦게 들어온다** — 사람은 정확히 박에 안 붙는다 (레이드백)
        i = int((t0 + 0.045) * SR)
        # 넓은 울림. 무그(그녀)와 같은 공기를 갖게 한다 (`CLAUDE.md` 6절)
        wet = 화성.plate(v, seed=20260814)
        mix = v + 0.34 * wet[:len(v)]
        mix *= 0.62 / max(1e-9, np.abs(mix).max())
        # 왼쪽 살짝 — 그녀(무그)가 오른쪽이므로 여행자는 반대쪽
        out[i:i + len(mix), 0] += mix * 0.92
        out[i:i + len(mix), 1] += mix * 0.72
        print("  %s  %s  %5.1f초  %d음절  %s" %
              (name, "★두 목소리" if name == "8행" else "        ",
               t0, len(syls), " ".join(syls)))

    seg = out[int(525 * SR):int(580 * SR)]
    seg = seg / max(1.0, np.abs(seg).max() / 0.98)
    synth.write_wav(os.path.join(HERE, "보컬시험 9악장.wav"), seg, bits=24)
    print("\n→ 보컬시험 9악장.wav  (8:45~9:40 · 55초)")
    print("**승인판은 안 건드렸다.** 읽어서 위에 얹기만 했다.")


if __name__ == "__main__":
    main()
