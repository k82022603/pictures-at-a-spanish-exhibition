# -*- coding: utf-8 -*-
"""마스터를 납품 파일로 굽는다.

**비트depth 는 파일의 종류가 정한다** (2026-08-13 검수자 판정).

> *"어제처럼 진행. 9악장 전체만 32비트 찍어냄. 단, 일일마감할 때 최종
> 9악장 음원의 경우 24비트도 동시에 찍어내서 google drive까지 업로드함."*

| 무엇 | 비트 | 왜 |
|---|---|---|
| **발췌** (`--excerpt`) | **24** | 들으시려고 내는 것이다. **어느 플레이어에서든 열려야 한다** |
| **전곡** | **32** | 뒤에 보컬·영상·마스터링이 남았으므로 **안 버린다** |
| **마감 때 최종 전곡** | **둘 다** (`--bits both`) | Drive 에 나란히 올린다 |

이 규칙이 기본값이라 **평소에는 `--bits` 를 안 쓴다.** 어겨야 할 때만 쓴다.

검수자 — *"mp3는 더이상 만들지 않아도 됨."*
**전곡을 구우면 악장별 구간표까지 만든다.**

    python 납품.py "산출물/20260813 - 한 마디" "full v4.20 9m40s"
    python 납품.py <폴더> "mv7 A 피아노" --excerpt 325:100
    python 납품.py <폴더> <이름> --bits both        # 마감

**발췌도 이 도구가 굽는다** (2026-08-13 신설). 전에는 `--excerpt` 가 사용법에만
적혀 있고 **구현이 없어서 손으로 `ffmpeg` 를 불렀고, 그것이 어제 사고의
원인이었다** — 발췌만 24비트로 깎여 나가는 것을 아무도 몰랐다. 손으로 굽는
경로가 남아 있으면 검사도 같이 빠진다.

**왜 도구로 만드는가.** 이 프로젝트는 형식을 손으로 굽다가 두 번 틀렸다.

  ① `write_wav` 가 **마스터만 16비트로** 떨어뜨리고 있었다. 계산도 스템도
     32비트 실수인데 마지막 한 줄이 깎았고, 넉 달 동안 아무도 안 봤다.
  ② `ffmpeg -c:a flac -sample_fmt s32` 가 **24비트를 쓴다.** 인코더가
     "Supported sample formats: s16 s32" 라고 적어놓고 그렇게 한다.
     경고도 안 낸다 — **「지원한다」와 「그 비트로 쓴다」가 다른 말이었다.**

**둘 다 「이름이 값과 다르다」이고, 사람이 매번 확인할 것이 아니라 도구가
확인해야 한다.** 그래서 이 스크립트는 굽고 나서 **반드시 되돌려 대조한다.**

경위와 실측은 [10. 렌더와 음원 파일] 5절과 별첨.
"""
import io
import os
import re
import subprocess
import sys

import numpy as np
from scipy.io import wavfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100


def find_flac():
    """공식 FLAC 도구를 찾는다.

    **ffmpeg 으로는 24비트가 상한이다.** 32비트는 FLAC 1.4+ 가 필요하고,
    winget 으로 깐 것은 **새 셸에서만 PATH 에 잡히므로** 설치 경로도 뒤진다.
    """
    from shutil import which
    p = which("flac")
    if p:
        return p
    base = os.path.expandvars(r"%LocalAppData%\Microsoft\WinGet\Packages")
    if os.path.isdir(base):
        for d in os.listdir(base):
            if not d.startswith("Xiph.FLAC"):
                continue
            for root, _, files in os.walk(os.path.join(base, d)):
                if "flac.exe" in files and "Win64" in root:
                    return os.path.join(root, "flac.exe")
    return None


def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr.decode("utf-8", "replace")[-800:])
        raise SystemExit("실패: %s" % cmd[0])


def load(path):
    """**자료형을 먼저 본다.** int16 도 float32 도 int32 도 돌아온다."""
    _, a = wavfile.read(path)
    return a


def probe(path, key):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=%s" % key, "-of", "default=nw=1", path],
                       capture_output=True)
    m = re.search(r"=(.+)", r.stdout.decode("utf-8", "replace"))
    return m.group(1).strip() if m else "?"


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def bake(src, fl, bits, flac_bin, cut=None):
    """마스터 → FLAC 한 판. **굽고 되돌려 대조한 결과를 돌려준다.**

    `bits` 는 **여기서 정해진다** — `flac --bps=` 는 raw 입력 전용이라
    wav 를 주면 거부하므로, 정수 wav 로 옮기는 이 단계가 유일한 자리다.

    `cut` 은 `(시작초, 길이초)`. 발췌도 같은 검사를 받는다.
    """
    tmp = os.path.join(HERE, "_납품중간%s.wav" % bits)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if cut:
        cmd += ["-ss", "%.3f" % cut[0], "-t", "%.3f" % cut[1]]
    cmd += ["-i", src, "-c:a", "pcm_s%dle" % bits, tmp]
    run(cmd)
    run([flac_bin, "--best", "--force", "--silent", "-o", fl, tmp])

    # ── 되돌려 대조한다. **이 검사가 이 스크립트의 존재 이유다** ────────
    back = os.path.join(HERE, "_납품확인.wav")
    run([flac_bin, "-d", "--force", "--silent", "-o", back, fl])
    a, b = load(tmp), load(back)
    n = min(len(a), len(b))
    ok = bool(np.array_equal(a[:n], b[:n]))
    got = probe(fl, "bits_per_raw_sample")
    for f in (tmp, back):
        try:
            os.remove(f)
        except OSError:
            pass
    return ok, got


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    outdir, name = sys.argv[1], sys.argv[2]
    src = arg("--from", os.path.join(HERE, "전곡화성.wav"))
    if not os.path.isabs(outdir):
        outdir = os.path.join(HERE, "..", outdir)
    os.makedirs(outdir, exist_ok=True)

    # ── 발췌 구간. `--excerpt 325:100` = 325초부터 100초 ──────────────
    cut = None
    if arg("--excerpt"):
        _a, _b = arg("--excerpt").split(":")
        cut = (float(_a), float(_b))

    # ── 비트depth 는 파일의 종류가 정한다 (2026-08-13 검수자 판정) ──────
    #
    # **발췌 24 · 전곡 32 · 마감 때 둘 다.** 기본값이 그 규칙이라
    # 평소에는 `--bits` 를 안 쓴다.
    #
    # 어제 사고의 모양이 **「이름이 값과 다르다」**였으므로, 무엇을 왜
    # 그 비트로 굽는지 **화면에 먼저 찍는다.**
    want = arg("--bits", "24" if cut else "32")
    if want not in ("24", "32", "both"):
        raise SystemExit("--bits 는 24 · 32 · both 중 하나다")
    bits_list = [32, 24] if want == "both" else [int(want)]

    flac_bin = find_flac()
    if not flac_bin:
        raise SystemExit("flac 을 못 찾았다. winget install --id Xiph.FLAC")

    fmt = probe(src, "sample_fmt")
    print("마스터   %s  (%s)" % (os.path.basename(src), fmt))
    if fmt not in ("flt", "s32"):
        print("  ⚠ 마스터가 %s 다. 32비트로 못 간다 — piano.write_wav 를 본다" % fmt)
    print("종류     %s" % ("발췌 %.0f초부터 %.0f초" % cut if cut else "전곡"))
    print("비트     %s%s" % (" · ".join("%d비트" % b for b in bits_list),
                             "" if arg("--bits") else "  (기본값 — 규칙대로)"))

    # ── ① 굽는다. 요청한 비트마다 한 판씩 ─────────────────────────────
    #
    # **어제(2026-08-12) 여기서 두 가지가 겹쳐 사고가 났다.**
    #
    # 검수자가 32비트 전곡을 열자 Windows 미디어 플레이어가 거부했다 —
    # *"지원되지 않는 형식으로 인코딩되어 있습니다"* (0xC00D36B4).
    # **FLAC 이 32비트를 지원한 것은 1.4(2022) 부터**라 재생기 대부분이 못 읽는다.
    #
    # **그 자리에서 내가 확인 없이 단정했다** — 「32비트는 대부분 못 연다」고
    # 말했는데, 검수자가 *"mv9 대문은 재생 가능함. 뭔가 잘못 알고 있는 것
    # 아닌가?"* 라고 되물었다. **재보니 발췌들은 24비트였다** — 발췌만 내가
    # 손으로 `ffmpeg` 을 불러 구웠고 ffmpeg 은 32비트를 못 쓴다. 즉 **전곡만
    # 안 열렸다.** 갈리는 지점은 「FLAC 이냐」가 아니라 **「어느 도구로
    # 구웠나」**였고, 나는 그 사실을 검수자가 반례를 낼 때까지 몰랐다.
    #
    # **그리고 승인 없이 형식을 24비트로 바꿨다.** 검수자 — *"24비트로 굳힌적
    # 없음 ^^"*. 막힌 것을 만나자 **문제를 푸는 김에 확정까지 바꿨다.**
    #
    # > **판정이 나왔다 (2026-08-13)** — 발췌 24 · 전곡 32 · 마감 때 둘 다.
    # > **두 경로가 하나로 합쳐졌으므로 발췌도 이제 검사를 받는다.**
    #
    # 24비트와 32비트의 차이는 −149.1 dB 로 24비트의 잡음 바닥(−144)보다도
    # 아래다. **안 들린다.** 그래도 남기는 이유는 뒤에 보컬·영상·마스터링이
    # 남아 있기 때문이고, **그건 마스터에 해당하는 말**이다.
    #
    # ── MP3 는 더 이상 굽지 않는다 (2026-08-12, 검수자 "mp3는 더이상 만들지
    #    않아도 됨"). 되살릴 일이 생기면 아래 한 줄이면 된다 —
    #      ffmpeg -i <마스터> -c:a libmp3lame -b:a 320k <이름>.mp3
    mb = lambda p: os.path.getsize(p) / 1048576.0
    made, bad = [], False
    for b in bits_list:
        # 둘을 함께 구울 때만 이름에 비트를 박는다. 한 판이면 이름 그대로다
        sfx = " (%dbit)" % b if len(bits_list) > 1 else ""
        fl = os.path.join(outdir, name + sfx + ".flac")
        ok, got = bake(src, fl, b, flac_bin, cut)
        print()
        print("FLAC     %s  %s비트  %.1f MB" % (os.path.basename(fl), got, mb(fl)))
        print("  무손실     %s" % ("★ 비트 단위 100% 일치" if ok
                                   else "✘ 다르다 — 쓰면 안 된다"))
        print("  비트depth  %s" % ("★ %d비트 — 요청한 그대로" % b if got == str(b)
                                   else "✘ %s 비트 — %d 여야 한다" % (got, b)))
        made.append(fl)
        bad = bad or (not ok) or got != str(b)
    if bad:
        raise SystemExit(1)

    # 발췌는 여기서 끝난다 — 악장별 구간표는 전곡에만 붙는다
    if cut:
        print()
        print("★ 발췌다. 청취 안내는 `CLAUDE.md` 8절의 **여섯 칸**을 다 채운다 — "
              "**시각은 계산하지 말고 음원에서 잰다.**")
        return
    fl = made[0]

    # ── ⑤ **악장별 구간표를 같이 만든다** ────────────────────────────
    #
    # `movement-guide` 스킬이 "전곡 파일을 하나라도 새로 만들면 쓴다. 요청을
    # 기다리지 않는다"고 적어두었는데 **2026-08-12 하루에 두 번 빠뜨렸다.**
    # 검수자 — *"오늘 같은말 여러번 하게 하지마라."*
    #
    # **스킬에 적어두는 것으로는 안 지켜졌다.** `11. 공용 함수` 6절이 그날
    # 세운 규칙이 이것이다 — **문서에 적을 수 있는 규칙은 도구로 옮길 수
    # 있는지 먼저 묻는다.** 그래서 납품이 구간표를 낳게 한다.
    guide = os.path.join(outdir, "구간표 - %s.md" % name)
    r = subprocess.run([sys.executable, os.path.join(HERE, "악장표.py")],
                       capture_output=True, cwd=HERE,
                       env=dict(os.environ, PYTHONUTF8="1"))
    body = r.stdout.decode("utf-8", "replace")
    if r.returncode != 0 or not body.strip():
        print()
        print("⚠ 구간표를 못 만들었다 — `악장표.py` 를 직접 돌려 확인한다")
    else:
        head = [
            "# 구간표 — %s" % name,
            "",
            "**`악장표.py` 가 코드와 음원에서 생성한 것이다. 손으로 안 적는다.**",
            "",
            "청취 안내를 쓸 때는 `CLAUDE.md` 8절의 **여섯 칸**을 다 채운다 —",
            "소리의 모양 · 시각 전부 · 길이 · 일상 비유 · 가장 쉬운 확인법 · A/B 차이.",
            "**시각은 반드시 음원에서 재서 적는다** (계산으로 적다가 틀린 적이 있다).",
            "",
            "```",
            body.rstrip(),
            "```",
            "",
        ]
        io.open(guide, "w", encoding="utf-8").write("\n".join(head))
        print("구간표       %s" % os.path.basename(guide))
        print()
        # ── 여기서 세 번 빠뜨렸다. 파일을 만든 것과 보낸 것은 다른 일이다 ──
        #
        # **2026-08-13 에 네 번째 지적을 받았다.** 그날은 구간표 파일이 실제로
        # 있었는데도 안 보냈다. 즉 **「만들었나」를 찍는 것으로는 안 막힌다** —
        # 막아야 하는 것은 **「보냈나」**다.
        #
        # 그리고 어제까지 나간 구간표는 **원자료 덤프뿐이고 일곱 칸 표가
        # 없었다.** 스킬이 요구하는 것은 **「집중해서 들을 지점」에 시각이
        # 박힌 표**이고, 그건 도구가 못 만든다. **그래서 미완성이라고
        # 화면에 적는다** — 조용히 그럴듯한 파일을 내놓는 것이 더 나쁘다.
        print("=" * 66)
        print("★ 전곡을 냈다. **아래 둘을 함께 보낸다** (`movement-guide`)")
        print("   1. %s" % os.path.basename(fl))
        print("   2. %s" % os.path.basename(guide))
        print()
        print("   **그 구간표는 아직 원자료뿐이다.** 일곱 칸 표를 손으로 채운다 —")
        print("   악장 · 구간(분:초) · 길이 · 빠르기 · 음량 · 무슨 일이 · **들을 지점**.")
        print("   「들을 지점」의 시각은 **음원에서 재서** 적는다. 계산 금지.")
        print("=" * 66)


if __name__ == "__main__":
    main()
