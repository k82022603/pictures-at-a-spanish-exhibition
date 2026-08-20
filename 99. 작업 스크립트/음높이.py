# -*- coding: utf-8 -*-
"""**소리의 높이를 잰다 — 이 프로젝트에서 높이를 재는 곳은 여기 하나다.**

2026-08-20 신설. 그전에는 `창법실측.py` 안에 `f0_track` 이 있었고, 그것을
`보컬가락.py` 가 **옮겨 적으면서** 같은 것이 두 곳이 됐다. `11. 공용 함수`
문서가 못박은 것이 그것이다 — **같은 일을 두 곳에 적지 않는다.**

**그리고 그 자가 틀려 있었다.**

  자기상관에서 봉우리를 고를 때 **가장 큰 지연**을 집고 있었다. 주기가 T 인
  소리는 T·2T·3T 에서 다 봉우리가 서므로, 가장 큰 지연을 집으면 **2T·3T** 를
  집는다. 그러면 높이가 **1/2·1/3 로 읽힌다.**

  | 넣은 음 | 옛 자 | 새 자 |
  |---|---|---|
  | 440 Hz (A4) | **146 Hz (D3)** — 1910센트 틀림 | 440.2 Hz (+1센트) |
  | 698 Hz (F5) | **140 Hz (C♯3)** — 2783센트 틀림 | 698.7 Hz (+1센트) |

  **낮은 소리는 2T 가 검색 범위 밖이라 우연히 맞았고, 높은 소리일수록 크게
  틀렸다.** 노래 목소리가 정확히 그 범위에 있다.

**어떻게 찾았나** — `보컬가락.py` 로 **계산해서 넣은 높이**가 목표보다 한
옥타브 아래로 읽혔다. 계산으로 넣은 것은 어긋날 수가 없으므로 **소리가 아니라
자를 의심해야 했다.** 아는 음(사인)을 넣어 보니 자가 틀렸다.

  > **이것이 「도구가 확인하게 한다」가 필요한 이유다.** 이 자는 넉 달 동안
  > 아무도 검사하지 않았고, **틀린 값이 그럴듯해 보였기 때문에** 그대로 문서와
  > 판정에 들어갔다. 경위는 `97. 회고` T-12.

**옛 자를 지우지 않고 남긴다**(R3 의 정신) — 어제 결론이 그 자로 나왔고,
**얼마나 달라지는지 견줄 수 있어야 그 결론을 다시 읽을 수 있다.**

    import 음높이
    tr = 음높이.재기(x)            # 0.01초마다. 노래가 아닌 구간은 0
    tr = 음높이.재기(x, 옛방식=True)   # 옛 자 (견주기용)
"""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
NAMES = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]


def 이름(hz):
    """Hz 를 사람이 읽는 음 이름으로. 옥타브 번호까지."""
    if hz is None or hz <= 0:
        return "—"
    m = int(round(69 + 12 * np.log2(hz / 440.0)))
    return "%s%d" % (NAMES[m % 12], m // 12 - 1)


def midi(hz):
    return 69 + 12 * np.log2(np.asarray(hz, float) / 440.0)


def 재기(x, lo=70.0, hi=800.0, hop=0.01, win=0.045, 옛방식=False):
    """0.01초마다 높이를 잰다. 노래로 볼 수 없는 구간은 0.

    자기상관(소리를 자기 자신과 겹쳐 보며 몇 초마다 되풀이되는지 찾는 것)을
    쓴다. **되풀이 주기의 첫 봉우리가 그 소리의 높이**이고, 꼭대기는 이웃
    셋으로 포물선을 맞춰 소수점까지 본다.

    `옛방식=True` 는 2026-08-20 이전의 틀린 자다. **견주기 위해서만 쓴다.**
    """
    sos = butter(4, [lo * 0.8, min(hi * 2.5, SR / 2 - 100)], "bandpass",
                 fs=SR, output="sos")
    y = sosfilt(sos, np.asarray(x, float))
    w, h = int(win * SR), int(hop * SR)
    out = []
    for i in range(0, max(1, len(y) - w), h):
        s = y[i:i + w] - y[i:i + w].mean()
        if np.sqrt(np.mean(s ** 2)) < 1e-4:
            out.append(0.0)
            continue
        r = np.correlate(s, s, "full")[len(s) - 1:]
        r = r / (r[0] + 1e-12)
        a, b = int(SR / hi), min(int(SR / lo), len(r) - 1)
        if b <= a + 2:
            out.append(0.0)
            continue
        band = r[a:b]
        pk = band.max()
        if pk < 0.35:                        # 주기성이 약하면 노래가 아니다
            out.append(0.0)
            continue
        if 옛방식:
            cand = np.where(band > 0.86 * pk)[0]
            grp = [cand[0]]
            for j in cand[1:]:
                if j - grp[-1] > 2:
                    grp.append(j)
            out.append(SR / (a + grp[-1]))   # ← 여기가 틀렸던 자리
            continue
        idx = None
        for j in range(1, len(band) - 1):
            if (band[j] >= band[j - 1] and band[j] > band[j + 1]
                    and band[j] > 0.80 * pk):
                idx = j
                break
        if idx is None:
            out.append(0.0)
            continue
        y0, y1, y2 = band[idx - 1], band[idx], band[idx + 1]
        den = y0 - 2 * y1 + y2
        d = 0.5 * (y0 - y2) / den if abs(den) > 1e-12 else 0.0
        out.append(SR / (a + idx + float(np.clip(d, -1, 1))))
    return np.array(out)


def 요약(tr, 최저=65, 가운데=72):
    """음높이 자취를 판정용 숫자 셋으로. 기본값은 F4 · C5 (우리 선율 기준).

    반환 — (가운데 음 Hz, 최저음 위 %, 가운데 음 위 %) · 못 재면 None
    """
    v = np.asarray(tr)
    v = v[v > 0]
    if len(v) < 10:
        return None
    m = midi(v)
    return (float(np.median(v)),
            float(np.mean(m >= 최저 - 0.5) * 100.0),
            float(np.mean(m >= 가운데 - 0.5) * 100.0))


def 자검사(verbose=True):
    """**아는 음을 넣어 자가 맞는지 본다.** 틀리면 False.

    이 함수가 있는 이유 — 옛 자는 넉 달 동안 아무도 검사하지 않았다.
    """
    좋음 = True
    for hz in (146.83, 174.61, 220.0, 261.63, 349.23, 440.0, 523.25, 698.46):
        t = np.arange(int(1.2 * SR)) / SR
        x = sum(np.sin(2 * np.pi * hz * k * t) / k for k in range(1, 9)) * 0.2
        r = 요약(재기(x))
        c = 1200 * np.log2(r[0] / hz) if r else 9999
        if abs(c) > 10:
            좋음 = False
        if verbose:
            print("  %6.1f Hz %-4s → %7.1f Hz %-4s  %+5.0f 센트  %s"
                  % (hz, 이름(hz), r[0] if r else 0, 이름(r[0] if r else 0),
                     c, "OK" if abs(c) <= 10 else "**틀림**"))
    return 좋음


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    print("높이 재는 자 — 아는 음으로 검사한다\n")
    print("=== 새 자 ===")
    ok = 자검사()
    print("\n  %s" % ("**통과 — 전부 10센트 안이다**" if ok else "**실패**"))
