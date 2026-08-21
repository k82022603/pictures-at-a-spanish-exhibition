# Suno 소명 — 저작권 대조 해제 요청

**2026-08-22.** 1부·3부 업로드가 *"This audio matches an existing recording"* 로 막혔다.
**우회하지 않고 소명으로 푼다** — 파일을 가공해 지문을 피하는 것은 하지 않는다.

## 무엇이 막혔나

| | |
|---|---|
| 계정 | `k82022603@gmail.com` |
| 막힌 파일 | `1부 (0~3악장) 0.00-2.40.mp3` · `3부 (7~8악장) 5.25-8.45.mp3` |
| 통과한 파일 | `2부 (4~6악장) 2.40-5.25.mp3` |
| 짚이는 원인 | **1부 0악장 50초가 무소르그스키 프롬나드 선율.** 2부는 우리 창작이라 안 걸렸다 |

## 우리 쪽 사실

- 원곡 **무소르그스키 《전람회의 그림》(1874)** — **퍼블릭 도메인**
- 이 녹음은 **직접 합성**했다. 파이썬 가산합성·Karplus-Strong·라더 필터. **샘플 라이브러리도 상업 녹음도 안 썼다**
- 편곡은 **원본 악보(MusicXML)에서 직접** 했다. **ELP·호로비츠 편곡은 일부러 참조하지 않았다** — 편곡 저작권이 살아 있어서다
- **같은 코드가 비트 단위로 같은 wav 를 낸다**(BL-30). 요구하면 재현해 보일 수 있다

> **마지막 항목이 이 소명의 힘이다.** 「우리가 만들었다」는 주장은 흔하지만
> **「지금 다시 만들어 보이겠다」는 증명은 드물다.**

---

## 언제 보냈나

**2026-08-22 오전 1:12 발송.** `k82022603@gmail.com` → `support@suno.com`.
제목 — *Upload blocked as matching an existing recording - public-domain work,
fully self-synthesised*

**첨부는 안 붙였다.** 먼저 사람이 읽게 하고, 요구하면 그때 낸다.

**답이 올 때까지 기다리지 않는다** — 2부는 이미 통과했으므로 그쪽은 진행할 수
있고, 프롬나드 악장은 우리 음원을 그대로 쓰는 길이 남아 있다.

---

## 보낸 글 (영문)

```
Subject: Upload blocked as "matches an existing recording" — public-domain
work, fully self-synthesised recording (account k82022603@gmail.com)

Hello,

Two of my uploads are blocked with "This audio matches an existing
recording." I believe this is a false positive and I own all rights to
the recordings. I would like to request a review.

Account: k82022603@gmail.com

Blocked uploads:
  - "1부 (0~3악장) 0.00-2.40.mp3"  (2 min 40 s)
  - "3부 (7~8악장) 5.25-8.45.mp3"  (3 min 20 s)
A third file from the same project, "2부 (4~6악장) 2.40-5.25.mp3",
uploaded without any warning.

What the audio is:

1. The underlying composition is Modest Mussorgsky's "Pictures at an
   Exhibition" (1874), which is in the public domain worldwide.

2. The recording is not a recording of any existing performance. It is
   synthesised from scratch by my own Python code — additive synthesis
   for piano, Karplus-Strong for nylon-string guitar, a nonlinear ladder
   filter for the Moog parts, and so on. No sample libraries and no
   commercial recordings were used at any point.

3. The arrangement is my own, written directly from the public-domain
   score (MusicXML). I deliberately did not reference any copyrighted
   arrangement of the work.

4. The render is bit-for-bit reproducible. Running the same code twice
   produces byte-identical output. I am happy to demonstrate this, or to
   provide the source code, the intermediate stems, or the score, if that
   would help your review.

The likely cause of the match is that the first section states
Mussorgsky's "Promenade" theme, which is presumably fingerprinted from
commercial recordings of the same public-domain work. The file that
uploaded cleanly contains only my own original material, which fits that
explanation.

I am using these uploads as reference audio for Cover generations of my
own project, and I am on a paid plan. Any guidance on how to get these
files cleared would be very welcome.

Thank you for your time.
```

---

*작성 일자: 2026-08-22*

---

## 답장 — **거절. 2026-08-22 오전 3:16** (발송 2시간 뒤)

`support@suno.com` · Sheila

**우리 주장을 반박하지 않았다.** 퍼블릭 도메인도, 자체 합성도 다투지 않았다.
**거절 사유는 「구분할 수단이 없다」**였다.

| 그들이 말한 것 | |
|---|---|
| 차단은 시스템이 **제대로 작동한 것** | 오작동이 아니라는 입장 |
| **검출기가 「원작자가 올린 것」과 「무단 사용」을 구분하지 못한다** | **★ 진짜 이유** |
| 그래서 **당신이 만들었어도** 일치하면 막는다 | |
| **창작자 인증 제도**를 개발 중 | **일정 없음** |
| *"we can't resolve this particular issue right now"* | 명시적 |

### 그래서 무엇이 닫혔나

**재소명은 값이 없다.** 사유가 「못 믿겠다」가 아니라 **「확인할 방법이 없다」**이므로
같은 글을 다시 보내도 같은 답이 온다. **인증 제도는 일정이 없고 9/3 시한이 있다.**

> **0악장을 새로 만드는 것 외에 길이 없다** (검수자 지시, 2026-08-22).
> 기존 0악장은 **한 줄도 안 건드린다** — 승인 기준선이고, 우리 음원으로는 계속 유효하다.

### 남는 것 하나 — 이 기록의 값

**「해봤고 이런 답이 왔다」가 나중의 판단 근거다.** 인증 제도가 나오면 그때
다시 올릴 수 있고, 그때 이 메일이 **우리가 먼저 요청했다는 증거**가 된다.
