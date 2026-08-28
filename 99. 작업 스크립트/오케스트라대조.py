# -*- coding: utf-8 -*-
"""오케스트라판이 원곡에 충실한가 — 숫자로 잰다.

무엇을 재나
    ① 화성·시간   원곡과 크로마그램(어느 음이 언제 울리나) 상관
    ② 강약         음량 곡선 상관 — 커지고 작아지는 모양이 같은가
    ③ 밝기         스펙트럼 무게중심 (Hz)
    ④ 질감         2 kHz 위 에너지 비율
    ⑤ 순함         스펙트럼 평탄도 — 낮을수록 「순한 톤」(오르간·신스),
                   높을수록 활·숨·잡음이 섞인 소리(생악기)

★ ⑤ 는 방향만 말한다. 해먼드·무그가 남았는지는 귀가 판정한다.
  이 도구는 「어느 판부터 들을까」를 정해줄 뿐이다.

자검사 셋 — 답을 아는 문제를 먼저 푼다. 하나라도 틀리면 멈춘다.
"""
import sys, os, subprocess, tempfile
import numpy as np
import 화성

SR = 44100
N, HOP = 4096, 2048


def 읽는다(경로):
    """wav·mp3 아무거나. 모노 float32, 44.1 kHz 로 돌려준다."""
    if not 경로.lower().endswith(".wav"):
        tmp = os.path.join(tempfile.gettempdir(), "orch_tmp.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", 경로,
                        "-ar", str(SR), "-ac", "2", tmp], check=True)
        경로 = tmp
    sr, x = 화성.read_wav(경로)     # ★ 자료형을 보고 나눈다 (T-12 · 12 문서)
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 2:
        x = x.mean(axis=1)
    mx = np.abs(x).max()
    if mx > 0:
        x = x / mx
    if sr != SR:                       # 성근 리샘플. 이 도구는 대조용이다
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
    return x.astype(np.float32)


def 스펙트럼(x):
    win = np.hanning(N).astype(np.float32)
    프레임수 = max(1, (len(x) - N) // HOP + 1)
    S = np.empty((프레임수, N // 2 + 1), dtype=np.float32)
    for i in range(프레임수):
        S[i] = np.abs(np.fft.rfft(x[i * HOP: i * HOP + N] * win))
    return S


def 크로마그램(S):
    f = np.fft.rfftfreq(N, 1 / SR)
    쓸것 = (f > 55) & (f < 4200)
    반음 = np.zeros(len(f), dtype=int)
    반음[쓸것] = np.round(12 * np.log2(f[쓸것] / 440.0)).astype(int) % 12
    C = np.zeros((S.shape[0], 12), dtype=np.float32)
    for p in range(12):
        C[:, p] = S[:, 쓸것 & (반음 == p)].sum(axis=1)
    합 = C.sum(axis=1, keepdims=True)
    return C / np.maximum(합, 1e-9)


def 상관(a, b):
    a, b = a.ravel(), b.ravel()
    n = min(len(a), len(b))
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def 잰다(x):
    S = 스펙트럼(x)
    f = np.fft.rfftfreq(N, 1 / SR)
    힘 = S.sum(axis=1) + 1e-9
    무게중심 = float((S * f).sum(axis=1).mean() / 힘.mean())
    고역 = float((S[:, f >= 2000].sum() / S.sum()))
    기 = np.exp(np.log(S + 1e-10).mean(axis=1))
    산 = S.mean(axis=1) + 1e-10
    평탄도 = float((기 / 산).mean())
    창 = 2048
    n = len(x) // 창
    음량 = np.sqrt((x[: n * 창].reshape(n, 창) ** 2).mean(axis=1))
    return dict(크로마=크로마그램(S), 무게중심=무게중심, 고역=고역,
                평탄도=평탄도, 음량=음량, 길이=len(x) / SR)


def 자검사(원본):
    잰것 = 잰다(원본)
    실패 = []
    # ① 자기 자신과는 완전히 같아야 한다
    if abs(상관(잰것["크로마"], 잰것["크로마"]) - 1.0) > 1e-6:
        실패.append("① 자기 자신과의 크로마 상관이 1.000 이 아니다")
    # ② 백색잡음과는 닮지 않아야 한다
    rng = np.random.default_rng(20051212)
    잡음 = 잰다(rng.standard_normal(len(원본)).astype(np.float32) * 0.3)
    c = 상관(잰것["크로마"], 잡음["크로마"])
    if c > 0.5:
        실패.append(f"② 백색잡음과의 크로마 상관이 {c:.3f} — 너무 높다")
    # ③ 잡음이 「순함」에서 생악기보다 높게 나와야 한다 (지표 방향)
    if 잡음["평탄도"] <= 잰것["평탄도"]:
        실패.append("③ 평탄도가 잡음에서 더 높지 않다 — 지표 방향이 뒤집혔다")
    return 실패


def 표(원본경로, 판들):
    원본 = 읽는다(원본경로)
    실패 = 자검사(원본)
    if 실패:
        print("자검사 실패 — 이 자로는 재지 않는다")
        for s in 실패:
            print("   ", s)
        sys.exit(1)
    print("자검사 3/3 통과\n")

    기준 = 잰다(원본)
    print(f"{'판':<26}{'길이':>7}{'화성·시간':>10}{'강약':>8}"
          f"{'밝기Hz':>9}{'고역%':>8}{'순함':>8}")
    print("-" * 76)
    print(f"{'★ 원곡 (우리 것)':<24}{기준['길이']:>7.1f}{1.000:>10.3f}{1.000:>8.3f}"
          f"{기준['무게중심']:>9.0f}{기준['고역']*100:>8.1f}{기준['평탄도']:>8.4f}")
    결과 = []
    for p in 판들:
        m = 잰다(읽는다(p))
        ch = 상관(기준["크로마"][:len(m["크로마"])], m["크로마"])
        dy = 상관(기준["음량"][:len(m["음량"])], m["음량"])
        이름 = os.path.basename(p).replace(".wav", "")
        print(f"{이름:<26}{m['길이']:>7.1f}{ch:>10.3f}{dy:>8.3f}"
              f"{m['무게중심']:>9.0f}{m['고역']*100:>8.1f}{m['평탄도']:>8.4f}")
        결과.append((이름, ch, dy, m))
    print("-" * 76)
    최고 = max(결과, key=lambda r: r[1])
    print(f"\n화성·시간이 원곡에 가장 가까운 것 — {최고[0]} ({최고[1]:.3f})")
    print("★ 해먼드·무그가 남았는지는 이 표가 못 잡는다. 귀가 판정한다.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용: python 오케스트라대조.py <원곡> <판1> [판2 ...]")
        sys.exit(2)
    표(sys.argv[1], sys.argv[2:])
