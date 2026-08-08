# -*- coding: utf-8 -*-
"""악장별 사실을 **코드와 음원에서 뽑아** 표로 만든다.

    python 악장표.py            화면에 출력
    python 악장표.py --md       악장표.md 로 저장

**손으로 적지 않는다.** `CLAUDE.md` 2절이 못박은 것 — 같은 사실이 두 곳에
있으면 반드시 어긋난다. 2026-08-08 하루에만 문서와 코드가 세 번 어긋났고
(6악장 베이스·9악장 컴파스·1악장 슬롯 넘침), 그래서 이 표는 **읽어서 만든다.**

읽는 곳
    전곡화성.py   악장 경계(mark) · 템포(BT/BB) · 화음 진행(PROG) · 잔향 곡선
    chordlog.npy  실제로 놓인 화음의 시각 — 슬롯을 넘겼는지 여기서 드러난다
    전곡화성.wav  악장별 RMS
    스템/*.wav    악장별 편성 (어느 악기가 실제로 소리를 내는가)
"""
import io
import os
import re
import sys

import numpy as np

SR = 44100
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "전곡화성.py")
WAV = os.path.join(HERE, "전곡화성.wav")
CLOG = os.path.join(HERE, "chordlog.npy")
STEMS = os.path.join(HERE, "스템")

STEM_NAME = {"kb": "피아노", "org": "해먼드", "bass": "베이스", "str": "현악",
             "gtr": "기타", "lead": "무그", "perc": "팔마스·카혼", "drum": "드럼"}


def read_source():
    """전곡화성.py 에서 악장 경계와 템포를 읽는다."""
    src = io.open(SRC, encoding="utf-8").read().split("\n")
    movs, cur, tempo, prog = [], None, {}, {}
    for ln in src:
        m = re.match(r'mark\("(\d)악장 ([^·"]+)', ln)
        if m:
            cur = int(m.group(1))
            t = re.search(r",\s*([\d.]+)\s*[,)]", ln)
            movs.append((cur, m.group(2).strip(), float(t.group(1)) if t else 0.0))
        m2 = re.match(r"B[TB] = (.+?)(\s+#|$)", ln)
        if m2 and cur is not None and cur not in tempo:
            try:
                tempo[cur] = 60.0 / eval(m2.group(1))
            except Exception:
                pass
        m3 = re.match(r"PROG(\d) = (\[.*)", ln)
        if m3:
            prog[int(m3.group(1))] = m3.group(2)
    return movs, tempo, prog


def beats_of(prog_text, src_all):
    """PROG 리터럴이 여러 줄이면 이어 붙여 박수 합을 센다."""
    i = src_all.index(prog_text)
    buf, depth = "", 0
    for ch in src_all[i:]:
        buf += ch
        depth += (ch == "[") - (ch == "]")
        if depth == 0 and buf.strip():
            break
    nums = re.findall(r',\s*(\d+)\s*\)', buf)
    return sum(int(n) for n in nums), len(nums)


def feel(q):
    """♩ 값을 몸으로 아는 말로 바꾼다."""
    if q < 60:  return "아주 느리게 — 천천히 걷는 것보다 느리다"
    if q < 76:  return "느리게 — 편히 걷는 속도"
    if q < 96:  return "보통 — 빠르게 걷는 속도"
    if q < 120: return "조금 빠르게 — 행진하는 속도"
    if q < 152: return "빠르게 — 가볍게 조깅하거나 신나게 고개를 끄덕이는 속도"
    return "아주 빠르게"


def busy(iv):
    if iv < 1.2:  return "쉴 틈 없이 바뀐다"
    if iv < 2.5:  return "매끄럽고 다채롭게 들린다"
    if iv < 4.0:  return "여유 있게 흐른다"
    return "아주 느긋하다. 한 색깔이 오래 머문다"


def loud(db):
    if db > -14:  return "큰 음량 — 곡에서 두꺼운 자리"
    if db > -18:  return "적당한 음량 — 크고 작음의 차이를 남겨둔 상태"
    if db > -21:  return "작은 음량 — 물러나 있다"
    return "아주 작다 — 비어 있는 자리"


def main():
    src_all = io.open(SRC, encoding="utf-8").read()
    movs, tempo, prog = read_source()
    movs.sort()
    bounds = [m[2] for m in movs] + [580.0]

    cl = np.load(CLOG, allow_pickle=True) if os.path.exists(CLOG) else []
    cts = np.array(sorted(float(r[0]) for r in cl)) if len(cl) else np.array([])

    wav = None
    if os.path.exists(WAV):
        import scipy.io.wavfile as wf
        _, x = wf.read(WAV)
        wav = x.astype(np.float64) / 32768.0
        if wav.ndim > 1:
            wav = wav.mean(1)

    stems = {}
    for k in STEM_NAME:
        p = os.path.join(STEMS, "스템-%s.wav" % k)
        if os.path.exists(p):
            import scipy.io.wavfile as wf
            _, y = wf.read(p)
            y = y.astype(np.float64)
            stems[k] = y.mean(1) if y.ndim > 1 else y

    def rms(a, s, e):
        seg = a[int(s * SR):int(e * SR)]
        return 20 * np.log10(max(np.sqrt((seg ** 2).mean()), 1e-12)) if len(seg) else -999

    print("악장별 사실표 — 코드와 음원에서 생성")
    print("=" * 78)
    for i, (n, name, t0) in enumerate(movs):
        t1 = bounds[i + 1]
        bpm = tempo.get(n)
        nb, nch = beats_of(prog[n], src_all) if n in prog else (0, 0)
        bar = nb * (60.0 / bpm) if bpm and nb else 0

        print()
        print("%d악장 · %s" % (n, name))
        print("  시각        %.1f ~ %.1f초  (%.0f초)" % (t0, t1, t1 - t0))
        if bpm:
            unit = "♪" if bpm > 140 else "♩"
            print("  빠르기      %s = %.0f%s" % (unit, bpm,
                  "   ← 8분음표 기준. 악보에 ♩로 적으면 두 배 빨라진다" if unit == "♪" else ""))
        if nb:
            print("  화음 진행   %d개 · %d박 · 한 바퀴 %.1f초" % (nch, nb, bar))
        if len(cts):
            m = (cts >= t0) & (cts < t1)
            k = int(m.sum())
            if k:
                print("  화성 리듬   %d개 · %.2f개/초 · 평균 %.2f초마다" %
                      (k, k / (t1 - t0), (t1 - t0) / k))
            # 슬롯 넘침 — **어림이 아니라 실측한다.**
            #
            # 이 악장의 화음 간격을 따라 경계 밖까지 화음이 계속 나타나면
            # 넘친 것이다. 2026-08-08 에 1악장이 13.9초, 7악장이 12.8초
            # 넘겨 다음 악장을 덮고 있었고, **두 템포가 겹쳐 울려 둘 다
            # 흐려졌다.** "138인데 138로 안 들린다"의 원인이었다.
            inside = cts[m]
            if len(inside) >= 3:
                g = float(np.median(np.diff(inside)))
                last = float(inside[-1])
                while g > 0.05:
                    nxt = cts[np.abs(cts - (last + g)) < g * 0.12]
                    if not len(nxt) or last > t1 + 90:
                        break
                    last = float(nxt[0])
                over = last - t1
                if over > 1.0:
                    print("  ⚠ 슬롯 넘침   %.1f초 — 다음 악장을 덮는다 (마지막 화음 %.1f초)"
                          % (over, last))
        if wav is not None:
            print("  RMS         %.1f dB" % rms(wav, t0, t1))
        parts = []
        if stems:
            on = []
            for k, y in stems.items():
                r = rms(y, t0, t1)
                if r > -70:
                    on.append("%s %.0f" % (STEM_NAME[k], r))
                    parts.append((STEM_NAME[k], r))
            print("  편성        " + " · ".join(on))

        # ── 풀어쓴 판 (CLAUDE.md 8절) ──────────────────────────────
        # 표는 정확하지만, 그 숫자가 무엇을 뜻하는지 알아야 쓸모가 있다.
        print()
        print("  ── 풀어서 ──")
        print("  · %.0f초 동안 연주 — %.0f초 지점부터 %.0f초 지점까지" % (t1 - t0, t0, t1))
        if bpm:
            if bpm > 140:
                q = bpm / 2.0
                print("  · %s — 8분음표 기준이라 4분음표로는 ♩=%.0f 다." % (feel(q), q))
                print("    **악보에 ♩=%.0f 로 적으면 두 배 빨라진다.**" % bpm)
            else:
                print("  · %s (♩=%.0f)" % (feel(bpm), bpm))
        if len(cts):
            k = int(((cts >= t0) & (cts < t1)).sum())
            if k:
                iv = (t1 - t0) / k
                print("  · 약 %.1f초마다 소리의 색깔이 바뀐다 — %s" % (iv, busy(iv)))
        if wav is not None:
            print("  · %s" % loud(rms(wav, t0, t1)))
        if parts:
            parts.sort(key=lambda p: -p[1])
            lead = [p[0] for p in parts if p[1] >= parts[0][1] - 4]
            back = [p[0] for p in parts if parts[0][1] - 12 <= p[1] < parts[0][1] - 4]
            quiet = [p[0] for p in parts if p[1] < parts[0][1] - 12]
            print("  · 주인공: %s" % ", ".join(lead))
            if back:
                print("    배경: %s — 뒤에서 은은하게 깔아준다" % ", ".join(back))
            if quiet:
                print("    숨은 조력자: %s — 아주 살살, 묵묵히 박자만" % ", ".join(quiet))
    print()
    print("=" * 78)
    print("이 표는 생성물이다. 고치려면 전곡화성.py 를 고치고 다시 돌린다.")


if __name__ == "__main__":
    main()
