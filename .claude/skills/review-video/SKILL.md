---
name: review-video
description: MusicVideo 음원을 유튜브 업로드용 검토 영상(MP4)으로 만들 때 쓴다. CQT 음정축 스펙트럼 + 화음 심볼·보이싱 자막 번인 + 유튜브 규격 인코딩 + 영상·소리 동기 검증을 다룬다. "유튜브에 올릴 영상", "MP4로 만들어줘", "검토 영상", "자막 넣어줘", "음원을 영상으로" 같은 요청에 쓴다. Phase 3 뮤직비디오(사진 사용)와는 다른 작업이며, G3 PoC 통과 전에는 사진을 쓰지 않는다.
---

# 유튜브 검토 영상

유튜브는 **음성 파일 업로드를 받지 않는다.** MP3·WAV·PCM은 "invalid file format"으로 거부된다. 그래서 MP4로 변환하는데, 검은 화면에 소리만 얹는 건 낭비다. **화면을 화성 판독 장치로 만든다.**

> **이것은 Phase 3 뮤직비디오가 아니다.** `02. AI 영상 생성 기술 검증 계획서`의 G3 PoC를 통과하기 전에는 253장 사진을 쓰지 않는다. 켄번스로 붙이면 듣기 편해지지만 나중에 버리는 일이 된다.

## 파이프라인

```
전곡화성.wav + chordlog.npy
  → 음정축.py      (건반 축 이미지)
  → 자막생성.py    (화음 심볼 + 보이싱 자막 ASS)
  → ffmpeg showcqt + ass 번인
  → 유튜브 규격 인코딩
  → 동기·정합 검증
```

## 1. 음정축과 자막

```bash
cd "99. 작업 스크립트"
python 음정축.py     # → 음정축.png  (1856×46)
python 자막생성.py   # → 자막.ass    (chordlog.npy 필요)
```

**음정축에 이 곡의 화성 설계를 새겨 넣는다.** 이게 이 영상의 핵심 아이디어다.

| 건반 색 | 의미 |
|---|---|
| 밝은 건반 | 이 곡의 음집합 `B♭ C D E♭ F G A` |
| 어두운 건반 | 이 곡에 쓰이지 않는 음 |
| **붉은 건반** | **F♯** — 유일한 조성 밖 음 |

스펙트럼이 붉은 건반 위에서 빛나는 순간이 곧 그녀가 등장하는 순간이다.

`자막생성.py`를 고칠 일이 있으면 두 가지를 주의한다.

- **`\pos()`로 위치를 지정한다.** libass는 같은 시각에 겹치는 자막을 충돌 회피로 위아래로 밀어내는데, 그러면 화음과 음이름 순서가 뒤집힌다. `\pos`를 쓰면 충돌 회피가 꺼진다
- **역슬래시는 하나다.** 파이썬 문자열에서 `"{\\an5\\pos(960,872)}"`로 써야 파일에 `{\an5\pos(...)}`가 들어간다. 두 개가 되면 자막이 그대로 문자로 표시된다

`MOV` 배열의 악장 경계는 `00` 기획서·`검증화성.py`와 같은 값이어야 한다.

## 2. 필터그래프

`영상필터.txt`에 여러 줄로 두고, **개행을 제거해** `-filter_complex_script`로 넘긴다.

```bash
tr -d '\n' < 영상필터.txt > 영상필터1.txt
```

```
[0:a]showcqt=s=1856x480:fps=30:count=6:bar_g=2.4:sono_g=3.4:basefreq=32.703196:endfreq=2093.004522:bar_v=23:sono_v=16:axis_h=46:sono_h=180:axisfile=음정축.png:cscheme=0.13|0.40|0.66|0.26|0.46|0.44[cqt];
color=c=0x0B0D12:s=1920x1080:r=30:d=580[bg];
[bg][cqt]overlay=32:320:shortest=1[v0];
[v0]drawbox=x=31:y=319:w=1858:h=482:color=0x233247@1.0:t=2[v1];
[v1]ass=자막.ass[vout]
```

**showcqt에서 반드시 지킬 것**

| 항목 | 이유 |
|---|---|
| `basefreq=32.703196` `endfreq=2093.004522` | C1~C7 **정확히 6옥타브(64배)**. 그래야 폭이 6등분되고 건반 이미지가 맞는다 |
| `axisfile=음정축.png` | 기본 주파수 범위를 벗어나면 **내장 폰트 축이 안 그려진다**("font axis rendering is not implemented in non-default frequency range"). axisfile로 대체해야 한다 |
| `axis_h`는 축 이미지 높이와 일치 | 46 |
| `tlength` 같은 식 인자에 `tc(...)` 함수 | ffmpeg 버전에 따라 파싱 실패한다. 문제 생기면 그냥 빼면 된다 |
| `bar_v` 를 20 이상 | 낮으면 막대가 흰색으로 포화되어 `cscheme` 색이 안 보인다 |

**화면 배치** (1920×1080)

| y | 내용 |
|---|---|
| 40–130 | 제목 · 실측 요약 (좌) / 음정축 범례 (우) |
| 160–290 | 악장 이름 · 중심음·선법·템포·서사 |
| 320–800 | CQT — 위 막대(순간) / 축 / 아래 스크롤(이력) |
| 862–962 | **화음 심볼** |
| 966–1008 | 네 성부의 실제 음이름 |
| 1026–1060 | 청취 지점 주석 |

## 3. 인코딩

**PC에서는 한 번에 통과한다.** 아래 분할은 Cowork 샌드박스의 도구 호출 제한(약 178초) 때문에 했던 우회다. 먼저 한 번에 시도하고, 실패할 때만 분할한다.

```bash
ffmpeg -hide_banner -v warning -y -i 전곡화성.wav \
  -filter_complex_script 영상필터1.txt -map "[vout]" -map 0:a \
  -c:v libx264 -preset veryfast -crf 20 -profile:v high -level 4.1 \
  -pix_fmt yuv420p -r 30 -g 60 -keyint_min 60 -sc_threshold 0 \
  -c:a aac -b:a 384k -ar 48000 -ac 2 -movflags +faststart \
  "전곡 코드 진행 vN.N - 화성 검토 영상.mp4"
```

### 분할해야 할 때

분할은 **두 종류**이고 성질이 다르다. 섞으면 헷갈린다.

**(1) CQT 렌더 분할** — 자막을 번인하는 단계다. **접합점을 악장 경계에 둔다.** CQT 스크롤 이력이 초기화되는데, 악장이 새로 시작하는 지점이면 눈에 띄지 않는다. 275(론다) · 425(바르셀로나)를 썼다.

이 경우 **두 번째 이후 구간은 자막 타임스탬프를 옮겨야 한다.** `-ss`로 자르면 출력 PTS가 0부터 시작하는데 자막은 절대 시각이다.

```
[v1]setpts=PTS+275/TB,ass=자막.ass,setpts=PTS-275/TB[vout]
```

`ass` 앞에서 더하고 뒤에서 되돌린다. 오프셋은 그 구간의 `-ss` 값과 같아야 한다.

**(2) 재인코딩 분할** — 이미 자막이 화면에 구워진 영상을 다시 인코딩하는 단계다. **자막 필터를 안 쓰므로 PTS 조작이 필요 없고, 접합점도 아무 키프레임이나 된다.** `-g 60`이면 2초마다 키프레임이니 290 같은 값을 쓰면 된다.

### 접합음을 없애는 방법

구간별로 오디오를 따로 인코딩해 붙이면 접합부에서 클릭이 난다. **영상만 분할 인코딩하고, 오디오는 원본 WAV에서 통째로 다시 먹싱한다.**

```bash
# 1) 구간별 영상만 (-an)
ffmpeg ... -an -c:v libx264 ... r1.mp4
ffmpeg -ss 290 ... -an -c:v libx264 ... r2.mp4
# 2) 영상 접합 (copy)
printf "file 'r1.mp4'\nfile 'r2.mp4'\n" > rlist.txt
ffmpeg -f concat -safe 0 -i rlist.txt -c copy rv.mp4
# 3) 연속 오디오 재먹싱
ffmpeg -i rv.mp4 -i 전곡화성.wav -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 384k -ar 48000 -ac 2 -shortest \
  -movflags +faststart "최종.mp4"
```

**주의 — `-preset ultrafast`는 `-profile:v high`를 무시하고 Constrained Baseline으로 떨어진다.** CABAC과 B프레임이 꺼져서 파일이 3배 커진다. 실제로 397MB가 나왔고, `veryfast crf 20`으로 다시 인코딩해 120MB가 됐다. 유튜브 권장은 High profile이다.

**주의 — `+faststart`는 파일 전체를 다시 쓴다.** 400MB 파일에서 이 단계만 1분 이상 걸리고, 중간에 끊기면 **moov atom이 없어 파일이 아예 안 열린다.** 접합 단계에서는 빼고, 마지막 먹싱에서만 붙인다.

## 4. 유튜브 규격

| 항목 | 값 |
|---|---|
| 컨테이너 | MP4 |
| 영상 | H.264 **High** profile, Level 4.1 |
| 해상도·프레임 | 1920×1080 / 30 fps |
| 픽셀 형식 | yuv420p |
| 음성 | AAC-LC **384 kbps** / **48 kHz** 스테레오 |
| moov | 선두 (faststart) |

음원 마스터는 44.1 kHz이므로 영상 음성만 48 kHz로 리샘플한다. **원본 MP3(320 kbps, 44.1 kHz)를 함께 남긴다 — 음질 판정 기준은 그쪽이다.**

허용 컨테이너: MOV · MPEG-1/2/4 · MP4 · MPG · AVI · WMV · MPEGPS · FLV · 3GPP · WebM · DNxHR · ProRes · CineForm · HEVC.

## 5. 검증 — 세 가지

파이프라인이 길어서 어긋날 지점이 많다. 반드시 실측한다.

### (a) 영상 ↔ 소리 동기

영상에서 오디오를 다시 뽑아 원본과 교차상관한다. **접합부를 포함한 여러 지점**에서 본다.

```bash
ffmpeg -v error -y -i "최종.mp4" -ar 44100 -ac 2 chk.wav
python - <<'PY'
import numpy as np
from scipy.io import wavfile
from scipy import signal as sg
sr, a = wavfile.read('전곡화성.wav'); a = a.astype(float).mean(1) / 32768
_,  b = wavfile.read('chk.wav');     b = b.astype(float).mean(1) / 32768
for t0 in (30, 160, 275, 425, 540):        # 접합점을 반드시 포함
    s, w = int(t0 * sr), int(4 * sr)
    x, y = a[s:s+w], b[s:s+w]
    c = sg.correlate(y - y.mean(), x - x.mean(), mode='same')
    lag = int(np.argmax(np.abs(c)) - len(x) // 2)
    r = np.corrcoef(x, np.roll(y, -lag)[:len(x)])[0, 1]
    print('%4ds  지연 %+3d 샘플 (%+.2f ms)  상관 %.4f' % (t0, lag, lag / sr * 1000, r))
PY
```

**통과 기준: 전 지점 0 샘플.** v1.6에서 접합부 포함 전부 0이었다.

### (b) 화음 라벨 ↔ 실제 울리는 음

`harmony-verify` 스킬의 3절과 같은 검사다. 영상에서 뽑은 오디오로 하면 영상↔소리 정합까지 함께 본다. 전체 **85% 이상**, 4악장 제외 **95% 이상**이면 통과.

### (c) 프레임 수·규격

```bash
ffprobe -v error -show_entries format=duration,size \
  -show_entries stream=codec_name,profile,width,height,r_frame_rate,pix_fmt,sample_rate,channels,nb_frames \
  -of default=nw=1 "최종.mp4"
```

`nb_frames` = 재생시간 × 30. `profile=High` 확인. **`Constrained Baseline`이면 ultrafast로 인코딩된 것이니 다시 한다.**

## 6. 대표 프레임 확인

숫자만으로는 레이아웃이 깨진 걸 못 잡는다. **악장이 바뀌는 지점과 접합부의 프레임을 뽑아 눈으로 본다.**

```bash
for T in 22 168 281 430 570; do
  ffmpeg -v error -y -ss $T -i "최종.mp4" -frames:v 1 "frame_$T.png"
done
```

`570`은 F♯→F 해소 구간이라 자막·주석이 다 나오는 프레임이다.

## 7. 결과 반영

영상을 새로 만들었으면 `05` 문서 10장과 `CLAUDE.md` 7절의 산출물 표·실측값을 갱신한다. **`doc-revise` 스킬 절차를 따른다.**
