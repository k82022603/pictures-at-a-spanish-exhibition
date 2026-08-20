# -*- coding: utf-8 -*-
"""참조 음원에서 **부르는 법을 숫자로 잰다.**

2026-08-14. 검수자가 참조용 음원을 주기로 했다.

**무엇을 하는 도구인가 —** 노래하는 소리를 재서 **음역 · 떨림 · 박자 타는
버릇 · 목소리의 굵기 · 시작하는 세기 · 긴 음의 흐름**을 숫자로 뽑는다.
그 숫자가 `산출물/…/창법 지시서 - 여행자의 목소리.md` 의 3절을 구체적인
값으로 바꾼다.

**무엇을 하는 도구가 아닌가 —** 목소리를 떼어내지 않고, 저장하지 않고,
어디에도 넣지 않는다. **재기만 한다.** 남는 것은 숫자뿐이다.

  `CLAUDE.md` 6절 — *"창법·음역·음색은 참조해도 된다. 사실이고 저작
  대상이 아니다. 편곡·가사·구성은 금지다."*

**참조 음원 자체는 git 에 안 올린다** (`.gitignore` 가 이미 음원을 막는다).

    python 창법실측.py "자료/참조.mp3"
    python 창법실측.py "자료/참조.mp3" 62:14 91:12      # 분:초 시작 + 길이(초)
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
from scipy.signal import butter, sosfilt

import 화성
import 음높이

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
NAMES = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]


def note(hz):
    """Hz 를 음 이름으로. 사람이 읽을 것이므로 옥타브 번호까지."""
    if hz <= 0:
        return "—"
    m = 69 + 12 * np.log2(hz / 440.0)
    return "%s%d" % (NAMES[int(round(m)) % 12], int(round(m)) // 12 - 1)


def load(path, t0=None, dur=None):
    """어떤 형식이든 ffmpeg 로 읽는다. **가운데 소리만** 남긴다.

    노래는 대개 좌우 한가운데 놓인다. 좌우를 더하면 가운데가 살고, 좌우로
    벌려 놓은 악기는 상대적으로 묻힌다 — **완전한 분리가 아니라 재기
    좋게 만드는 정도**다.
    """
    tmp = os.path.join(tempfile.gettempdir(), "_창법실측.wav")
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if t0 is not None:
        cmd += ["-ss", str(t0)]
    if dur is not None:
        cmd += ["-t", str(dur)]
    cmd += ["-i", path, "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", tmp]
    subprocess.run(cmd, check=True)
    sr, x = 화성.read_wav(tmp)        # 자료형을 보고 나눈다 (검증.py 7번)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    mid = (x[:, 0] + x[:, 1]) / 2.0
    return mid, x.mean(1)


def f0_track(x, lo=70.0, hi=800.0, hop=0.01, win=0.045):
    """0.01초마다 높이를 잰다. 목소리가 아닌 구간은 0 으로 둔다.

    **2026-08-20 — 이 함수의 본문이 틀려 있었다.** 자기상관에서 **가장 큰
    지연**을 집고 있었는데, 주기가 T 인 소리는 T·2T·3T 에 다 봉우리가 서므로
    그러면 **2T·3T 를 집어 높이가 1/2·1/3 로 읽힌다.**

      | 넣은 음 | 옛 자가 읽은 값 |
      |---|---|
      | 440 Hz (A4) | **146 Hz (D3)** |
      | 698 Hz (F5) | **140 Hz (C♯3)** |

    **낮은 소리는 우연히 맞았고 노래 목소리 대역에서 크게 틀렸다.**
    8-14 참조 음원 실측과 8-19 Suno 실측이 이 자로 나왔다. 다시 잰 값과
    경위는 `97. 회고` **T-12** · `14` **11장**.

    **본문은 `음높이.py` 한 곳으로 옮겼다**(`11. 공용 함수`). 이름은 그대로
    두어 부르는 쪽을 안 건드린다. 옛 자로 견주려면 `음높이.재기(x,
    옛방식=True)`.
    """
    return 음높이.재기(x, lo=lo, hi=hi, hop=hop, win=win)


def band_ratio(x):
    """소리의 굵기 — 어느 대역에 힘이 실려 있는가."""
    n = 1 << 16
    S = np.zeros(n // 2 + 1)
    w = np.hanning(n)
    cnt = 0
    for i in range(0, max(1, len(x) - n), n // 2):
        S += np.abs(np.fft.rfft(x[i:i + n] * w)) ** 2
        cnt += 1
    S /= max(1, cnt)
    f = np.fft.rfftfreq(n, 1 / SR)
    tot = S.sum() + 1e-12
    out = {}
    for nm, lo, hi in (("저역 (~200)", 0, 200), ("★ 저중역 (200~500)", 200, 500),
                       ("중역 (500~2k)", 500, 2000),
                       ("존재감 (2k~5k)", 2000, 5000), ("공기 (5k~)", 5000, SR / 2)):
        out[nm] = 100.0 * S[(f >= lo) & (f < hi)].sum() / tot
    return out


def vibrato(tr):
    """떨림 — 얼마나 자주, 얼마나 넓게 흔드는가.

    긴 음(0.25초 이상 이어진 구간)만 본다. 음을 옮겨 다니는 것과 한 음을
    흔드는 것은 다르다.
    """
    segs, cur = [], []
    for v in tr:
        if v > 0:
            cur.append(v)
        else:
            if len(cur) >= 25:
                segs.append(np.array(cur))
            cur = []
    if len(cur) >= 25:
        segs.append(np.array(cur))
    # **한 음 안에서만 잰다.** 첫 판은 「소리가 이어진 구간」을 통째로 재서
    # **음이 바뀌는 것까지 떨림으로 셌다** — 1433 센트(한 옥타브)가 나왔고
    # 사람이 그렇게 떨 수는 없다. 반음 넘게 움직이면 **거기서 끊는다.**
    holds = []
    for s in segs:
        cut = [0]
        for i in range(1, len(s)):
            if abs(1200 * np.log2(s[i] / s[i - 1])) > 60:      # 반음의 절반
                cut.append(i)
        cut.append(len(s))
        for a, b in zip(cut, cut[1:]):
            if b - a >= 30:                        # 0.3초 이상 머문 음만
                holds.append(s[a:b])
    rate, depth = [], []
    for s in holds:
        c = 1200 * np.log2(s / np.median(s))       # 센트
        c = c - np.convolve(c, np.ones(15) / 15, "same")   # 큰 흐름은 뺀다
        z = np.where(np.diff(np.sign(c)))[0]
        if len(z) > 3:
            rate.append(len(z) / 2.0 / (len(s) * 0.01))
            depth.append(np.percentile(np.abs(c), 90) * 2)
    return (float(np.median(rate)) if rate else 0.0,
            float(np.median(depth)) if depth else 0.0,
            len(holds))


def attack(x):
    """소리를 시작할 때 얼마나 무르게 여는가 — 최대에 닿기까지 몇 ms."""
    e = np.abs(x)
    w = int(0.005 * SR)
    e = np.convolve(e, np.ones(w) / w, "same")
    thr = 0.25 * e.max()
    on = np.where(e > thr)[0]
    if len(on) < 2:
        return 0.0
    starts = [on[0]] + [on[i] for i in range(1, len(on))
                        if on[i] - on[i - 1] > int(0.15 * SR)]
    ms = []
    for s in starts[:40]:
        seg = e[s:s + int(0.25 * SR)]
        if len(seg) > 10:
            ms.append(1000.0 * int(np.argmax(seg)) / SR)
    return float(np.median(ms)) if ms else 0.0


def report(path, t0=None, dur=None, label=""):
    mid, mono = load(path, t0, dur)
    tr = f0_track(mid)
    voiced = tr[tr > 0]
    print("\n" + "─" * 62)
    print("구간 %s  (%.1f초)" % (label or "전체", len(mono) / SR))
    print("─" * 62)
    if len(voiced) < 20:
        print("  노래로 볼 만한 소리를 못 찾았다. 구간을 다시 지정한다")
        return
    lo, med, hi = (np.percentile(voiced, 5), np.median(voiced),
                   np.percentile(voiced, 95))
    print("  음역        %s ~ %s   (가운데 %s)" % (note(lo), note(hi), note(med)))
    print("              %.0f ~ %.0f Hz" % (lo, hi))
    r, d, n = vibrato(tr)
    print("  떨림        초당 %.1f 번 · 폭 %.0f 센트  (긴 음 %d 개에서)" % (r, d, n))
    print("              %s" % ("거의 안 떤다 — 곧은 소리" if d < 40 else
                                "조금 떤다" if d < 90 else "많이 떤다"))
    print("  시작        최대까지 %.0f ms  %s" %
          (attack(mid), "(무르게 연다)" if attack(mid) > 60 else "(또렷하게 친다)"))
    print("  소리의 굵기")
    for k, v in band_ratio(mid).items():
        print("     %-18s %5.1f %%  %s" % (k, v, "█" * int(v / 2)))
    print("  노래가 이어진 시간  %.0f %%" % (100.0 * len(voiced) / len(tr)))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    path = sys.argv[1]
    print("창법 실측 —", os.path.basename(path))
    print("**재기만 한다. 소리는 남기지 않는다.**")
    spans = sys.argv[2:]
    if not spans:
        report(path)
        return
    for s in spans:
        mm, rest = s.split(":", 1)
        ss, dur = (rest.split("+") + ["15"])[:2] if "+" in rest else (rest, "15")
        t0 = int(mm) * 60 + float(ss)
        report(path, t0, float(dur), "%s:%s 부터 %s초" % (mm, ss, dur))


if __name__ == "__main__":
    main()
