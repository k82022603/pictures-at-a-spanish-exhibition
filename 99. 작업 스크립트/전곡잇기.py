# -*- coding: utf-8 -*-
"""**조각 다섯을 전곡으로 잇는다 — 이으면서 검사한다.**

2026-08-22. **검수자가 「0:02~0:30 잡음」을 잡아낸 뒤에 만들었다.**

## 왜 검사가 이 안에 있나

그날 나는 Suno `Extend` 결과를 그대로 썼다. 화면이 **`KEEP`(0~43초)** 이라고 적어 놓았으니
그 구간은 원본 그대로일 줄 알았다. **아니었다** — 고역이 최대 23 dB 깎여 있었고,
**나는 재지 않았다. 낱말을 믿고 소리를 안 쟀다.**

**그래서 잇는 도구가 직접 본다.** 조각 안에서 **고역 비율이 갑자기 뛰는 자리**를 찾는다.
악기가 들어오며 바뀌는 것과 구분이 안 되므로 **오류가 아니라 경고**이고,
**사람이 그 시각을 듣고 판단한다.** 잡아 주지도 않는 것보다 낫다.

(`16. 도구 설명서` 가 지적한 구조 — **만드는 도구엔 자기검사가 있고 재는 도구엔 없다.**
이 파일은 만드는 도구이므로 있어야 한다.)
"""
import subprocess
import sys

import numpy as np

sys.path.insert(0, ".")
from 꼬리늘리기 import 읽기, 쓰기  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

페이드 = 0.020      # 조각 사이 크로스페이드
창 = 5.0            # 고역 검사 창
급변 = 8.0          # 이만큼 뛰면 경고 (dB)


def 고역비(x, sr):
    """5초마다 4 kHz 이상이 전체의 몇 dB 인가."""
    out = []
    n = int(창 * sr)
    for i in range(len(x) // n):
        s = x[i * n:(i + 1) * n].mean(axis=1)
        S = np.abs(np.fft.rfft(s * np.hanning(len(s)))) ** 2
        f = np.fft.rfftfreq(len(s), 1 / sr)
        out.append(10 * np.log10(S[f >= 4000].sum() / (S.sum() + 1e-20) + 1e-20))
    return np.array(out)


def 검사(이름, x, sr, 시작=0.0):
    """조각 안에서 고역이 갑자기 뛰는 자리를 찾는다."""
    h = 고역비(x, sr)
    경고 = []
    for i in range(1, len(h)):
        if abs(h[i] - h[i - 1]) >= 급변:
            t = 시작 + i * 창
            경고.append((t, h[i - 1], h[i]))
    print("  %-8s %7.2f초  고역 %5.1f ~ %5.1f dB  %s"
          % (이름, len(x) / sr, h.min(), h.max(),
             "OK" if not 경고 else "★ 급변 %d 곳" % len(경고)))
    for t, a, b in 경고:
        print("        ★ %d:%05.2f 에서 %+.1f dB (%.1f → %.1f) — **들어서 확인할 것**"
              % (int(t) // 60, t % 60, b - a, a, b))
    return 경고


def 잇기(조각, 출력):
    sr = None
    쓸것 = []
    print("[조각 검사]")
    누적 = 0.0
    모든경고 = []
    for 이름, p in 조각:
        s, x = 읽기(p)
        if sr is None:
            sr = s
        if s != sr:
            sys.exit("표본율이 다르다 — %s 는 %d, 나머지는 %d" % (이름, s, sr))
        모든경고 += 검사(이름, x, sr, 누적)
        누적 += len(x) / sr
        쓸것.append((이름, x))

    n = int(페이드 * sr)
    f = np.linspace(0, 1, n)[:, None]
    out = 쓸것[0][1]
    경계 = [0.0]
    for 이름, x in 쓸것[1:]:
        경계.append(len(out) / sr)
        a = out.copy()
        a[-n:] = a[-n:] * (1 - f) + x[:n] * f
        out = np.vstack([a, x[n:]])
    경계.append(len(out) / sr)

    피크 = np.abs(out).max()
    if 피크 >= 0.999:
        sys.exit("클리핑 — 피크 %.4f" % 피크)
    쓰기(출력, sr, out)

    # ── **낸 파일이 정말 float 인가** (2026-08-22) ──────────────────
    #
    # **`쓰기()` 가 `int16` 으로 떨어뜨리고 있었다.** 소리는 멀쩡했고 FLAC 은
    # 「무손실 100% 일치」라고 찍혔다 — **16비트 데이터를 32비트 그릇에
    # 정확히 담았으니 거짓말이 아니다.** `납품.py` 의 다른 경고 한 줄이
    # 아니었으면 못 봤다.
    #
    # **그래서 만든 쪽에서도 본다.** 「무손실」과 「비트가 살아 있다」는 다른 말이다.
    # **`ffprobe` 로 본다.** `화성.read_wav` 는 자료형을 −1~1 실수로 바꿔 돌려주므로
    # **파일에 무엇으로 적혔는지는 알 수 없다.** 여기서 알아야 하는 것이 바로 그것이다.
    낸것 = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=sample_fmt",
         "-of", "default=nw=1:nk=1", 출력],
        capture_output=True, text=True).stdout.strip()
    print("\n[자료형] 낸 파일 %s  %s"
          % (낸것, "OK" if 낸것.startswith("flt") else "★ float 가 아니다"))
    if not 낸것.startswith("flt"):
        sys.exit("낸 파일이 float 가 아니다 — 꼬리늘리기.쓰기() 를 본다")

    m = out.mean(axis=1)
    d = np.abs(np.diff(m))
    한계 = np.percentile(d, 99.99)
    print("\n[이음매 검사] 전곡 99.99%% 도약 = %.5f" % 한계)
    for (이름, _), t in list(zip(쓸것, 경계))[1:]:
        k = int(t * sr)
        튐 = d[k - 480:k + 480].max()
        print("  %d:%05.2f  %-6s 앞  최대 도약 %.5f  %s"
              % (int(t) // 60, t % 60, 이름, 튐, "OK" if 튐 <= 한계 else "★튄다"))

    print("\n**%.2f초 = %d:%05.2f · 피크 %.3f (%.1f dBFS)**"
          % (len(out) / sr, int(len(out) / sr) // 60, (len(out) / sr) % 60,
             피크, 20 * np.log10(피크)))
    print("\n[조각 경계 — 확실한 값]")
    for (이름, _), t in zip(쓸것, 경계):
        print("  %-8s %d:%05.2f" % (이름, int(t) // 60, t % 60))
    print("  %-8s %d:%05.2f" % ("끝", int(경계[-1]) // 60, 경계[-1] % 60))
    return 모든경고


if __name__ == "__main__":
    S = "../산출물/20260821 - 전곡을 Suno 에 넘긴다/Suno 전곡 맡기기"
    N = "../산출물/20260822 - 0악장을 다시 만든다"
    잇기([("0악장", N + "/받은 것 - 0악장 Extend/0악장 - 원본 앞부분 + 맺음 + 꼬리.wav"),
          ("1부b",  N + "/받은 것 - 1부b Extend/1부b - 꼬리 3.5초.wav"),
          ("2부",   S + "/받은 것 - 2부/2부 Suno-03.wav"),
          ("3부",   S + "/받은 것 - 3부/3부 Suno-04.wav"),
          ("4부",   S + "/받은 것 - 4부/4부 Suno-03.wav")],
         N + "/이어붙인 것/전곡 E - 0악장 앞부분을 원본으로 되돌린 것.wav")
