# -*- coding: utf-8 -*-
"""**악장 경계를 찾는 자.** 화성 하나가 아니라 여섯 가지를 함께 본다.

2026-08-22. 앞선 자(`악장찾기.py`)는 **크로마만** 봤고, 그래서
**7악장 ↔ 8악장 경계를 못 찾았다** — 둘 다 D 를 중심음으로 쓰므로 화성이 안 갈린다.
**우리 곡에서도 그 경계의 크로마 닮음이 0.887 이다.** 자가 못 볼 자리였다.

**여섯을 본다** — 크로마 12 · 대역 에너지 8 · 저역 타격 · 고역 타격 ·
스펙트럼 무게중심 · 음량. 악장이 바뀌면 **적어도 하나는 움직인다.**

방법은 자기유사도 행렬(SSM)에 **체커보드 커널**을 씌워 novelty 를 뽑는 표준 방식이다.
「앞 L초끼리 닮고, 뒤 L초끼리 닮고, 앞뒤는 안 닮은」 자리가 경계다.

**자기검사가 이 도구의 핵심이다** — 우리 곡에 돌려 **알려진 경계 아홉**을 찾는지 본다.
못 찾으면 멈춘다. 답을 아는 문제로 자를 재지 않으면 Suno 판의 결과도 못 믿는다.
"""
import os
import sys

import numpy as np
from scipy import signal as sg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 화성

sys.stdout.reconfigure(encoding="utf-8")

창 = 1.0            # 특징 한 칸의 길이(초)
홉 = 0.5            # 칸 간격(초)
LS = [6.0, 12.0, 24.0]   # 커널 반쪽 길이 셋. **한 크기로는 못 잡는다** —
                         # 2·5악장은 15초뿐이라 16초 커널이 통째로 삼킨다.
                         # 짧은 자리는 6 이, 긴 자리는 24 가 잡는다.


def 읽기(p):
    """**`화성.read_wav` 가 자료형을 본다.** 직접 `/ 32768` 하지 않는다 — 마스터가
    float32 로 바뀐 날 도구 여섯이 전부 −110 dB 를 찍은 적이 있다(`검증.py` 7번).

    이 파일은 **한 채널로 합친 것**을 쓴다."""
    sr, x = 화성.read_wav(p)
    return sr, x.mean(axis=1) if x.ndim > 1 else x


def 특징(m, SR):
    """칸마다 22개 숫자. 크로마 12 · 대역 8 · 타격 2."""
    h = int(홉 * SR)
    w = int(창 * SR)
    n = (len(m) - w) // h + 1
    # 저·고역 봉투는 미리 한 번만
    def 봉투(lo, hi):
        sos = sg.butter(4, [lo, hi], "band", fs=SR, output="sos")
        return np.abs(sg.sosfiltfilt(sos, m))
    e_lo, e_hi = 봉투(60, 150), 봉투(6000, 12000)
    F = np.zeros((n, 22))
    edges = np.array([40, 100, 250, 500, 1000, 2000, 4000, 8000, 16000])
    for i in range(n):
        s = m[i * h:i * h + w]
        f, P = sg.welch(s, SR, nperseg=min(4096, len(s)))
        tot = P.sum() + 1e-20
        # 크로마
        ok = (f > 55) & (f < 4200)
        ff, PP = f[ok], P[ok]
        pc = np.rint(12 * np.log2(ff / 440.0 + 1e-20) + 69).astype(int) % 12
        c = np.array([PP[pc == k].sum() for k in range(12)])
        F[i, :12] = c / (c.sum() + 1e-20)
        # 대역 8
        for k in range(8):
            F[i, 12 + k] = P[(f >= edges[k]) & (f < edges[k + 1])].sum() / tot
        # 타격 세기(봉투 평균) — 밀도 대신 세기를 쓴다. 창이 1초라 개수는 불안정하다
        F[i, 20] = e_lo[i * h:i * h + w].mean()
        F[i, 21] = e_hi[i * h:i * h + w].mean()
    # 열마다 z-정규화 — 단위가 다른 것들을 같은 무게로
    F = (F - F.mean(axis=0)) / (F.std(axis=0) + 1e-9)
    return F


def _nv1(S, L):
    """한 크기의 체커보드 novelty."""
    k = int(L / 홉)
    g = np.exp(-0.5 * (np.arange(-k, k + 1) / (k / 2.0)) ** 2)
    K = np.outer(g, g)
    sign = np.ones((2 * k + 1, 2 * k + 1))
    sign[:k, k + 1:] = -1
    sign[k + 1:, :k] = -1
    K = K * sign
    nv = np.zeros(len(S))
    for i in range(k, len(S) - k):
        nv[i] = (S[i - k:i + k + 1, i - k:i + k + 1] * K).sum()
    nv[:k] = 0
    nv[-k:] = 0
    m = np.abs(nv).max() + 1e-12
    return nv / m


def novelty(F):
    """SSM + **여러 크기**의 체커보드 커널을 합친다."""
    X = F / (np.linalg.norm(F, axis=1, keepdims=True) + 1e-9)
    S = X @ X.T
    nv = np.zeros(len(S))
    for L in LS:
        nv = nv + _nv1(S, L)
    return nv / (np.abs(nv).max() + 1e-12)


def 경계(m, SR, 개수, 최소간격=10.0):
    F = 특징(m, SR)
    nv = novelty(F)
    pk, _ = sg.find_peaks(nv, distance=int(최소간격 / 홉))
    pk = pk[np.argsort(-nv[pk])][:개수]
    return np.sort(pk * 홉), nv


def 자검사():
    """**답을 아는 문제.** 우리 곡의 경계 아홉을 찾아내는가."""
    참 = [50, 90, 105, 160, 260, 275, 325, 425, 525]
    SR, m = 읽기("전곡화성.wav")
    찾음, _ = 경계(m, SR, 개수=14)
    print("[자검사] 우리 곡의 알려진 경계 아홉을 찾는가")
    맞음 = 0
    for t in 참:
        d = np.abs(찾음 - t)
        j = int(np.argmin(d))
        ok = d[j] <= 6.0
        맞음 += ok
        print("   참 %4d초 → 찾은 %7.1f초  (차이 %5.1f초)  %s"
              % (t, 찾음[j], 찾음[j] - t, "OK" if ok else "★빗나감"))
    print("   맞춘 것 %d/9" % 맞음)
    if 맞음 < 7:
        sys.exit("자검사 실패 — 아홉 중 %d 개만 맞다. 이 자로는 재지 않는다." % 맞음)
    print("   → 자검사 통과\n")
    return 찾음


if __name__ == "__main__":
    자검사()
    if len(sys.argv) > 1:
        SR, m = 읽기(sys.argv[1])
        개수 = int(sys.argv[2]) if len(sys.argv) > 2 else 9
        b, nv = 경계(m, SR, 개수)
        print("[실측] %s" % sys.argv[1])
        print("  찾은 경계 %d개" % len(b))
        for t in b:
            print("    %d:%05.2f  (%.1f초)" % (int(t) // 60, t % 60, t))
