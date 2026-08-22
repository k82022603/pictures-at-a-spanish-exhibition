# -*- coding: utf-8 -*-
"""**악장 경계를 찾는 자 — 셋째 판.** 음악 구조 분석의 정석대로 짓는다.

2026-08-22. 앞의 둘이 왜 실패했는지부터 적는다.

| 판 | 무엇을 봤나 | 왜 실패했나 |
|---|---|---|
| `악장찾기.py` | 크로마만 | **7↔8 은 둘 다 D 중심**이라 화성이 안 갈린다 |
| `구조분석.py` | 크로마+대역+타격, SSM | 자검사 8/9 였으나 **Suno 판에서 귀와 어긋났다** |
| 좁은 범위 훑기 | 순간 변화량 | **범위를 빼면 3/9.** 「어디쯤인지 알 때만」 맞는 자 |

**공통된 잘못은 「순간의 변화」만 본 것이다.**
악장은 **안이 서로 닮은 덩어리**이고, 경계는 **그 덩어리의 가장자리**다.
한 순간이 아니라 **앞 L초 덩어리와 뒤 L초 덩어리를 통째로 견줘야** 한다.

## 셋째 판이 더하는 것

1. **음색(MFCC)을 본다.** 화성이 같아도 **편성이 바뀌면** 음색이 움직인다.
   7악장(피아노 아르페지오+플루트) → 8악장(오르간·무그 솔로 교대)이 그런 자리다.
2. **시간 지연 임베딩.** 한 프레임이 아니라 앞뒤를 묶어 본다 — 순간 잡음에 안 흔들린다.
3. **세 갈래를 따로 재고 합친다** — 화성 · 음색 · 리듬. 셋 중 하나만 움직여도 잡힌다.
4. **경로 강화.** SSM 을 대각선 방향으로 다듬어 반복 구조를 살린다.

## 자검사

**우리 곡의 알려진 경계 아홉을 ±3초 안에 몇 개 맞추는가.**
**범위를 주지 않는다** — 전곡을 훑어 상위 아홉을 뽑는다. 그래야 Suno 판에 쓸 수 있다.
"""
import os
import sys

import numpy as np
from scipy import signal as sg
from scipy.fftpack import dct
from scipy.ndimage import median_filter, uniform_filter1d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 화성

sys.stdout.reconfigure(encoding="utf-8")

홉 = 0.25                 # 특징 간격(초) — 촘촘하게
창 = 0.50
지연 = 4                  # 시간 지연 임베딩: 앞뒤 4칸(=1초)을 묶는다
LS = [4.0, 8.0, 16.0, 32.0]   # 커널 반쪽(초)
# **4.0 이 있어야 한다.** 이 곡의 변주 악장 둘(2·5)이 **15초**다.
# 반쪽이 8초면 앞뒤로 16초를 보므로 **악장을 통째로 넘어간다.**
# 곡을 보면 아는 사실이지 성능을 보고 돌린 값이 아니다.


def 읽기(p):
    """**`화성.read_wav` 가 자료형을 본다.** 직접 `/ 32768` 하지 않는다 — 마스터가
    float32 로 바뀐 날 도구 여섯이 전부 −110 dB 를 찍은 적이 있다(`검증.py` 7번).

    이 파일은 **한 채널로 합친 것**을 쓴다."""
    sr, x = 화성.read_wav(p)
    return sr, x.mean(axis=1) if x.ndim > 1 else x


def _멜뱅크(SR, nfft, n=26, fmin=40, fmax=12000):
    def h2m(f): return 2595 * np.log10(1 + f / 700.0)
    def m2h(m): return 700 * (10 ** (m / 2595.0) - 1)
    pts = m2h(np.linspace(h2m(fmin), h2m(fmax), n + 2))
    bins = np.floor((nfft + 1) * pts / SR).astype(int)
    fb = np.zeros((n, nfft // 2 + 1))
    for i in range(n):
        a, b, c = bins[i], bins[i + 1], bins[i + 2]
        if b == a: b = a + 1
        if c == b: c = b + 1
        fb[i, a:b] = (np.arange(a, b) - a) / (b - a)
        fb[i, b:c] = (c - np.arange(b, c)) / (c - b)
    return fb


def 특징(m, SR):
    """세 갈래를 따로 낸다 — 화성(12) · 음색(13) · 리듬(4)."""
    nfft = 1 << 12
    h = int(홉 * SR)
    w = int(창 * SR)
    n = (len(m) - w) // h + 1
    fb = _멜뱅크(SR, nfft)
    freqs = np.fft.rfftfreq(nfft, 1 / SR)
    ok = (freqs > 55) & (freqs < 4200)
    pc = np.zeros(len(freqs), dtype=int)
    pc[ok] = np.rint(12 * np.log2(freqs[ok] / 440.0) + 69).astype(int) % 12
    win = np.hanning(w)

    def 봉투(lo, hi):
        sos = sg.butter(4, [lo, hi], "band", fs=SR, output="sos")
        return np.abs(sg.sosfiltfilt(sos, m))
    e_lo, e_mi, e_hi = 봉투(40, 160), 봉투(300, 2500), 봉투(5000, 12000)

    H = np.zeros((n, 12))     # 화성
    T = np.zeros((n, 13))     # 음색
    R = np.zeros((n, 4))      # 리듬
    for i in range(n):
        s = m[i * h:i * h + w]
        if len(s) < w:
            s = np.pad(s, (0, w - len(s)))
        S = np.abs(np.fft.rfft(s * win, nfft)) ** 2
        # 화성 — 크로마, L1 정규화
        c = np.zeros(12)
        for k in range(12):
            c[k] = S[ok & (pc == k)].sum()
        H[i] = c / (c.sum() + 1e-20)
        # 음색 — MFCC
        mel = np.log(fb @ S + 1e-12)
        T[i] = dct(mel, type=2, norm="ortho")[:13]
        # 리듬 — 세 대역 봉투의 세기와 들쭉날쭉함
        a, b = i * h, i * h + w
        R[i] = [e_lo[a:b].mean(), e_mi[a:b].mean(), e_hi[a:b].mean(),
                e_lo[a:b].std() / (e_lo[a:b].mean() + 1e-12)]
    # 화성은 CENS 처럼 부드럽게 — 순간 화음이 아니라 「그 자리의 조성」을 본다
    H = uniform_filter1d(H, size=int(2.0 / 홉), axis=0)
    T[:, 0] = 0                                   # 0차는 전체 세기 — 음량이므로 뺀다
    R = np.log(R + 1e-9)
    return H, T, R


def _임베딩(F, d):
    """앞뒤 d칸을 붙여 한 점으로. 순간 잡음에 안 흔들린다."""
    n, k = F.shape
    P = np.pad(F, ((d, d), (0, 0)), mode="edge")
    return np.hstack([P[i:i + n] for i in range(2 * d + 1)])


def _ssm(F):
    X = _임베딩((F - F.mean(0)) / (F.std(0) + 1e-9), 지연)
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)
    S = X @ X.T
    # 경로 강화 — 대각선 방향 중앙값으로 다듬는다
    return median_filter(S, size=(3, 3))


def _novelty(S, L):
    k = int(L / 홉)
    g = np.exp(-0.5 * (np.arange(-k, k + 1) / (k / 2.0)) ** 2)
    K = np.outer(g, g)
    K[:k, k + 1:] *= -1
    K[k + 1:, :k] *= -1
    nv = np.zeros(len(S))
    for i in range(k, len(S) - k):
        nv[i] = (S[i - k:i + k + 1, i - k:i + k + 1] * K).sum()
    nv[:k] = 0
    nv[-k:] = 0
    p = np.percentile(np.abs(nv[nv != 0]), 99) + 1e-12
    return np.clip(nv / p, -1, 1)


def novelty(m, SR):
    """세 갈래 × 세 커널 = 아홉 개를 합친다."""
    H, T, R = 특징(m, SR)
    총 = None
    for F, w in [(H, 1.0), (T, 1.0), (R, 0.7)]:
        S = _ssm(F)
        nv = sum(_novelty(S, L) for L in LS) / len(LS)
        총 = nv * w if 총 is None else 총 + nv * w
    총 = 총 - 총.min()
    return 총 / (총.max() + 1e-12)


def 경계(m, SR, 개수, 최소간격=10.0):
    nv = novelty(m, SR)
    pk, prop = sg.find_peaks(nv, distance=int(최소간격 / 홉), prominence=0.02)
    order = np.argsort(-prop["prominences"])
    sel = pk[order][:개수]
    return np.sort(sel * 홉), nv


def 자검사(허용=3.0):
    참 = [50, 90, 105, 160, 260, 275, 325, 425, 525]
    SR, m = 읽기("전곡화성.wav")
    찾음, _ = 경계(m, SR, 개수=9)
    print("[자검사] 범위를 주지 않고 전곡을 훑는다. 허용 오차 ±%.0f초" % 허용)
    맞음 = 0
    for t in 참:
        d = np.abs(찾음 - t)
        j = int(np.argmin(d))
        ok = d[j] <= 허용
        맞음 += ok
        print("   참 %4d초 → %7.2f초  (%+6.2f)  %s" % (t, 찾음[j], 찾음[j] - t, "OK" if ok else "★빗나감"))
    print("   찾은 아홉: " + " ".join("%.1f" % v for v in 찾음))
    print("   **%d/9**" % 맞음)
    return 맞음, 찾음


if __name__ == "__main__":
    맞음, _ = 자검사()
    if 맞음 < 8:
        sys.exit("\n자검사 미달 — 이 자로는 재지 않는다.")
    print("   → 통과\n")
    if len(sys.argv) > 1:
        SR, m = 읽기(sys.argv[1])
        b, _ = 경계(m, SR, int(sys.argv[2]) if len(sys.argv) > 2 else 9)
        print("[실측] %s" % sys.argv[1])
        for t in b:
            print("   %d:%05.2f" % (int(t) // 60, t % 60))
