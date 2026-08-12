"""
화성 엔진 — 성부 진행 자동 최적화 + 테이프 새추레이션 마스터 체인
《스페인 전람회의 그림》 WBS 1.4 / BL-24 일부

"조잡한 소리"의 원인은 두 곳이다.
  (1) 화성 — 성부가 병행으로 움직이고, 저역에서 3도가 뭉치고, 화음이 매번 같은 자리에 놓인다.
  (2) 음색 — 디지털 합성의 2~4kHz 경직됨. 실제 1970년대 음반은 테이프를 거쳐 그 대역이 둥글다.
이 파일이 두 가지를 각각 해결한다.
"""
import itertools
import numpy as np
from scipy import signal as sg

SR = 44100


# ════════════════════════════════════════════════════ 1. 화성 사전
def read_wav(path):
    """**wav 를 읽어 −1~1 실수로 돌려준다. 파일을 읽을 때는 반드시 이것을 쓴다.**

    `scipy.io.wavfile.read` 는 **파일에 적힌 자료형을 그대로** 돌려준다 —
    int16 · int32 · float32 셋 다 나온다. 그런데 이 프로젝트의 도구들은
    오랫동안 `/ 32768.0` 을 무조건 곱하고 있었다.

    **그 가정이 2026-08-12 에 깨졌다.** 그날 마스터를 float32 로 올렸더니
    `검증화성.py`·`화성검증.py`·`악장대조.py` 셋이 전부 **악장별 RMS 를
    −110 dB** 로 찍었다. 소리는 멀쩡했고 **읽는 쪽이 틀린 것**이다.

    **하루 전에 같은 실수를 하고 회고까지 썼다** — 2026-08-11 에 float32
    스템을 int16 으로 읽어 −118 dB 를 얻고 「스템이 비었나」로 갔다.
    적어놓기만 하고 **도구는 안 고쳤다.**

    > **그래서 함수로 만든다.** 규칙을 문서에 적으면 다음 스크립트가 또 틀린다.

    돌려주는 것 — `(표본율, 배열)`. 배열은 **float64 · −1~1**.
    """
    from scipy.io import wavfile
    sr, a = wavfile.read(path)
    if a.dtype.kind == "i":
        a = a.astype(np.float64) / float(np.iinfo(a.dtype).max)
    elif a.dtype.kind == "u":                     # 8비트 wav 는 부호 없음
        info = np.iinfo(a.dtype)
        a = (a.astype(np.float64) - info.max / 2.0) / (info.max / 2.0)
    else:
        a = a.astype(np.float64)                  # 이미 −1~1 실수다
    return sr, a


PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
      "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10,
      "Bb": 10, "B": 11}

Q = {
    "":        [0, 4, 7],
    "m":       [0, 3, 7],
    "dim":     [0, 3, 6],
    "7":       [0, 4, 7, 10],
    "m7":      [0, 3, 7, 10],
    "maj7":    [0, 4, 7, 11],
    "m7b5":    [0, 3, 6, 10],
    "dim7":    [0, 3, 6, 9],
    "6":       [0, 4, 7, 9],
    "m6":      [0, 3, 7, 9],
    "sus4":    [0, 5, 7],
    "7sus4":   [0, 5, 7, 10],
    "add9":    [0, 2, 4, 7],
    "madd9":   [0, 2, 3, 7],
    "maj9":    [0, 2, 4, 7, 11],
    "m9":      [0, 2, 3, 7, 10],
    "9":       [0, 2, 4, 7, 10],
    "7b9":     [0, 1, 4, 7, 10],
    "m11":     [0, 3, 5, 7, 10],
    # 플라멩코 프리지안 화음 — D F♯ A + E♭(♭9). 안달루시아 종지의 종착 화음
    "phr":     [0, 1, 4, 7],
}

# 화음 품질을 결정하는 음 = 5도를 뺀 나머지. 근음은 베이스가 맡으므로 선택.
def essential(degs):
    if len(degs) <= 3:
        return [d for d in degs if d != 7]
    return [d for d in degs if d not in (0, 7)]


def parse(sym):
    """'Ebmaj7/G' -> (근음 pc, 도수 리스트, 지정 베이스 pc 또는 None)"""
    slash = None
    if "/" in sym:
        sym, b = sym.split("/")
        i = 2 if len(b) > 1 and b[1] in "#b" else 1
        slash = PC[b[:i]]
    i = 2 if len(sym) > 1 and sym[1] in "#b" else 1
    root, qual = PC[sym[:i]], sym[i:]
    if qual not in Q:
        raise KeyError("알 수 없는 화음 품질: %r (%s)" % (qual, sym))
    return root, Q[qual], slash


def pcset(sym):
    r, d, _ = parse(sym)
    return sorted({(r + x) % 12 for x in d})


# ═══════════════════════════════════════ 2. 성부 진행 최적화
# 좋은 화성은 화음의 선택이 아니라 성부의 이동에서 나온다.
# 후보 보이싱을 모두 만들고 벌점이 가장 낮은 것을 고른다.

# par5_ok · par8_ok 는 **허용 구간에서 난 병행**이다 (BL-34 ①, 2026-08-11).
# 사고로 난 병행과 같은 칸에 넣으면 판정이 죽는다 — 「0건」이 통과 기준인데
# 허용분이 섞여 들어오면 그 기준이 아무것도 안 재게 된다.
#
# `lowtight_ok` 도 같다. **저역 밀집 기준(최저 두 성부가 4도 미만)도 건반
# 화성학에서 온 것**이고, 4악장에서 소리를 내는 것은 피아노가 아니라 **기타**다.
# 쓸어 치는 기타 화음은 원래 좁게 붙는다 — 열린 D 코드가 D A D F♯ 이다.
# 병행과 같은 이유로 같은 자리에서 갈라 센다.
STAT = {"chords": 0, "move": 0.0, "par5": 0, "par8": 0, "lowtight": 0, "leap": 0,
        "par5_ok": 0, "par8_ok": 0, "lowtight_ok": 0}


def _score(c, prev, ess_pc, third_pc, root_pc, par_pen=40.0, plane=0.0):
    s = 0.0
    # (a) 성부 간격 — 저역에서 좁은 간격은 뭉친다
    for i in range(len(c) - 1):
        g = c[i + 1] - c[i]
        if g < 3:
            s += 34.0                       # 저역·중역 불문 2도 이하 중첩 금지
        if c[i] < 56 and g < 5:
            s += 9.0 * (5 - g)              # C♯3 아래에서는 5도 이상 벌려야 한다
        if g > 12:
            s += 2.5 * (g - 12)             # 성부가 너무 벌어지면 화음이 안 들린다
    # (b) 품질음 누락
    pres = [x % 12 for x in c]
    for e in ess_pc:
        if e not in pres:
            s += 30.0
    # (c) 3도 중복 — 장·단 성격이 과하게 두꺼워진다
    if pres.count(third_pc) > 1:
        s += 11.0
    # (d) 최저 성부가 근음이면 베이스와 겹친다 (베이스는 독립 성부)
    if c[0] % 12 == root_pc:
        s += 3.0
    if prev is None:
        s += 0.35 * abs(c[-1] - 65)          # 첫 보이싱은 중역에서 시작
        return s
    # (e) 이동량 — 이것이 성부 진행의 본질
    s += 1.0 * sum(abs(a - b) for a, b in zip(c, prev))
    s += 1.3 * abs(c[-1] - prev[-1])         # 최상성부는 특히 매끄럽게
    # (f) 도약 억제
    for a, b in zip(c, prev):
        if abs(a - b) > 7:
            s += 2.2 * (abs(a - b) - 7)
    # (g) 외성 병행 5도·8도 — **금지에 가깝게 무겁다**
    #
    # 2026-08-08 까지 16.0 이었고 화음 349개에 0건이 나왔다. 그런데 그날
    # 1악장을 슬롯 경계에서 끊자 `prev` 가 달라지면서 **2악장 첫 화음에
    # 병행 8도가 하나 났다.** 이동량이 25.5점인 전환이라 병행을 피하는
    # 대안이 41.5점보다 비쌌던 것이다.
    #
    # **0건이 설계였던 것은 맞지만 여유가 없었다.** 16.0 은 "웬만하면
    # 피한다"이지 "하지 않는다"가 아니다. 이동량이 큰 전환에서는 뒤집힌다.
    # 40.0 이면 어지간한 이동량 차이로는 못 이긴다.
    #
    # **BL-34 ① (2026-08-11) — `par_pen` 으로 열었다. 기본값은 그대로다.**
    # 이 금지는 18세기 화성학 시험 채점 기준이고 **4악장에서는 틀렸다.**
    # 플라멩코 라스게아도는 병행 화음으로 움직이는 것이 어법인데, 이 벌점이
    # 그 악장을 스페인 음악이 아니게 만들고 있었다 (`08` 11.4절).
    #
    # **벌점을 빼는 것만으로는 안 된다 — 실측으로 확인했다.**
    # `par_pen=0` 만 주면 병행 5도는 **0건**이고 병행 8도 7건에 보이싱은
    # 화음 하나만 바뀐다. 총이동량은 오히려 6.43 → 6.48 로 는다.
    # 처음에 "공통음이 없으니 최소 이동이 곧 평행"이라고 봤는데 틀렸다 —
    # (e) 이동량과 (h) 공통음 보상이 만드는 최적해는 평행이 아니다.
    #
    # 그래서 `plane` 으로 **평행을 보상**한다. 아래 (g2) 를 볼 것.
    #
    # **음집합은 안 깨진다** — 후보(`cands`)가 애초에 그 화음의 화음음뿐이다.
    i0, i1 = (prev[-1] - prev[0]) % 12, (c[-1] - c[0]) % 12
    if i0 == i1 and i0 in (0, 7) and c[0] != prev[0]:
        s += par_pen
    # (g2) 평행 이동 보상 — 라스게아도 (BL-34 ①, 2026-08-11)
    #
    # **윗 성부들이 같은 간격으로 움직일 때 준다.** 기타가 왼손 모양을 유지한
    # 채 미끄러지는 것이고, 플라멩코 종지의 소리가 이것이다.
    #
    # **왜 「전부」가 아니라 「윗줄」인가** — 네 성부를 통째로 옮기면서 품질음을
    # 다 지키는 것이 이 진행에서는 **불가능**하다. Gm7·E♭maj7 이 7화음이라
    # 성질이 서로 다르기 때문이다(플라멩코 원형인 Am–G–F–E 는 전부 3화음이라
    # 통째로 옮겨진다). 실측으로 확인했다 — 「전부」로 걸면 평행이 0 이 되거나,
    # 품질음을 버려야 평행이 난다.
    #
    # 실제 라스게아도도 그렇다. **윗줄이 평행하게 미끄러지고 맨 아래는 따로**
    # 움직인다. 그래서 최저 성부를 풀어 주고, 그 성부가 빠질 뻔한 품질음을
    # 메우게 한다.
    #
    # **품질음이 다 있을 때만 준다.** 이 가드가 없으면 보상이 품질음 누락
    # 벌점(30)을 이겨서 **화음의 정체를 버리고 모양을 지킨다.** 2026-08-11
    # 첫 렌더가 그랬다 — 4악장 종지 Dphr 이 `[54,63,66,69]`(F♯ **E♭** F♯ A)
    # 에서 `[50,57,62,66]`(D A D F♯) 이 되면서 **프리지안 ♭2 인 E♭ 이
    # 빠졌다.** 그 음이 플라멩코 종지를 플라멩코로 만드는 음이다.
    # **음집합은 안 깨졌지만 화음의 성격이 깨졌다.**
    #
    # 후보가 화음음뿐이므로 **음집합 밖으로는 애초에 못 간다.**
    if plane > 0.0 and len(c) >= 3 and all(e in pres for e in ess_pc):
        d0 = c[1] - prev[1]
        if d0 != 0 and all(a - b == d0 for a, b in zip(c[1:], prev[1:])):
            s -= plane
    # (h) 공통음 유지 보상
    same = sum(1 for a in c if a in prev)
    s -= 1.6 * same
    return s


def voice_lead(sym, prev=None, lo=50, hi=71, nv=4, par_pen=40.0, plane=0.0):
    """par_pen — 외성 병행 5도·8도 벌점. **기본값을 넘기지 않으면 예전과 같다.**

    `par_pen=0.0` 은 그 화음에서 병행을 허용한다는 뜻이고, 그때 나는 병행은
    `STAT["par5_ok"]`·`par8_ok` 로 따로 센다 (BL-34 ①).

    plane — 네 성부가 **전부 같은 간격으로** 움직일 때 주는 보상. 라스게아도다.
    `par_pen` 을 푸는 것만으로는 평행이 안 나온다는 것을 실측으로 확인했다.
    """
    root, degs, _ = parse(sym)
    pcs = sorted({(root + d) % 12 for d in degs})
    ess = [(root + d) % 12 for d in essential(degs)]
    third = (root + (3 if 3 in degs else (5 if 5 in degs and 4 not in degs else 4))) % 12
    cands = [m for m in range(lo, hi + 1) if m % 12 in pcs]
    if len(cands) < nv:
        nv = len(cands)
    best, bs = None, 1e18
    for c in itertools.combinations(cands, nv):
        s = _score(list(c), prev, ess, third, root, par_pen, plane)
        if s < bs:
            bs, best = s, list(c)
    # 통계
    STAT["chords"] += 1
    if prev is not None and len(prev) == len(best):
        STAT["move"] += sum(abs(a - b) for a, b in zip(best, prev))
        i0, i1 = (prev[-1] - prev[0]) % 12, (best[-1] - best[0]) % 12
        if i0 == i1 and best[0] != prev[0]:
            ok = "_ok" if par_pen <= 0.0 else ""      # 허용 구간인가
            if i0 == 7:
                STAT["par5" + ok] += 1
            elif i0 == 0:
                STAT["par8" + ok] += 1
        for a, b in zip(best, prev):
            if abs(a - b) > 7:
                STAT["leap"] += 1
    tight = "lowtight_ok" if plane > 0.0 else "lowtight"
    for i in range(len(best) - 1):
        if best[i] < 56 and best[i + 1] - best[i] < 5:
            STAT[tight] += 1
    return best


# ═════════════════════════════════════════════ 3. 베이스 대선율 생성
# Jon Camp 방식 — 근음을 지키는 악기가 아니라 노래하는 악기.
# 화음음 사이를 8분음표로 걷고, 화음이 바뀌기 직전에 다음 근음으로 계단식 접근한다.

def _near(pc, ref, lo, hi):
    best, bd = None, 999
    for m in range(lo, hi + 1):
        if m % 12 == pc % 12 and abs(m - ref) < bd:
            bd, best = abs(m - ref), m
    return best if best is not None else int(np.clip(ref, lo, hi))


def _step(cur, tgt, scale, lo, hi):
    d = 1 if tgt > cur else -1
    m = cur + d
    for _ in range(4):
        if lo <= m <= hi and m % 12 in scale:
            return m
        m += d
    return int(np.clip(tgt, lo, hi))


def bassline(prog, scale, eighth, lo=28, hi=53, rng=None, leap_p=0.14,
             density=2.0, accent_every=4):
    """prog = [(sym, beats)]. 반환 [(midi, dur, vel_scale, is_accent)] 와 총 시간."""
    rng = rng or np.random.default_rng(7)
    out, t, cur = [], 0.0, None
    for i, (sym, beats) in enumerate(prog):
        root, degs, slash = parse(sym)
        ct = sorted({(root + d) % 12 for d in degs if d in (0, 3, 4, 7, 10, 11, 9)})
        nroot = parse(prog[(i + 1) % len(prog)][0])[0]
        n = max(1, int(round(beats * density)))
        # 화음의 첫 음 — 근음·3음·5음을 돌아가며 짚는다 (전위가 자연히 생긴다)
        pick = [0, degs[1], 7, 0][i % 4]
        if slash is not None:
            pick = (slash - root) % 12
        seq = [_near(root + pick, cur if cur is not None else 41, lo, hi)]
        tgt = _near(nroot, seq[-1], lo, hi)
        for k in range(1, n):
            if k >= n - max(1, n // 3):                 # 후반 — 다음 화음으로 접근
                seq.append(_step(seq[-1], tgt, scale, lo, hi))
            elif rng.random() < leap_p:                 # 옥타브 도약
                m = seq[-1] + (12 if seq[-1] < 40 else -12)
                seq.append(m if lo <= m <= hi else seq[-1])
            else:                                       # 화음음 사이를 오간다
                pool = [m for m in range(lo, hi + 1)
                        if m % 12 in ct and 2 <= abs(m - seq[-1]) <= 9]
                seq.append(int(rng.choice(pool)) if pool else
                           _step(seq[-1], tgt, scale, lo, hi))
        d = beats * eighth / n                          # 총 beats*eighth 를 n등분
        for k, m in enumerate(seq):
            out.append((m, d, 1.0 if k % accent_every == 0 else 0.72, k == 0))
            cur = m
        t += beats * eighth
    return out, t


# ═════════════════════════════════ 4. 테이프 새추레이션 · 콘솔 워머 (BL-24)
def _sos(fc, kind, order=2):
    return sg.butter(order, min(fc, 0.45 * SR) / (SR / 2), btype=kind, output="sos")


def tape(x, drive=1.35, bias=0.055, pre=0.60, bump=0.11, gap=13500):
    """아날로그 테이프 녹음 경로.
    프리엠퍼시스 → 비대칭 포화 → 디엠퍼시스 → 헤드 범프 → 갭 손실.
    비대칭(bias)이 2차 배음을 만들고, 그것이 '따뜻함'으로 들린다.
    """
    hp = _sos(3000, "high", 1)
    y = x + pre * sg.sosfilt(hp, x)
    y = (np.tanh(drive * (y + bias)) - np.tanh(drive * bias)) / np.tanh(drive)
    y = y - (pre * 0.52) * sg.sosfilt(hp, y)
    y = y + bump * sg.sosfilt(_sos(95, "low"), y)
    y = sg.sosfilt(_sos(gap, "low", 1), y)
    return y


def deharsh(x, fc=2750.0, q=1.15, db=-2.6):
    """2~4kHz의 디지털 경직됨을 눌러준다. 합성 음원이 '조잡하게' 들리는 대역."""
    b, a = sg.iirpeak(fc / (SR / 2), q)
    g = 10 ** (db / 20.0) - 1.0
    return x + g * sg.lfilter(b, a, x)


def shelf(x, fc, db, kind="high"):
    g = 10 ** (db / 20.0)
    return x + np.float32(g - 1.0) * sg.sosfilt(_sos(fc, kind), x).astype(x.dtype)


def plate(x, seed=0, rt60=2.0, damp=7600, hp=190, pre=0.014):
    """플레이트 잔향 (BL-29) — 초기 반사 없이 처음부터 조밀하고, 길게 남는다.

    `room()`은 7탭 × 6반복으로 홀의 **뚜렷한 초기 반사**를 흉내낸다. 탭이 하나씩
    들리는 것이 홀의 성질이기 때문이다. 플레이트는 반대다 — 금속판의 굽힘파가
    사방으로 퍼지므로 **처음부터 뭉개져 있고 탭이 들리지 않는다.**

    그래서 탭을 세는 방식으로는 만들 수 없다. **감쇠하는 잡음을 임펄스 응답으로
    삼아 합성곱**한다. 잡음이 곧 최대 밀도이고, 지수 감쇠가 꼬리 길이를 정한다.
    (탭 방식으로 같은 밀도를 내려면 수백 번 더해야 하고 그만큼 느리다.)

    `rt60` = 꼬리가 −60 dB로 줄기까지의 초. 1970년대 EMT 플레이트가 2초 안팎이었고
    그것이 그 시절 보컬이 "앞에 떠 있게" 들린 이유다. 고역도 룸보다 늦게 깎는다
    (7.6kHz 대 4.2kHz) — 플레이트는 밝다.
    """
    rng = np.random.default_rng(7311 + seed)
    n = ns(rt60 * 1.15)
    t = np.arange(n) / SR
    ir = (rng.standard_normal(n) * np.exp(-6.91 * t / rt60)).astype(np.float32)
    ir = sg.sosfilt(_sos(damp, "low"), ir).astype(np.float32)
    ir = sg.sosfilt(_sos(hp, "high"), ir).astype(np.float32)
    ir[:ns(0.001)] = 0.0                       # 직접음은 없다 — 센드로만 쓴다
    e = float(np.sqrt(np.dot(ir, ir)))
    ir /= np.float32(e if e > 0 else 1.0)
    y = sg.oaconvolve(x, ir)[:len(x)].astype(np.float32)
    p = ns(pre)                                # 프리딜레이 — 원음과 꼬리를 떼어놓는다
    if p:
        y[p:] = y[:-p]
        y[:p] = 0.0
    return y


def send_env(spec, k, ramp=2.0):
    """센드량을 시간에 따라 바꾸는 포락선을 만든다 (BL-32).

    spec = [(시각초, 값), ...]. 값은 다음 지점까지 유지되고, 경계에서
    `ramp` 초에 걸쳐 선형으로 건너간다. 첫 지점 이전은 첫 값으로 채운다.

    **왜 필요한가** — `07. 작곡 계획` 11장이 세운 설계는 성부마다가 아니라
    **악장마다** 다르다. 4악장의 그녀는 2005년에 실제로 촬영된 무희이고
    (V3 가 못박은 유일한 실재의 악장), 7악장에서 상상으로 넘어간다.
    그러니 같은 무그라도 4악장에서는 마르고 7악장에서는 젖어야 한다.
    **잔향이 그녀가 얼마나 실재하는지를 재는 눈금이 된다.**

    **왜 잔향 앞에 곱하는가** — 이것은 콘솔의 센드 페이더를 움직이는 것과 같다.
    잔향 뒤에 곱하면 경계에서 꼬리가 잘린다. 앞에 곱하면 4악장에서 울린 소리의
    꼬리는 그대로 남은 채 새로 들어오는 소리만 젖기 시작한다 — 그게 자연스럽다.

    `room`·`plate` 는 둘 다 선형이므로 **상수 spec 은 예전 `amt * f(x)` 와
    수학적으로 같다.** 즉 이 기능을 더해도 기존 소리가 바뀌지 않는다.
    """
    env = np.zeros(k, dtype=np.float32)
    pts = sorted(spec, key=lambda p: p[0])
    r = max(1, ns(ramp))
    prev_v = float(pts[0][1])
    i0 = 0
    for t, v in pts:
        i = min(k, max(0, ns(t)))
        if i > i0:
            env[i0:i] = prev_v
        v = float(v)
        if v != prev_v and i < k:                  # 경계를 선형으로 건넌다
            j = min(k, i + r)
            env[i:j] = np.linspace(prev_v, v, j - i, dtype=np.float32)
            i0 = j
        else:
            i0 = i
        prev_v = v
    if i0 < k:
        env[i0:] = prev_v
    return env


def room(x, seed=0):
    """홀 잔향. 9분 40초 × float64 는 메모리를 잡아먹으므로 float32 · 제자리 연산."""
    rng = np.random.default_rng(90210 + seed)
    y = np.zeros(len(x), dtype=np.float32)
    for dl, g in [(0.0193, .50), (0.0291, .42), (0.0411, .34),
                  (0.0623, .27), (0.0891, .21), (0.1277, .15), (0.1811, .10)]:
        d = ns(dl * (1 + 0.02 * rng.standard_normal()))
        for kk in range(1, 7):
            s = d * kk
            if s >= len(x):
                break
            y[s:] += np.float32(g * 0.60 ** kk) * x[:-s]
    y = sg.sosfilt(_sos(4200, "low"), y).astype(np.float32)
    y = sg.sosfilt(_sos(160, "high"), y).astype(np.float32)
    return y * np.float32(0.5)


# ═════════════════════════════════════════════════ 5. 스템 버스 타임라인
def ns(s):
    return int(round(s * SR))


class _Send:
    """스템 이름 하나에 대한 입력구. 실제 저장은 Desk의 단일 스테레오 버퍼."""

    def __init__(self, desk, name):
        self.d, self.n = desk, name

    def put(self, sig, at, gain=1.0, pan=0.0):
        self.d._put(self.n, sig, at, gain, pan)


class Desk:
    """스템별 스테레오 버퍼에 담았다가 믹스 시점에 합산한다 (BL-29).

    `stems=False`면 옛 경로 — 단일 스테레오 버퍼에 즉시 합산한다. 2코어·3.9GB
    샌드박스에서는 7스템(1.35 GB)을 따로 들 수 없어 그것이 유일한 선택이었다.
    **옛 경로를 지우지 않는다** — 실패로 판정되면 되돌릴 수 있어야 한다.

    스템을 나누면 세 가지가 풀린다.
      · 성부마다 다른 잔향 — 보컬에만 플레이트를 걸 수 있다
      · 페이더를 믹스 시점에 정한다 (`mix(gains=)`)
      · 스템을 디스크에 내려두면 렌더 없이 믹스만 반복할 수 있다
    스템별 에너지(`self.e`)는 두 경로 모두 페이더 전 제곱합으로 누적한다.
    """

    def __init__(self, sec, names, gains=None, stems=True):
        n = ns(sec) + SR * 8
        self.names = list(names)
        self.g = {k: 10 ** (v / 20.0) for k, v in (gains or {}).items()}
        self.e = {k: 0.0 for k in names}
        self.s = {k: _Send(self, k) for k in names}
        self.stems = bool(stems)
        self._n = n
        if self.stems:
            self.B = {k: [np.zeros(n, dtype=np.float32),
                          np.zeros(n, dtype=np.float32)] for k in self.names}
            self.L = self.R = None
        else:
            self.B = None
            self.L = np.zeros(n, dtype=np.float32)
            self.R = np.zeros(n, dtype=np.float32)

    def __getitem__(self, k):
        return self.s[k]

    def _grow(self, need):
        """길이를 늘린다. 스템 모드에서는 **전부 같이** 늘려야 길이가 어긋나지 않는다."""
        if need <= self._n:
            return
        p = need - self._n + 1
        if self.stems:
            for k in self.names:
                b = self.B[k]
                b[0] = np.pad(b[0], (0, p))
                b[1] = np.pad(b[1], (0, p))
        else:
            self.L = np.pad(self.L, (0, p))
            self.R = np.pad(self.R, (0, p))
        self._n += p

    def _put(self, name, sig, at, gain, pan):
        i = ns(max(0.0, at))
        j = i + len(sig)
        self._grow(j)
        self.e[name] += float(np.dot(sig, sig)) * (gain ** 2)   # 페이더 전 에너지
        s32 = sig.astype(np.float32, copy=False)
        if self.stems:
            # 페이더(self.g)는 여기서 곱하지 않는다 — 믹스 시점으로 옮겼다
            gl = np.float32(np.cos((pan + 1) * np.pi / 4) * 1.414 * gain)
            gr = np.float32(np.sin((pan + 1) * np.pi / 4) * 1.414 * gain)
            b = self.B[name]
            b[0][i:j] += s32 * gl
            b[1][i:j] += s32 * gr
        else:
            g = gain * self.g.get(name, 1.0)
            gl = np.float32(np.cos((pan + 1) * np.pi / 4) * 1.414 * g)
            gr = np.float32(np.sin((pan + 1) * np.pi / 4) * 1.414 * g)
            self.L[i:j] += s32 * gl
            self.R[i:j] += s32 * gr

    def stem_rms(self, trim, check=False):
        """페이더 전 RMS. `check=True`면 스템 버퍼에서 직접 잰 값과 대조해 출력한다.

        **두 값은 원래 조금 다르다.** 누적치(`self.e`)는 음마다 제곱합을 더한 것이고
        버퍼 실측은 겹쳐 울린 결과를 잰 것이라, 음이 겹치면 `(a+b)² ≠ a² + b²` 이다.
        그래서 겹침이 많은 스템(피아노·오르간)일수록 차가 크고, 겹침이 적은 스템
        (베이스·리드)은 0에 가깝다 — **차이의 크기가 아니라 그 분포가 정상 신호다.**

        판정은 **±0.5 dB**로 본다. 그보다 크면 `_put`이 잘못된 것이다.
        """
        k = ns(trim)
        out = {n: float(np.sqrt(v / k)) for n, v in self.e.items()}
        if check and self.stems:
            print("\n[스템 RMS 대조 · 제곱합 누적 vs 버퍼 실측]")
            print("  겹친 음이 많을수록 차가 커진다. ±0.5 dB 안이면 정상")
            for n in self.names:
                bl, br = self.B[n]
                # 팬 법칙(cos/sin × 1.414)이 좌우 합의 제곱합을 보존한다
                m = float(np.sqrt((np.dot(bl[:k], bl[:k]) +
                                   np.dot(br[:k], br[:k])) / 2.0 / k))
                d = 20 * np.log10(max(m, 1e-12) / max(out[n], 1e-12))
                print("  %-5s 누적 %.6f   버퍼 %.6f   차 %+.3f dB%s"
                      % (n, out[n], m, d, "" if abs(d) < 0.5 else "   ← 어긋남"))
        return out

    # ── 스템 입출력 (BL-29 단계 3) ────────────────────────────────
    # 페이더를 곱하기 **전** 상태로 내린다. 그래야 믹스.py 에서 페이더를 바꿀 수 있다.
    # float32 로 쓴다 — 16비트로 내리면 양자화 때문에 동일성 검증이 깨진다.
    STEM_FMT = "스템-%s.wav"

    def save_stems(self, path, trim):
        """스템을 wav 로 내린다. **`mix()` 전에 불러야 한다** — mix 가 버퍼를 놓아준다."""
        import os
        from scipy.io import wavfile
        if not self.stems:
            raise ValueError("stems=False 에서는 내릴 스템이 없다")
        os.makedirs(path, exist_ok=True)
        k = ns(trim)
        tot = 0
        for n in self.names:
            b = self.B[n]
            a = np.stack([b[0][:k], b[1][:k]], axis=1)
            f = os.path.join(path, self.STEM_FMT % n)
            wavfile.write(f, SR, a)
            tot += os.path.getsize(f)
        print("[스템 저장] %s  %d개  %.2f GB" % (path, len(self.names), tot / 2 ** 30))

    @classmethod
    def load_stems(cls, path, names, gains=None):
        """내려둔 스템으로 Desk 를 되살린다. 렌더 없이 믹스만 다시 할 수 있다."""
        import os
        from scipy.io import wavfile
        names = list(names)
        d = cls(1.0, names, gains, stems=True)      # 껍데기만 만들고 버퍼를 갈아 끼운다
        n0 = None
        for n in names:
            sr, a = wavfile.read(os.path.join(path, cls.STEM_FMT % n))
            if sr != SR:
                raise ValueError("%s: 표본율 %d ≠ %d" % (n, sr, SR))
            a = np.ascontiguousarray(a, dtype=np.float32)
            if n0 is None:
                n0 = len(a)
            elif len(a) != n0:
                raise ValueError("%s: 길이 %d ≠ %d — 스템 세트가 섞였다" % (n, len(a), n0))
            d.B[n] = [np.ascontiguousarray(a[:, 0]), np.ascontiguousarray(a[:, 1])]
        d._n = n0
        return d

    def mix(self, trim, gains=None, reverb=None, sends=None, peak=0.89):
        """sends = {스템: (종류, 양)}. 종류는 "room" 또는 "plate".

        **주지 않으면 지금까지처럼 합에 한 번만 건다.** 센드를 받은 스템은
        전역 홀에서 빠지고 자기 잔향만 받는다 — 그래야 공간이 섞이지 않는다.
        """
        k = ns(trim)
        rv = reverb if reverb is not None else 0.15
        sends = sends or {}
        if sends and not self.stems:
            raise ValueError("성부별 센드는 stems=True 에서만 쓸 수 있다")
        wL = wR = None
        if self.stems:
            # 페이더를 여기서 곱한다. gains 를 주면 렌더 없이 덮어쓸 수 있다
            gg = dict(self.g)
            if gains:
                gg.update({n: 10 ** (v / 20.0) for n, v in gains.items()})
            L = np.zeros(k, dtype=np.float32)
            R = np.zeros(k, dtype=np.float32)
            # 전역 홀로 보낼 몫 — 센드를 받은 스템은 여기서 빠진다
            gL = L if not sends else np.zeros(k, dtype=np.float32)
            gR = R if not sends else np.zeros(k, dtype=np.float32)
            for n in self.names:                    # 순서 고정 — 누산 순서가 재현돼야 한다
                b = self.B[n]
                g = np.float32(gg.get(n, 1.0))
                dl = b[0][:k] * g
                dr = b[1][:k] * g
                L += dl
                R += dr
                if n in sends:
                    kind, amt = sends[n]
                    f = plate if kind == "plate" else room
                    if wL is None:
                        wL = np.zeros(k, dtype=np.float32)
                        wR = np.zeros(k, dtype=np.float32)
                    if np.isscalar(amt):            # 곡 전체에 같은 양
                        wL += np.float32(amt) * f(dl, 0)
                        wR += np.float32(amt) * f(dr, 1)
                    else:                           # BL-32 — 악장마다 다른 양
                        env = send_env(amt, k)
                        wL += f(dl * env, 0)
                        wR += f(dr * env, 1)
                        del env
                elif sends:
                    gL += dl
                    gR += dr
                self.B[n] = None                    # 다 쓴 스템은 즉시 놓아준다
                del dl, dr
            self.B = None
        else:
            L = np.ascontiguousarray(self.L[:k])
            R = np.ascontiguousarray(self.R[:k])
            gL, gR = L, R
            self.L = self.R = None
        # 전역 홀
        L += np.float32(rv) * room(gL, 0)
        R += np.float32(rv) * room(gR, 1)
        if sends:
            del gL, gR
        if wL is not None:                          # 성부별 센드
            L += wL
            R += wR
            del wL, wR
        # 콘솔 EQ — 예전 체계의 +6 dB 프레즌스를 버린다. 그것이 경직됨의 원인이었다.
        def eq(x):
            x = sg.sosfilt(_sos(28, "high"), x).astype(np.float32)
            x = shelf(x, 62, -2.2, "low")
            b1, a1 = sg.iirpeak(330 / (SR / 2), 1.1)
            x -= np.float32(0.14) * sg.lfilter(b1, a1, x).astype(np.float32)
            x = deharsh(x).astype(np.float32)         # 2~4kHz 경직됨 완화
            x = shelf(x, 4200, 2.4, "high")           # 프레즌스는 위쪽에서 조금만
            x = shelf(x, 9500, 2.0, "high")           # 에어
            return x.astype(np.float32)
        L, R = eq(L), eq(R)
        # 미드/사이드 — 저역은 중앙 유지
        M = (L + R) * np.float32(0.5)
        S = (L - R) * np.float32(0.5)
        S = sg.sosfilt(_sos(220, "high"), S).astype(np.float32) * np.float32(1.65)
        L, R = M + S, M - S
        del M, S
        # 글루 컴프 (2:1, 느린 릴리스)
        det = np.maximum(np.abs(L), np.abs(R))
        blk = 128
        nb = len(det) // blk
        pk = det[:nb * blk].reshape(nb, blk).max(axis=1)
        del det
        e, env = 0.0, np.zeros(nb)
        ac, rc = np.exp(-1 / (0.012 * SR / blk)), np.exp(-1 / (0.28 * SR / blk))
        for i, p in enumerate(pk):
            c = ac if p > e else rc
            e = c * e + (1 - c) * p
            env[i] = e
        thr = float(np.percentile(env, 72)) or 0.3
        g = np.maximum(np.interp(np.arange(len(L)), np.arange(nb) * blk, env) / thr,
                       1.0).astype(np.float32) ** np.float32(-0.5)
        L *= g
        R *= g
        del g, env, pk
        # 테이프
        m0 = np.float32(max(np.abs(L).max(), np.abs(R).max(), 1e-9) / 0.72)
        L, R = tape(L / m0).astype(np.float32), tape(R / m0).astype(np.float32)
        m = max(np.abs(L).max(), np.abs(R).max(), 1e-9)
        return np.stack([L / m * peak, R / m * peak], axis=1)


# ═══════════════════════════════════════════════════════ 6. 캐시 래퍼
import piano
import ensemble as ens
import synth

# 인간화(humanize)가 세기를 연속적으로 흔들면 캐시 키가 매번 달라져 메모리가 터진다.
# 지속시간·세기를 양자화해 캐시가 실제로 맞아떨어지게 하고, 상한을 두어 비운다.
def q(x, step):
    return round(round(float(x) / step) * step, 4)


def _cap(dct, n):
    if len(dct) > n:
        dct.clear()


_RC, _HC, _MC, _DC = {}, {}, {}, {}


def pn(m, dur, vel=0.7, ring=1.0):
    """피아노 — 양자화 + float32 캐시"""
    _cap(piano._CACHE, 420)
    y = piano.note(int(m), q(dur, 0.02), q(vel, 0.05), q(ring, 0.15))
    if y.dtype != np.float32:
        y = y.astype(np.float32)
        piano._CACHE[(int(m), round(q(dur, 0.02), 3), round(q(vel, 0.05), 2),
                      round(q(ring, 0.15), 2))] = y
    return y


def st(m, dur, vel=0.3, **kw):
    _cap(ens._SCACHE, 140)
    return ens.strings(int(m), q(dur, 0.05), vel=q(vel, 0.04), **kw)


def ny(m, dur, vel=0.6, **kw):
    _cap(ens._GCACHE, 260)
    if "ring" in kw:
        kw["ring"] = q(kw["ring"], 0.1)
    return ens.nylon(int(m), q(dur, 0.03), vel=q(vel, 0.05), **kw)


def fla(m, dur, vel=0.6, **kw):
    """플라멩코 기타 캐시 래퍼. `ny` 와 같은 규칙이다 (BL-30 — 씨앗 고정)."""
    _cap(ens._GCACHE, 260)
    if "ring" in kw:
        kw["ring"] = q(kw["ring"], 0.1)
    return ens.flamenco(int(m), q(dur, 0.03), vel=q(vel, 0.05), **kw)


def rick(m, d, vel=0.75, ring=0.55):
    _cap(_RC, 320)
    k = (int(m), q(d, 0.03), q(vel, 0.05), q(ring, 0.15))
    if k not in _RC:
        _RC[k] = ens.rick(int(m), k[1], vel=k[2], ring=k[3]).astype(np.float32)
    return _RC[k]


def _seed(k):
    """캐시 키에서 재현 가능한 씨앗을 만든다 (BL-30).

    파이썬의 `hash()`는 문자열 해시 무작위화 때문에 **실행마다 달라진다.**
    그래서 쓰지 않고 값에서 직접 접는다 — 같은 소리는 언제나 같은 잡음을 받는다.
    """
    v = 20260807
    for x in k:
        v = (v * 1000003 + (int(x * 1000) if isinstance(x, float)
                            else int(x) if isinstance(x, (int, bool))
                            else 0)) & 0x7FFFFFFF
    return v


def hamm(m, d, reg, gain=1.0):
    _cap(_HC, 320)
    # BL-30 — 옛 키는 `id(reg)`를 썼다. 메모리 주소라 실행마다 달라지고
    # 씨앗을 뽑을 수도 없다. 값(tuple)으로 바꾼다
    k = (int(m), q(d, 0.03), tuple(reg), q(gain, 0.05))
    if k not in _HC:
        _HC[k] = synth.hammond(int(m), k[1], reg=reg, gain=k[3], drive=1.7,
                               click=0.28,
                               seed=_seed((k[0], k[1], k[3]))).astype(np.float32)
    return _HC[k]


def moog(m, d, gain=1.0, cut=4200, res=0.34, glide=None, vib=0.0, scream=0.0):
    """vib · scream 은 WBS 1.4.8 에서 열었다. 기본값 0 이므로 기존 호출은 그대로다.

    **캐시 키에 반드시 넣는다.** 안 넣으면 같은 음높이·길이의 벨팅과 평음이
    같은 파형을 돌려받아, 비브라토를 걸어도 소리가 안 바뀐다.
    """
    _cap(_MC, 260)
    k = (int(m), q(d, 0.03), q(gain, 0.05), int(cut / 200) * 200, q(res, 0.05), glide,
         q(vib, 0.05), q(scream, 0.05))
    if k not in _MC:
        y = synth.moog(int(m), k[1], gain=k[2], cut_hi=k[3], res=k[4],
                       glide_from=glide, vib=k[6], scream=k[7], seed=_seed(k[:5]))
        # 무그의 톱니 상단을 접어 경직됨을 없앤다 — 1970년대 라더 필터는 이보다 훨씬 둔했다
        _MC[k] = sg.sosfilt(_sos(7200, "low", 2), y).astype(np.float32)
    return _MC[k]


# ═══════════════════════════════════════ 드럼 (WBS 1.1.6)
# 다른 악기와 같은 규칙을 따른다 — 캐시 상한, 세기 양자화, 씨앗 고정.
# BL-31 에서 `synth.py` 의 무씨앗 난수를 전부 끊었으므로 여기서 씨앗을 준다.

def drum(kind, gain=1.0, seed=0, midi=48):
    """kick · snare · hat · hato(열린 하이햇) · tom · crash.

    `seed` 는 **타수**를 넣는다. 같은 타격이 매번 똑같이 들리면 기계가 되고,
    씨앗 없이 두면 렌더마다 달라진다(T-06). 타수를 넣으면 **곡 안에서는
    매번 다르고 렌더 사이에서는 같다** — 이 프로젝트가 원하는 성질이다.
    """
    _cap(_DC, 420)
    if ":" in kind:                       # "tom:45" — 음높이를 실어 보낸다
        kind, midi = kind.split(":", 1)
        midi = int(midi)
    k = (kind, q(gain, 0.04), int(seed) % 64, int(midi) if kind == "tom" else 0)
    if k not in _DC:
        g = k[1]
        s = k[2]
        if kind == "kick":
            y = synth.kick(gain=g, seed=s)
        elif kind == "snare":
            y = synth.snare(gain=g, seed=s)
        elif kind == "rim":
            y = synth.rim(gain=g, seed=s)
        elif kind == "hat":
            y = synth.hat(open_=False, gain=g, seed=s)
        elif kind == "hato":
            y = synth.hat(open_=True, gain=g, seed=s)
        elif kind == "tom":
            y = synth.tom(midi=k[3], gain=g, seed=s)
        elif kind == "crash":
            y = synth.crash(gain=g, seed=s)
        else:
            raise ValueError("모르는 드럼 %r" % kind)
        _DC[k] = y.astype(np.float32)
    return _DC[k]


# 패턴 — `07. 작곡 계획` 16장이 정본이다. 여기에는 격자만 둔다.
#
# 값은 (박 위치, 악기, 세기). 위치는 **박 단위**이고 소수를 쓸 수 있다.
# 하이햇을 4분음표로 두는 것이 이 곡의 핵심이다 — 베이스가 이미 8분음표라
# 하이햇까지 8분이면 같은 격자를 두 번 말하고 마디가 아니라 질감만 는다.

# ── 설리반의 어법을 우리 박자로 옮긴다 (2026-08-08, 검수자 제공 드럼 탭) ──
#
# 그의 패턴은 전부 4/4 다. 우리는 5/4+6/4 이므로 **자리를 그대로 못 옮기고
# 기법을 번역**한다. 옮긴 것 다섯.
#
#   ① 고스트 노트 — `- - O - - g O -`. 본타 앞에 아주 약한 타를 붙인다.
#      **정박만 때리면 기계가 된다.** 쿵짝쿵짝의 진짜 원인이 이것의 부재였다.
#   ② 싱코페이션 킥 — 그의 표에 "3박 후반이 포인트"라고 적혀 있다.
#      우리 5박·6박에서는 **마디 중간의 뒷박**이 그 자리다.
#   ③ 마디 끝 오픈 하이햇 — 그는 거의 매 마디 끝에 `o` 를 둔다. 숨이다.
#   ④ 탐 필은 16분 `O o` 쌍 — 강·약이 붙어 굴러 내려간다. 단타 넷이 아니다.
#   ⑤ 플램 — 본타 직전 25ms 에 약한 타를 겹친다.
#
# 라이드 벨(RB)과 크래시 연타는 아직이다. 라이드는 소리가 없고, 크래시는
# 9악장에만 넣었다. 도시 악장이 작곡될 때 `p ↔ ff` 대비와 함께 정한다.


def pat_promenade(nb, n):
    """5/4(nb=5) 또는 6/4(nb=6). n 은 몇 번째 마디인가.

    프롬나드는 절제된 구간이므로 스네어가 아니라 **사이드 스틱**이다.
    킥→림샷 3박은 고정이고 그 뒤가 2박·3박을 오간다(`07` 16.2절).
    """
    p = [(0, "kick", 1.00)]
    rb = min(3, nb - 1)                   # 3박 마디(2악장)에서는 2박에 온다
    # ② 싱코페이션 킥 — 마디 중간의 뒷박. 정박에만 있으면 행진이 된다
    if nb > 3:
        p.append((2.5, "kick", 0.55 if n % 2 == 0 else 0.44))
    # ① 고스트 — 본타 바로 앞. 아주 약하게
    p.append((rb - 0.25, "rim", 0.20))
    p.append((rb, "rim", 0.66))
    if n % 4 == 2:
        p.append((nb - 1.5, "kick", 0.60))
    if n % 4 == 3:                        # ⑤ 플램으로 다음 마디에 넘긴다
        p.append((nb - 1 - 0.025, "rim", 0.26))
        p.append((nb - 1, "rim", 0.48))
    for b in range(nb):
        p.append((b, "hat", 0.36 if b == 0 else (0.26 if b == rb else 0.18)))
    # ③ 마디 끝 오픈 하이햇 — 두 마디에 한 번. 숨이다
    if n % 2 == 1:
        p.append((nb - 0.5, "hato", 0.24))
    return p


def pat_finale(n):
    """9악장 총주. 고조된 자리이므로 **오픈 스네어**다.

    설리반이 탐탐을 팀파니처럼 쓰는 것이 여기다 — "리듬 머신이 아니라
    오케스트라 타악기 파트"라는 말의 뜻.
    """
    p = [(0, "kick", 1.00), (2, "kick", 0.88)]
    p.append((2.75, "kick", 0.50))                    # ② 싱코페이션
    p.append((0.75, "snare", 0.22))                   # ① 고스트
    p.append((1, "snare", 0.84))
    p.append((2.75, "snare", 0.20))                   # ① 고스트
    p.append((3, "snare", 0.84))
    p += [(b, "hat", 0.34 if b == 0 else 0.22) for b in range(4)]
    if n % 2 == 1:
        p.append((3.5, "hato", 0.24))                 # ③
    # **주기는 악장 길이에 맞춘다.** 9악장은 드럼이 놓이는 마디가 11개뿐이라
    # 8마디 주기면 탐 롤이 한 번밖에 안 온다. 4마디로 좁혀 세 번 오게 한다.
    if n % 8 == 0:
        p.append((0, "crash", 0.62 if n == 0 else 0.44))
    if n % 4 == 3:
        # ④ 16분 `O o` 쌍으로 굴러 내려간다. 단타 넷이 아니다
        p += [(2.00, "snare", 0.62), (2.25, "snare", 0.26),
              (2.50, "tom:50", 0.66), (2.75, "tom:50", 0.28),
              (3.00, "tom:45", 0.72), (3.25, "tom:45", 0.30),
              (3.50, "tom:40", 0.78), (3.75, "tom:40", 0.34)]
    elif n % 2 == 1:
        p += [(3.5 - 0.025, "snare", 0.28), (3.5, "snare", 0.56)]   # ⑤ 플램
    return p


PAT_4S = ([(0, "kick", 1.00), (1, "snare", 0.86),
           (2, "kick", 0.92), (3, "snare", 0.86)] +
          [(b, "hat", 0.30) for b in range(4)])         # 9악장 — 하이햇 4분음표
# 7/8 은 **8분음표 단위**로 센다 (2+2+3). 여기서만 하이햇이 8분이다.
PAT_78 = ([(0, "kick", 1.00), (2, "kick", 0.90), (4, "snare", 0.92)] +
          [(b, "hat", 0.32) for b in range(7)])


def pat_break(n, role):
    """**막드럼을 쓰지 않는다.** 아래 새 판을 쓴다 — 옛 판은 지우지 않고 남긴다."""
    return pat_break_kbkick(n, role)


def pat_break_kbkick(n, role):
    """8악장 — **금속과 나무만.** 킥·스네어·탐은 건반이 대신한다.

    2026-08-08 청취 판정 — **"드럼 북 때문에 지저분하다. 웅장함을 가장한
    지저분함. 차라리 건반을 킥으로 쓰는 것이 낫겠다."** 맞는 지적이었다.

    이 곡의 소리는 전부 음정을 갖는다 — 피아노·오르간·베이스·기타·무그·현악.
    그리고 곡의 중심 아이디어가 **단 하나의 음집합**이다. 그런데 킥과 탐은
    음정이 없는 막이라 **그 세계 밖에 혼자 있었다.** 게다가 우리 것은 녹음된
    키트가 아니라 사인 스윕 + 잡음이라, 밀도가 오르면 웅장해지는 게 아니라
    뭉갠다.

    그래서 남기는 것은 **금속(하이햇·크래시)과 나무(림샷)** 뿐이다. 둘 다
    음정이 없지만 **공기와 어택**이라 화성을 가리지 않는다. 저역과 중역의
    타격은 `전곡화성.py` 가 피아노 저역으로 낸다 — 그것이 음정 있는 킥이다.
    """
    g = [0, 2, 4]
    if role == "drum":
        p = [(1, "rim", 0.42), (3, "rim", 0.46), (5, "rim", 0.72), (6, "rim", 0.34)]
        p += [(b, "hat", 0.40 if b in g else 0.26) for b in range(7)]
        if n % 4 == 3:
            p += [(4.5, "rim", 0.30), (5.5, "rim", 0.34), (6.5, "rim", 0.38)]
        return p
    if role == "tutti":
        p = [(4, "rim", 0.62), (3.75, "rim", 0.22)]
        p += [(b, "hat", 0.42 if b in g else 0.28) for b in range(7)]
        if n % 4 == 0:
            p.append((0, "crash", 0.52))
        return p
    p = [(4, "rim", 0.48), (3.75, "rim", 0.16)]
    p += [(b, "hat", 0.30 if b in g else 0.18) for b in range(7)]
    return p


def pat_break_membrane(n, role):
    """옛 판 — 킥·스네어·탐을 쓴다. **2026-08-08 청취 판정에서 탈락했다.**

    지우지 않는 이유는 R3 와 같다. 되돌릴 수 있어야 한다.
    """
    """8악장 인스트루멘털 브레이크의 7/8 (2+2+3). `role` 이 주역을 정한다.

    **주고받기가 이 악장의 전부다.** 41마디를 같은 패턴으로 치면 아무리
    빨라도 반주다. 4마디마다 주역이 바뀌고, 드럼은 자기 차례에 앞으로 나온다.

    role — "org" 해먼드 리드 / "drum" 드럼 주도 / "moog" 비명 / "tutti" 총주
    """
    g = [0, 2, 4]                                  # 2+2+3 의 그룹 머리
    if role == "drum":
        # 드럼 차례 — 킥이 그룹을 다 짚고 스네어가 뒤를 채운다
        p = [(0, "kick", 1.00), (2, "kick", 0.94), (4, "kick", 0.90),
             (1, "snare", 0.30), (3, "snare", 0.34), (5, "snare", 0.86),
             (6, "snare", 0.40)]
        p += [(b, "hat", 0.38 if b in g else 0.24) for b in range(7)]
        if n % 4 == 3:                             # 네 마디마다 탐으로 굴린다
            p += [(4.0, "tom:50", 0.70), (4.5, "tom:50", 0.30),
                  (5.0, "tom:45", 0.76), (5.5, "tom:45", 0.32),
                  (6.0, "tom:40", 0.82), (6.5, "tom:40", 0.36)]
        return p
    if role == "tutti":
        p = [(0, "kick", 1.00), (2, "kick", 0.92), (4, "snare", 0.96),
             (3.75, "snare", 0.30), (6, "kick", 0.70)]
        p += [(b, "hat", 0.40 if b in g else 0.26) for b in range(7)]
        if n % 4 == 0:
            p.append((0, "crash", 0.58))
        return p
    # 해먼드 리드·무그 차례 — 드럼은 받쳐만 준다. 앞에 나서지 않는다
    p = [(0, "kick", 0.92), (4, "snare", 0.72), (3.75, "snare", 0.20)]
    p += [(b, "hat", 0.30 if b in g else 0.18) for b in range(7)]
    return p
# 6/8 — 백비트를 치지 않는다. 그녀의 목소리 위에 백비트가 있으면 반주가 된다.
PAT_68 = [(0, "kick", 0.80), (3, "hato", 0.26)]


def lay_drum(put, t0, unit, pat, gain=1.0, n=0, jitter=None):
    """패턴 하나를 놓는다. `put(y, 시각, 세기, 팬)` 을 받는다.

    unit  — 한 칸의 초. 4/4·5/4·6/4 는 4분음표, 7/8·6/8 은 8분음표다.
    n     — 몇 번째 마디인가. 타격 씨앗에 섞어 같은 마디가 반복돼도 미세하게 다르게 한다.
    """
    for i, (b, kind, v) in enumerate(pat):
        tt = t0 + b * unit
        vv = v * gain
        if jitter is not None:
            tt, vv = jitter(tt, vv)
        pan = {"hat": 0.22, "hato": 0.22, "crash": -0.18}.get(kind, 0.0)
        put(drum(kind, gain=min(1.0, vv), seed=n * 7 + i), tt, 1.0, pan)
