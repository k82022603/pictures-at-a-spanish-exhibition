// **10분 뼈대 — 사진 244장이 음악 위에 놓인다.**
//
// 이 파일은 **아무것도 정하지 않는다.** 어느 사진이 몇 초에 나오는지는
// `뼈대.py` 가 정해 `뼈대.json` 에 적어 두었고, 여기서는 그것을 **그리기만** 한다.
// 배치를 바꾸려면 이 파일이 아니라 `뼈대.py` 를 고친다.
import {
  AbsoluteFill, Audio, Img, Sequence, interpolate,
  staticFile, useCurrentFrame, useVideoConfig, Easing,
} from "remotion";
import 뼈대 from "./뼈대.json";

// ── 색 ────────────────────────────────────────────────────
// 검정이 아니라 **아주 짙은 남색**이다. 순검정은 사진 가장자리와 붙어
// 화면이 잘린 것처럼 보인다.
const 바탕 = "#07090E";
const 글자 = "#F2EFE6";
const 흐린글자 = "#8B99A8";
const 글꼴 = "'Malgun Gothic', 'Noto Sans KR', sans-serif";

// `뼈대.json` 의 경로는 원본 폴더 기준이고, Remotion 은 `public/` 아래만 읽는다.
const 사진경로 = (p) => staticFile(p.replace("2005년 12월 스페인/", "사진/"));

// ── 화면에 띄울 때 밝히는 것 ──────────────────────────────────
//
// **사진 파일은 안 건드린다.** 밝힌 사본을 만들면 244 가 흔들린다.
// **얼마나 밝히는지는 `뼈대.py` 가 정해 `뼈대.json` 에 실어 보낸다** —
// 여기서는 시키는 대로 하기만 한다.
const 보정필터 = (b) => (b
  ? `brightness(${b.밝기 ?? 1}) contrast(${b.대비 ?? 1}) saturate(${b.채도 ?? 1})`
  : "");

// ── 켄번스 ────────────────────────────────────────────────
//
// **사진 내용은 한 픽셀도 안 바뀐다. 보는 자리만 천천히 옮겨간다.**
// 방향은 **컷 번호로 정한다** — 난수를 쓰면 구울 때마다 달라져서
// 「어제 것과 뭐가 달라졌나」를 못 가린다 (BL-30 과 같은 이유).
const 움직임 = (i, 줌없이) => {
  // ## 개정 — **가로 사진도 줌을 되살린다** (2026-08-24, 검수자)
  //
  // > **검수자** — *"줌 없으니 밋밋함. 가로 사진도 줌 살려줘."*
  //
  // 한 판(v6)을 줌 없이 구웠다. **화질로는 2.14배 → 1.88배로 나아졌지만
  // 화면이 밋밋해졌다.** 가로 사진에서 「다가가는 느낌」이 사라졌고,
  // **세로 사진은 줌이 남아 있어 두 리듬이 섞였다.**
  //
  // **표현을 택했다.** 무른 것은 ①(또렷하게)이 가린다.
  // 아래 `이동만` 은 안 지운다 — 되돌릴 때 쓴다(R3).
  const 이동만 = [
    { 부터: 1.00, 까지: 1.00, x: -30, y: 0 },
    { 부터: 1.00, 까지: 1.00, x: 30, y: 0 },
    { 부터: 1.00, 까지: 1.00, x: 0, y: -20 },
    { 부터: 1.00, 까지: 1.00, x: 0, y: 20 },
    { 부터: 1.00, 까지: 1.00, x: -22, y: 12 },
    { 부터: 1.00, 까지: 1.00, x: 22, y: -12 },
  ];
  const 표 = [
    { 부터: 1.00, 까지: 1.10, x: 0, y: 0 },      // 천천히 다가간다
    { 부터: 1.10, 까지: 1.00, x: 0, y: 0 },      // 천천히 물러난다
    { 부터: 1.08, 까지: 1.12, x: -34, y: 0 },    // 왼쪽으로 흐른다
    { 부터: 1.08, 까지: 1.12, x: 34, y: 0 },     // 오른쪽으로 흐른다
    { 부터: 1.06, 까지: 1.14, x: 0, y: -22 },    // 위로 훑는다
    { 부터: 1.14, 까지: 1.06, x: 0, y: 22 },     // 아래로 훑는다
  ];
  // ## 개정 2 — **가로는 다시 줌 없이** (2026-08-24, 검수자)
  //
  // > **검수자** — *"가로 이 사진은 줌 없는 것이 낫겠다.
  // > 인물사진 줌해버리니까 결과물이 좋진 않아 보여."*
  //
  // **앞선 「밋밋함」 판정은 내가 「줌을 뺐다」고 잘못 보고한 상태에서 나온 것이었다**
  // (실제로는 줌이 살아 있었다). **v7 을 보고 다시 판정하니 줌 없는 쪽**이다.
  //
  // **이유가 화질이 아니라 사람이다** — 꽉 채운 가로 사진에는 **사람이 크게 찍힌 것**이
  // 많고, 거기서 줌을 하면 **얼굴로 밀고 들어가는 꼴**이 된다. V1(얼굴 클로즈업 금지)의
  // 뜻과도 어긋난다.
  //
  // 세로·멀티패널은 **온전히** 놓아서 줌을 해도 얼굴로 안 밀고 들어간다. 그대로 둔다.
  return (줌없이 ? 이동만 : 표)[i % 6];
};

// ── 선명하게 보이게 한다 ─────────────────────────────────────
//
// **꽉 채우는 가로 사진은 1.88배로 늘어나 무르다.** 업스케일을 안 하기로 했으므로
// (검수자, 2026-08-24) **가장자리를 진하게 그려 또렷해 보이게** 한다.
//
// **진짜 디테일이 늘어나는 것이 아니다** — 실측으로 선명도는 42%→118% 로 오르지만
// 원본과의 닮음(SSIM)은 0.974 → 0.951 로 떨어진다. **「선명해 보이게」이지
// 「선명하게」가 아니다**(`23` 7.7절).
//
// 그래도 **10분을 흘려 보는 데서는 대개 구분이 안 되고**, 켄번스가 천천히
// 움직이는 중이라 더 그렇다. **공짜다.**
//
// **CSS 에는 언샵이 없다.** `contrast()` 는 밝기 대비를 벌릴 뿐 가장자리를 못 세운다.
// 그래서 **SVG 의 3×3 되감기(convolution)**를 쓴다 — 가운데를 키우고 상하좌우를
// 깎는다. 합이 정확히 1 이라 **전체 밝기는 안 바뀐다.**
// ## 개정 — **여기서 안 한다. ffmpeg 가 한다** (2026-08-24)
//
// **SVG 되감기를 여기서 걸었더니 렌더가 22분 → 76분이 됐다.**
// 브라우저가 **18,595 프레임마다** 1920×1080 에 3×3 계산을 하기 때문이다.
//
// **ffmpeg 는 인코딩하며 한 번에 지나간다.** 걸리는 자리는 똑같다 —
// **1920×1080 으로 늘린 뒤**다. 그래서 결과도 같다:
//
// | | 선명도 | |
// |---|---|---|
// | 안 걸었을 때 | 95 | |
// | SVG (`날 0.35`) | 268 | |
// | **`ffmpeg unsharp=5:5:1.0`** | **259** | **닮은 정도 0.9939 · 화소당 차이 0.77/255** |
//
// **명령은 `95. 영상 프로젝트/README.md` 4절에 있다.**
//
// 이 자리를 비워 두는 이유 — **「화면에 뭔가를 거는 일은 ffmpeg 가 한다」**가
// 이 프로젝트가 원래 쓰던 방식이다(`review-video` 스킬). 그걸 안 보고
// 브라우저 안에서 풀다가 렌더를 두 번 낭비했다.
const 또렷하게 = "";
const 필터정의 = () => null;

const 켄번스틀 = (i, 프레임, 총프레임, 줌없이) => {
  const m = 움직임(i, 줌없이);
  const t = interpolate(프레임, [0, 총프레임], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.ease),          // 시작과 끝을 부드럽게
  });
  return {
    transform: `scale(${interpolate(t, [0, 1], [m.부터, m.까지])}) `
      + `translate(${interpolate(t, [0, 1], [0, m.x])}px, `
      + `${interpolate(t, [0, 1], [0, m.y])}px)`,
  };
};

// ── 세로 사진 한 장 ────────────────────────────────────────
//
// 768×1024 를 1920×1080 에 꽉 채우면 **위아래가 잘려 나간다.**
// 그래서 **자기 자신을 흐리게 깔고** 그 위에 온전한 사진을 얹는다.
const 세로한장 = ({ src, i, 보정 }) => {
  const 프레임 = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: 바탕, overflow: "hidden" }}>
      <Img src={src} style={{
        width: "100%", height: "100%", objectFit: "cover",
        filter: "blur(48px) brightness(0.42) saturate(0.7)",
        transform: "scale(1.2)",
      }} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <Img src={src} style={{
          height: "100%", width: "auto", objectFit: "contain",
          boxShadow: "0 0 90px rgba(0,0,0,.75)",
          filter: 보정필터(보정),
          ...켄번스틀(i, 프레임, durationInFrames),
        }} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ── 가로 사진 한 장 ────────────────────────────────────────
//
// ## 개정 — **잘라내지 않는다** (2026-08-24, 검수자)
//
// > **검수자** — *"가로 사진을 「잘라내지 말고 온전히」 — 세로처럼 뒤에 흐린 배경"*
//
// **1024×768(4:3)을 1920×1080(16:9)에 꽉 채우면 위아래 25%가 잘려 나간다.**
// 실측으로 확인했다 — 원본을 **1.88배**로 키우고 **세로 75%만** 보이고 있었다.
// **인물 사진에서 이게 특히 나빴다** — 사람이 화면을 꽉 채우고 발밑과 머리 위가 사라진다.
//
// **그래서 세로 사진과 같은 방식으로 바꾼다** — 온전한 사진을 최대 크기로 놓고
// 뒤에 자기 자신을 흐리게 깐다. **좌우에 흐린 띠가 생기는 대신 한 픽셀도 안 잘린다.**
//
// **덤이 하나 있다** — 늘어나는 배율이 **1.88배 → 1.41배**로 줄어 **덜 무르다.**
const 가로한장 = ({ src, i, 보정, 줌없이 }) => {
  const 프레임 = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: 바탕, overflow: "hidden" }}>
      <Img src={src} style={{
        width: "100%", height: "100%", objectFit: "cover",
        filter: "blur(48px) brightness(0.42) saturate(0.7)",
        transform: "scale(1.2)",
      }} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <Img src={src} style={{
          height: "100%", width: "auto", objectFit: "contain",
          boxShadow: "0 0 90px rgba(0,0,0,.75)",
          filter: 보정필터(보정),
          // **줌을 되살렸다** — 안 잘리니 얼굴로 밀고 들어가지 않는다.
          // 다만 `뼈대.json` 이 「줌없이」라고 표시한 사진만은 안 준다
          ...켄번스틀(i, 프레임, durationInFrames, 줌없이),
        }} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ── 멀티패널 — 세로 두 장을 나란히 ──────────────────────────
//
// **세로 사진이 107장(44%)이다.** 둘씩 묶으면 화면 수가 줄어
// 그만큼 한 장에 머무는 시간이 벌린다 (`00` 기획서).
const 멀티패널 = ({ srcs, i, 보정 }) => {
  const 프레임 = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = interpolate(프레임, [0, durationInFrames], [0, 1], {
    extrapolateRight: "clamp", easing: Easing.inOut(Easing.ease),
  });
  return (
    <AbsoluteFill style={{ backgroundColor: 바탕, overflow: "hidden" }}>
      <Img src={srcs[0]} style={{
        width: "100%", height: "100%", objectFit: "cover",
        filter: "blur(56px) brightness(0.34) saturate(0.6)", transform: "scale(1.2)",
      }} />
      <AbsoluteFill style={{
        flexDirection: "row", justifyContent: "center",
        alignItems: "center", gap: 28, padding: "48px 0",
      }}>
        {srcs.map((s, k) => (
          <Img key={k} src={s} style={{
            height: "100%", width: "auto", objectFit: "contain",
            boxShadow: "0 0 70px rgba(0,0,0,.8)",
            filter: 보정필터(보정 && 보정[k]),
            // 두 장이 **반대로** 움직인다. 같이 움직이면 한 장처럼 보인다
            transform: `scale(${interpolate(t, [0, 1], k === 0 ? [1.0, 1.05] : [1.05, 1.0])})`,
          }} />
        ))}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ── 컷 하나 ──────────────────────────────────────────────
const 컷하나 = ({ 컷, i, 경계인가 }) => {
  const 프레임 = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();
  // **악장이 바뀌는 자리는 길게 어두워진다.** 그 안에서는 짧게 겹친다
  const 겹침 = Math.max(3, Math.round(Math.min(0.4, durationInFrames / fps * 0.2) * fps));
  const 들어옴 = 경계인가 ? Math.round(fps * 0.8) : 겹침;
  const 나감 = 겹침;
  const 어둠 = Math.max(
    interpolate(프레임, [0, 들어옴], [1, 0], { extrapolateRight: "clamp" }),
    interpolate(프레임, [durationInFrames - 나감, durationInFrames], [0, 1],
      { extrapolateLeft: "clamp" }));
  const p = 컷.사진.map(사진경로);
  return (
    <AbsoluteFill>
      {컷.종류 === "멀티패널" ? <멀티패널 srcs={p} i={i} 보정={컷.보정} />
        : 컷.방향 === "세로" ? <세로한장 src={p[0]} i={i} 보정={컷.보정 && 컷.보정[0]} />
          : <가로한장 src={p[0]} i={i} 보정={컷.보정 && 컷.보정[0]}
              줌없이={Boolean(컷.줌없이)} />}
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: 어둠 }} />
    </AbsoluteFill>
  );
};

// ── 제목 ─────────────────────────────────────────────────
const 제목 = () => {
  const 프레임 = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();
  const 나옴 = (지연) => interpolate(
    프레임, [지연, 지연 + fps * 1.2, durationInFrames - fps * 1.6, durationInFrames - fps * 0.4],
    [0, 1, 1, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp",
      easing: Easing.inOut(Easing.ease) });
  return (
    <AbsoluteFill style={{
      backgroundColor: 바탕, justifyContent: "center", alignItems: "center",
    }}>
      <div style={{
        fontFamily: 글꼴, color: 흐린글자, fontSize: 24,
        letterSpacing: "0.42em", opacity: 나옴(fps * 0.3), marginBottom: 34,
      }}>2005 · DICIEMBRE</div>
      <div style={{
        fontFamily: 글꼴, color: 글자, fontSize: 92, fontWeight: 700,
        letterSpacing: "-0.01em", opacity: 나옴(fps * 1.0),
      }}>스페인 전람회의 그림</div>
      <div style={{
        width: 168, height: 1, backgroundColor: 흐린글자,
        margin: "40px 0", opacity: 나옴(fps * 2.0) * 0.6,
      }} />
      <div style={{
        fontFamily: 글꼴, color: 흐린글자, fontSize: 27, letterSpacing: "0.06em",
        opacity: 나옴(fps * 2.2),
      }}>Pictures at a Spanish Exhibition</div>
    </AbsoluteFill>
  );
};

// ── 악장 이름 — 악장이 바뀔 때 왼쪽 아래에 조용히 ────────────────
const 악장이름 = ({ 이름, 번호 }) => {
  const 프레임 = useCurrentFrame();
  const { fps } = useVideoConfig();
  const o = interpolate(프레임, [0, fps * 1.2, fps * 4.5, fps * 5.8],
    [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const 밀림 = interpolate(프레임, [0, fps * 1.2], [16, 0],
    { extrapolateRight: "clamp", easing: Easing.out(Easing.ease) });
  return (
    <AbsoluteFill style={{
      justifyContent: "flex-end", alignItems: "flex-start",
      padding: "0 0 74px 78px", opacity: o,
    }}>
      {/* **밝은 사진 위에서는 글자가 안 읽힌다.** 마드리드 벽화(빨강·파랑) 위에서
          로마 숫자가 사라졌다. 그래서 **왼쪽 아래에만 옅은 그늘**을 깐다 —
          사진을 어둡게 하는 게 아니라 **글자 뒤에만** 깔리므로 V2 와 무관하다 */}
      <AbsoluteFill style={{
        background: "linear-gradient(to top right, "
          + "rgba(0,0,0,.88) 0%, rgba(0,0,0,.55) 22%, rgba(0,0,0,0) 54%)",
      }} />
      <div style={{ transform: `translateY(${밀림}px)`, position: "relative" }}>
        {/* **로마 숫자를 썼다가 걷어냈다.** 1악장의 `I` 가 획 하나라
            벽화 위에서 아예 안 보였다. **읽히지 않는 것은 없는 것과 같다.** */}
        <div style={{
          fontFamily: 글꼴, color: 흐린글자, fontSize: 22,
          letterSpacing: "0.30em", marginBottom: 10,
          textShadow: "0 2px 20px rgba(0,0,0,.95)",
        }}>{번호}악장</div>
        <div style={{
          fontFamily: 글꼴, color: 글자, fontSize: 50, fontWeight: 600,
          textShadow: "0 2px 26px rgba(0,0,0,.95)",
        }}>{이름}</div>
      </div>
    </AbsoluteFill>
  );
};

// ── 프레임 번호를 미리 계산한다 ────────────────────────────────
//
// **반올림을 컷마다 따로 하면 한 프레임씩 빈다.** 그래서 시작 프레임만
// 반올림하고 **길이는 다음 컷의 시작에서 뺀다.** 마지막만 전체 길이에서 뺀다.
const 총프레임 = Math.round(뼈대.총길이 * 뼈대.fps);
const 컷들 = 뼈대.컷.map((c, i, a) => {
  const 시작 = Math.round(c.시작 * 뼈대.fps);
  const 끝 = i + 1 < a.length ? Math.round(a[i + 1].시작 * 뼈대.fps) : 총프레임;
  return { ...c, 시작프레임: 시작, 길이프레임: Math.max(1, 끝 - 시작) };
});
const 악장첫컷 = new Set(
  뼈대.악장.map((m) => 컷들.findIndex((c) => c.악장 === m.번호)).filter((x) => x >= 0));

export const 전곡 = () => (
  <AbsoluteFill style={{ backgroundColor: 바탕 }}>
    <필터정의 />
    {/* **음악이 기준이다.** 사진은 이 위에 얹힌다 */}
    <Audio src={staticFile("음악.mp3")} />

    {컷들.map((c, i) => (
      <Sequence key={i} from={c.시작프레임} durationInFrames={c.길이프레임}>
        {c.종류 === "제목" ? <제목 />
          : <컷하나 컷={c} i={i} 경계인가={악장첫컷.has(i)} />}
      </Sequence>
    ))}

    {/* 악장 이름 — 악장이 시작하고 6초 동안 */}
    {뼈대.악장.filter((m) => m.번호 !== 0).map((m) => (
      <Sequence key={m.번호} from={Math.round(m.시작 * 뼈대.fps)}
        durationInFrames={Math.round(뼈대.fps * 6)}>
        <악장이름 이름={m.이름} 번호={m.번호} />
      </Sequence>
    ))}
  </AbsoluteFill>
);

export const 총길이프레임 = 총프레임;
export const FPS = 뼈대.fps;
