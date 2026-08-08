const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  TableOfContents, PageBreak, LevelFormat, PageOrientation,
} = require("docx");
const fs = require("fs");

const KO = "Noto Sans CJK KR";
const ACCENT = "8C2F1E";   // deep spanish red
const INK = "1A1A1A";
const GREY = "666666";
const RULE = "D8D0C8";

/* ------------------------------------------------------------------ helpers */
const P = (text, o = {}) => new Paragraph({
  alignment: o.align,
  spacing: { before: o.before ?? 0, after: o.after ?? 120, line: o.line ?? 300 },
  indent: o.indent,
  numbering: o.numbering,
  border: o.border,
  children: [new TextRun({
    text, font: KO, size: o.size ?? 20, bold: o.bold, italics: o.italics,
    color: o.color ?? INK,
  })],
});

const RICH = (runs, o = {}) => new Paragraph({
  alignment: o.align,
  spacing: { before: o.before ?? 0, after: o.after ?? 120, line: o.line ?? 300 },
  indent: o.indent,
  numbering: o.numbering,
  children: runs.map(r => new TextRun({
    text: r.t, font: KO, size: r.size ?? o.size ?? 20, bold: r.b,
    italics: r.i, color: r.c ?? o.color ?? INK,
  })),
});

const H1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 400, after: 200 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 10, color: ACCENT, space: 6 } },
  children: [new TextRun({ text, font: KO, size: 28, bold: true, color: ACCENT })],
});

const H2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 300, after: 140 },
  children: [new TextRun({ text, font: KO, size: 23, bold: true, color: INK })],
});

const BULLET = (text, lvl = 0) => P(text, {
  numbering: { reference: "bul", level: lvl }, after: 70, line: 290,
});

const RULE_P = () => new Paragraph({
  spacing: { before: 60, after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE, space: 1 } },
  children: [new TextRun({ text: "", font: KO, size: 2 })],
});

/* table builder: cols = array of dxa widths */
const CONTENT_W = 9406;   // A4 width 11906 − left 1250 − right 1250

function TBL(cols0, rows, opt = {}) {
  // normalise the supplied ratios to the full text width
  const raw = cols0.reduce((a, b) => a + b, 0);
  const cols = cols0.map(c => Math.round(c * CONTENT_W / raw));
  cols[cols.length - 1] += CONTENT_W - cols.reduce((a, b) => a + b, 0);
  const total = cols.reduce((a, b) => a + b, 0);
  return new Table({
    columnWidths: cols,
    width: { size: total, type: WidthType.DXA },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
      right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      insideVertical: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    },
    rows: rows.map((cells, ri) => new TableRow({
      tableHeader: ri === 0,
      children: cells.map((c, ci) => {
        const isH = ri === 0;
        const isTotal = opt.totalRow && ri === rows.length - 1;
        return new TableCell({
          width: { size: cols[ci], type: WidthType.DXA },
          shading: isH
            ? { type: ShadingType.CLEAR, fill: "F2EDE8", color: "auto" }
            : isTotal
              ? { type: ShadingType.CLEAR, fill: "FAF7F4", color: "auto" }
              : undefined,
          margins: { top: 70, bottom: 70, left: 110, right: 110 },
          children: String(c).split(" ").map((line, li) => new Paragraph({
            alignment: (opt.center || []).includes(ci) ? AlignmentType.CENTER : AlignmentType.LEFT,
            spacing: { before: li ? 40 : 0, after: 0, line: 260 },
            children: [new TextRun({
              text: line, font: KO, size: opt.size ?? 18,
              bold: isH || isTotal || (li === 0 && opt.boldFirstCol && ci === 0),
              color: isH ? ACCENT : INK,
            })],
          })),
        });
      }),
    })),
  });
}

/* ------------------------------------------------------------------ content */
const kids = [];

/* --- cover --- */
kids.push(
  new Paragraph({ spacing: { before: 1400, after: 0 }, children: [
    new TextRun({ text: "MUSIC VIDEO PROJECT  ·  PHASE 0", font: KO, size: 17, color: GREY, characterSpacing: 60 })] }),
  new Paragraph({ spacing: { before: 200, after: 0 }, children: [
    new TextRun({ text: "스페인 전람회의 그림", font: KO, size: 60, bold: true, color: ACCENT })] }),
  new Paragraph({ spacing: { before: 80, after: 0 }, children: [
    new TextRun({ text: "Pictures at a Spanish Exhibition", font: KO, size: 26, italics: true, color: GREY })] }),
  new Paragraph({
    spacing: { before: 280, after: 0 },
    border: { top: { style: BorderStyle.SINGLE, size: 12, color: ACCENT, space: 10 } },
    children: [new TextRun({ text: "", font: KO, size: 2 })] }),
  P("2005년 12월 스페인 여행 기록 — 사진 253장 · 플라멩코 영상 9편", { size: 22, before: 200 }),
  P("무소르그스키의 프롬나드 구조 위에 르네상스의 음색을 얹은 9분 40초 심포닉 프로그레시브 뮤직비디오", { size: 20, color: GREY, after: 600 }),
  TBL([1600, 4600], [
    ["항목", "내용"],
    ["문서", "Phase 0 기획서 (검수용)"],
    ["작성일", "2026-08-05"],
    ["작성", "Claude"],
    ["검수자", "JinYong"],
    ["상태", "승인 대기"],
  ], { boldFirstCol: true }),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- TOC --- */
kids.push(
  H1("목차"),
  new TableOfContents("목차", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- 1. 개요 --- */
kids.push(
  H1("1. 프로젝트 개요"),
  P("2005년 12월 스페인 여행에서 남은 사진 253장과 플라멩코 공연 영상 9편으로 9분 40초 분량의 뮤직비디오를 만든다. 배경음악은 기성 음원을 쓰지 않고 직접 작곡·편곡·합성한다."),
  P("소재가 20년 전 콤팩트 디지털카메라 기록이라 해상도 한계가 이 프로젝트의 가장 큰 제약이다. 따라서 화질을 끌어올리는 작업과, 낮은 화질이 흠으로 보이지 않게 만드는 연출을 동시에 설계한다."),
  H2("1.1 핵심 사양"),
  TBL([1500, 4700], [
    ["항목", "값"],
    ["최종 길이", "9분 40초 (580초)"],
    ["화면비 · 해상도", "16:9 · 1920×1080 (업스케일 후 3840×2160 검토)"],
    ["프레임레이트", "30 fps"],
    ["음악", "B♭장조 프롬나드 주제 기반 다악장 조곡, 5/4↔6/4 교대"],
    ["오디오", "48 kHz 스테레오, 라우드니스 −14 LUFS (스트리밍 기준)"],
    ["납품 형식", "H.264 MP4 마스터 + 음원 단독 WAV/MP3"],
  ], { boldFirstCol: true }),
);

/* --- 2. 컨셉 --- */
kids.push(
  H1("2. 컨셉 — 왜 《전람회의 그림》인가"),
  P("무소르그스키의 《전람회의 그림》에서 프롬나드는 미술관에서 그림과 그림 사이를 걸어가는 관람객이다. 각 악장이 한 폭의 그림이고, 프롬나드가 그 사이마다 모습을 바꿔 돌아온다."),
  RICH([
    { t: "이 구조를 그대로 대입한다. " },
    { t: "관람객 = 여행자, 그림 = 도시.", b: true },
    { t: " 마드리드에서 바르셀로나까지 여섯 도시가 여섯 폭의 그림이고, 프롬나드는 도시 사이의 이동 구간에서 돌아온다. 돌아올 때마다 편성이 달라져 여행자가 지쳐가는 과정, 익숙해지는 과정을 드러낸다." },
  ]),
  H2("2.1 이 구조가 해결하는 문제"),
  BULLET("9분 40초를 지루하지 않게 버티는 문제 — 여섯 개의 독립된 악장으로 쪼개되 프롬나드 주제가 전체를 하나로 묶는다."),
  BULLET("편집 문법 문제 — 프롬나드 구간은 이동·타이틀·전환에, 각 악장은 그 도시의 사진에 배정된다. 음악 구조가 곧 편집 구조다."),
  BULLET("박자 문제 — 프롬나드 원곡은 5/4와 6/4를 번갈아 쓴다. 이 불규칙성은 \"일정하지 않은 걸음걸이\"를 표현한 장치이고, 여행 영상의 리듬과 정확히 같은 성질이다."),
  BULLET("스페인 연결 문제 — 세비야 악장에서 프롬나드 주제를 E 프리지안으로 변형한다. 프리지안은 플라멩코의 음계이므로, 같은 선율이 안달루시아에 도착하는 순간 스페인 음악이 된다. ELP가 원곡 주제를 다루던 방식과 같다."),
  H2("2.2 참조와 저작권"),
  TBL([1750, 900, 1000, 2550], [
    ["대상", "연도", "지위", "사용 범위"],
    ["무소르그스키 《전람회의 그림》", "1874", "퍼블릭 도메인 (작곡자 1881년 사망)", "원곡 선율을 그대로 인용 가능. IMSLP 공개 악보에서 직접 채보해 편곡한다."],
    ["ELP 《Pictures at an Exhibition》", "1971", "편곡 저작권 유효", "원곡이 퍼블릭 도메인이어도 ELP의 편곡은 보호된다. 참조하지 않고 원본 악보에서 직접 편곡한다."],
    ["Renaissance 〈Mother Russia〉", "1974", "저작권 유효 (Dunford / Thatcher)", "음색·편성·전개 방식만 참조한다. 선율 인용은 하지 않는다."],
  ], { size: 17 }),
  P("결과적으로 완성 음원의 저작권은 전적으로 이 프로젝트에 귀속되며, 유튜브 등 어디에 올려도 권리 주장이 걸리지 않는다.", { before: 140, italics: true, color: GREY }),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- 3. 음악 설계 --- */
kids.push(
  H1("3. 음악 설계"),
  H2("3.1 프롬나드 주제 — 확인된 사실"),
  TBL([1500, 4700], [
    ["항목", "값"],
    ["조성", "B♭장조 (100% 온음계, 화성 외 음 없음)"],
    ["박자", "5/4와 6/4 교대 — 제시부 한 프레이즈가 11박"],
    ["원곡 템포", "약 100 BPM (Allegro giusto, nel modo russico)"],
    ["선율 음역", "F4 – F5 (1옥타브)"],
    ["선율 성격", "순차진행 중심, 반복적, 73%가 화음 구성음"],
    ["화성", "vi – V6 등 전위·부속화음을 쓰는 단순하지만 유려한 진행"],
  ], { boldFirstCol: true }),
  P("정확한 음정은 Phase 1 착수 시 IMSLP 퍼블릭 도메인 악보에서 채보해 확정한다. 위 항목은 이미 교차 확인된 사실이며, 이 범위 안에서 편곡 설계가 가능하다.", { before: 140, size: 18, color: GREY }),

  H2("3.2 3성부 분리 — 데모의 실패 원인과 수정"),
  P("30초 데모는 오르간과 베이스를 같은 음으로 유니즌 배치했다. 그래서 \"건반이 주역인지 베이스가 주역인지\" 구분되지 않는 한 덩어리로 뭉쳤다. 늘어지게 들린 것도 BPM 때문이 아니라 화성이 1.875초에 한 번만 바뀌었기 때문이다."),
  P("수정 원칙 — 세 성부가 각자 다른 일을 한다.", { bold: true, before: 100 }),
  TBL([1200, 2500, 2500], [
    ["성부", "데모 (문제)", "수정 후"],
    ["건반", "베이스와 같은 음", "주역. 선율과 화성을 동시에 담당"],
    ["베이스", "루트만 유니즌", "독립된 대선율. Jon Camp식 리드 베이스"],
    ["드럼", "단순 반복 패턴", "하나의 목소리. 악장별로 성격이 바뀜"],
  ], { size: 18 }),
  P("템포 대응 — 기본 템포를 올리고 화성 변화를 반 마디로 촘촘하게 하며, 하이햇을 16분으로 쪼갠다. 격렬한 악장에서는 7/8을 써서 더 조인다.", { before: 140 }),

  H2("3.3 악기 편성"),
  P("〈Mother Russia〉의 편성이 기준이다 — 현악 주도 도입에 피아노 액센트, 무가사 보칼리즈, 아코스틱 기타 간주. 여기에 ELP의 오르간과 무그를 격렬한 악장용으로 얹는다. 아코스틱 기타가 스페인 나일론 기타와 같은 악기군이라 두 참조가 자연스럽게 이어진다."),
  TBL([1500, 1900, 2800], [
    ["성부", "참조 연주자", "합성 방식 / 상태"],
    ["피아노", "John Tout, Keith Emerson", "가산합성 + 현 비조화성 + 해머 노이즈 · 신규 구축"],
    ["현악 앙상블", "Jimmy Horowitz 편곡", "8성부 디튠 소톱 + 보디 레조넌스 + 느린 어택 · 신규 구축"],
    ["아코스틱 / 나일론 기타", "Michael Dunford", "Karplus-Strong 물리모델링 · 신규 구축"],
    ["해먼드 오르간", "Keith Emerson", "드로바 9단 가산합성 + 레슬리 로터리 · 구축 완료"],
    ["무그 리드", "Keith Emerson", "래더 필터 스윕 + 포르타멘토 · 구축 완료"],
    ["리드 베이스", "Jon Camp", "독립 대선율, 리켄배커 톤 · 개선 필요"],
    ["드럼", "Carl Palmer, Terence Sullivan", "합성 킷 · 구축 완료, 패턴 재설계 필요"],
    ["팔마스 · 카혼", "세비야 악장 한정", "필터드 노이즈 버스트 · 신규 구축"],
    ["보칼리즈", "Annie Haslam", "미결정 — 4장 참조"],
  ], { size: 17 }),

  H2("3.4 악장 구성표"),
  TBL([420, 1750, 700, 1100, 2230], [
    ["#", "악장", "길이", "사진", "성격"],
    ["0", "Promenade — 제시", "0:50", "마드리드 광각", "현악 주도, 피아노 액센트. B♭장조 5/4↔6/4. 타이틀 타이포"],
    ["1", "마드리드", "0:40", "13장", "피아노 리드, 도시의 활기. 알레그로"],
    ["2", "Promenade — 변주 I", "0:15", "이동 인서트", "아코스틱 기타 독주로 축소"],
    ["3", "세고비아", "0:55", "25장", "로마 수도교와 알카사르. 장중한 오르간 코랄"],
    ["4", "세비야 — 플라멩코", "1:40", "27장 + 영상 55초", "프롬나드 주제를 E 프리지안으로 변형. 컴파스, 팔마스, 무그 리드"],
    ["5", "Promenade — 변주 II", "0:15", "이동 인서트", "현악 단조. 지친 걸음"],
    ["6", "론다", "0:50", "27장", "협곡과 다리. 광활한 현악 아다지오"],
    ["7", "그라나다 — 알함브라", "1:40", "77장", "보칼리즈 구간. 무가사 소프라노 또는 무그 대체"],
    ["8", "바르셀로나 — 가우디", "1:40", "84장", "격렬한 7/8 변박. 오르간과 무그 총주"],
    ["9", "The Great Gate — 피날레", "0:55", "전체 회상", "프롬나드 대주제 총주. 엔딩 크레딧"],
    ["", "합계", "9:40", "253장", ""],
  ], { size: 17, totalRow: true, center: [0, 2, 3] }),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- 4. 영상 설계 --- */
kids.push(
  H1("4. 영상 설계"),
  H2("4.1 소재 실측"),
  TBL([1900, 700, 700, 700, 900, 1300], [
    ["폴더", "총", "가로", "세로", "고해상", "배정 악장"],
    ["2005.12.08 마드리드", "13", "13", "0", "5", "1"],
    ["2005.12.09 세고비아", "25", "19", "6", "0", "3"],
    ["2005.12.10 세비야", "27", "17", "10", "0", "4"],
    ["2005.12.10 세비야 탱고영상", "9편", "—", "—", "—", "4"],
    ["2005.12.11 론다", "27", "19", "8", "0", "6"],
    ["2005.12.12 그라나다", "77", "41", "36", "1", "7"],
    ["2005.12.13 바르셀로나", "31", "13", "18", "1", "8"],
    ["2005.12.14 바르셀로나", "53", "22", "31", "3", "8"],
    ["합계", "253", "144", "109", "10", ""],
  ], { size: 17, totalRow: true, center: [1, 2, 3, 4, 5] }),
  P("사진 해상도는 1024×768이 131장, 768×1024 세로가 108장이다. 1500만 화소 이상 고해상은 10장뿐이다. 탱고 영상은 320×240 MJPEG 무음, 각 15초.", { before: 140, size: 18 }),
  RICH([{ t: "여기서 두 가지가 결정된다. ", }, { t: "1080p조차 이미 업스케일이라는 것", b: true }, { t: ", 그리고 " }, { t: "세로 사진 109장(43%)은 16:9 화면을 채울 수 없다는 것", b: true }, { t: "이다." }], { before: 100 }),

  H2("4.2 세로 사진 전략 — 멀티패널"),
  P("세로 사진을 좌우 잘라내면 43%의 소재에서 구도가 망가진다. 대신 세로 사진 2~3장을 한 화면에 나란히 배치한다."),
  BULLET("세로 3장 병치는 프로그레시브 앨범 재킷의 관습적인 레이아웃이라 장르와도 맞는다."),
  BULLET("109장을 55개 패널로 묶으면 유효 샷 수가 253개에서 199개로 줄어, 컷당 시간이 1.5초에서 1.9초로 늘어난다. 이것이 그라나다 77장과 바르셀로나 84장을 소화할 수 있게 만드는 유일한 방법이다."),
  BULLET("잔여 여백은 같은 사진을 확대·블러 처리해 채운다. 검은 여백보다 화면이 덜 비어 보인다."),

  H2("4.3 영상 문법"),
  TBL([1500, 4700], [
    ["장치", "적용"],
    ["컷 타이밍", "음악의 마디·박 그리드에 맞춰 자른다. 데모 검증에서 온그리드 어택 에너지가 오프그리드의 2.4배로 확인됨"],
    ["켄번스", "정지 사진에 완만한 줌·팬. 악장 성격에 따라 속도를 달리한다"],
    ["타이포그래피", "악장 제목, 도시명, 날짜. 프롬나드 구간에 배치해 음악 구조와 일치시킨다"],
    ["컬러 그레이딩", "악장별로 다른 룩. 세비야는 따뜻한 적색, 론다는 청회색, 그라나다는 황금빛"],
    ["필름 그레인 · 비네트", "저해상도를 의도된 질감으로 전환한다. 화질 결함을 감추는 가장 효과적인 수단"],
    ["멀티패널 · 스플릿", "세로 사진 처리 및 리듬 변화용"],
  ], { size: 18 }),
  P("직접 제작으로 가능한 범위는 위까지다. 새 인물 영상 생성, 등장인물 추가, 립싱크는 외부 도구가 필요하다.", { before: 140, bold: true }),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- 5. 도구 --- */
kids.push(
  H1("5. 도구 파이프라인"),
  P("2026년 8월 기준으로 영상 생성 모델의 절대 우위는 없다. 다만 이 프로젝트에서는 모델 선택보다 파이프라인 순서가 중요하다. 1024×768 원본은 이 모델들이 기대하는 입력 해상도에 미달하므로, 업스케일이 선택이 아니라 전제 조건이다."),
  TBL([1200, 1900, 1150, 1950], [
    ["단계", "도구", "비용", "판단"],
    ["음원 합성", "자체 신디사이저 (numpy / scipy)", "무료", "확정. 전액 보유권"],
    ["사진 업스케일", "Topaz Gigapixel / Photo (Starlight 모델)", "일회성", "필수. 저해상도 복원 전용 모델이 있다"],
    ["영상 업스케일", "Topaz Video (Starlight / Iris)", "구독", "권장. 320×240을 그대로 확대하면 뭉개진다"],
    ["사진 → 영상", "Kling 3.0 — 해상도·디테일, 캐릭터 일관성, 15초 멀티샷", "월 $7.99~ 또는 초당 $0.10", "히어로 샷 10~20장만 제한 사용"],
    ["", "Seedance 2.0 — 레퍼런스 기반 제어. 움직임을 지정한 대로", "종량제", "인물 움직임을 통제해야 할 때"],
    ["", "Veo 3.1 — 시네마틱 품질 1위, 네이티브 4K, 48 kHz 오디오, 립싱크 최상", "초당 $0.75~", "보컬·인물 확정 후에만"],
    ["편집 · 그레이딩 · 타이포", "ffmpeg (자체 스크립트)", "무료", "확정"],
  ], { size: 17 }),
  P("권장 조합 — Topaz로 전량 업스케일한 뒤, 각 악장의 히어로 샷 10~20장만 Kling 3.0 또는 Seedance 2.0으로 움직이는 샷으로 만든다. 253장 전부에 적용하지 않는 이유는 6장에 적었다.", { before: 140, italics: true }),
);

/* --- 6. 리스크 --- */
kids.push(
  H1("6. 리스크"),
  TBL([420, 1750, 2300, 1730], [
    ["#", "리스크", "내용", "대응"],
    ["1", "해상도 한계", "253장 중 고해상은 10장. 1080p도 업스케일", "Topaz 복원 + 그레인·비네트로 질감 전환"],
    ["2", "AI 영상의 환각", "생성 모델이 원본에 없던 디테일을 만들어낸다. 개인 여행 기록에서는 \"내 기억이 아닌 장면\"이 된다", "히어로 샷 10~20장으로 제한. 인물 얼굴이 큰 사진은 제외"],
    ["3", "탱고 영상 품질", "320×240 무음, 1440×1080으로 늘리면 흐릿하다", "작은 프레임 + 블러 배경 배치, 또는 그레인으로 감춤"],
    ["4", "보컬 미결정", "인스트루멘털 / 직접 녹음 / AI 보컬 세 갈래가 편곡을 바꾼다", "Phase 1 종료 시점까지 결정. 7악장 보칼리즈가 분기점"],
    ["5", "합성 음원의 한계", "실연주 녹음 수준은 아니다. 특히 피아노와 현악은 합성 난도가 높다", "Phase 1 검수에서 조기 판정. 필요하면 AI 음악 도구로 전환"],
    ["6", "저작권", "르네상스·ELP 참조가 인용으로 넘어가면 문제", "선율 인용은 퍼블릭 도메인 무소르그스키로만 한정"],
  ], { size: 17, center: [0] }),
);

/* --- 7. 일정 --- */
kids.push(
  H1("7. 일정 및 검수 게이트"),
  TBL([1050, 1200, 2350, 1600], [
    ["Phase", "단계", "산출물", "검수 게이트"],
    ["0", "기획", "본 문서 — 트리트먼트, 악장 구성표, 사양서", "✔ 기획 승인"],
    ["1", "음악", "3성부 분리 데모 60초 → 전곡 편곡 → 믹스·마스터", "✔ 데모 승인 ✔ 전곡 승인"],
    ["2", "소재 정리", "253장 셀렉·등급, 업스케일, 컬러 기준 확정", "—"],
    ["3", "스토리보드", "악장별 샷리스트, 음악 타임코드에 샷 매핑", "✔ 스토리보드 승인"],
    ["4", "편집", "러프컷 → 파인컷", "✔ 러프컷 리뷰"],
    ["5", "마감", "그레이딩, 타이포, 그레인, 납품 마스터", "✔ 최종 검수"],
  ], { size: 18, center: [0] }),
  P("각 게이트에서 승인이 나오기 전까지 다음 단계로 넘어가지 않는다. 특히 Phase 1의 데모 승인이 가장 중요하다 — 여기서 합성 음원의 품질이 목표에 못 미친다고 판단되면 도구 전략을 바꿔야 하고, 그 결정이 늦어질수록 손실이 커진다.", { before: 140 }),
);

/* --- 8. 결정 대기 --- */
kids.push(
  H1("8. 결정 대기 항목"),
  TBL([420, 1750, 2400, 1630], [
    ["#", "항목", "선택지", "필요 시점"],
    ["1", "보컬", "인스트루멘털 / 직접 녹음 / AI 보컬 (Synthesizer V, ACE Studio, Suno Premier)", "Phase 1 종료"],
    ["2", "외부 도구 예산", "전액 무료 / 업스케일까지 / 영상 생성까지", "Phase 2 착수"],
    ["3", "최종 해상도", "1080p 확정 / 업스케일 후 4K 시도", "Phase 2 착수"],
    ["4", "여행자 등장", "사진 속 인물 그대로 / AI로 움직이는 샷 생성", "Phase 3 스토리보드"],
  ], { size: 18, center: [0] }),
  RULE_P(),
  P("다음 작업 — 기획 승인 후 Phase 1로 넘어가 피아노·현악·나일론 기타 합성기를 구축하고, 프롬나드 주제를 채보해 3성부가 분리된 60초 데모를 만든다. 데모는 0악장 제시부와 4악장 세비야 프리지안 변형을 붙여, 조곡 전체의 성격을 한 번에 판단할 수 있게 구성한다.", { bold: true }),
);

/* ------------------------------------------------------------------ document */
const doc = new Document({
  creator: "Claude",
  title: "스페인 전람회의 그림 — 뮤직비디오 제작 기획서",
  description: "Phase 0 기획서",
  styles: {
    default: {
      document: { run: { font: KO, size: 20, color: INK } },
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: KO, size: 28, bold: true, color: ACCENT } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: KO, size: 23, bold: true, color: INK } },
    ],
  },
  numbering: {
    config: [{
      reference: "bul",
      levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 340, hanging: 200 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 680, hanging: 200 } } } },
      ],
    }],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },       // A4
        margin: { top: 1300, bottom: 1200, left: 1250, right: 1250 },
      },
    },
    children: kids,
  }],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync("기획서_스페인전람회의그림.docx", b);
  console.log("written", b.length, "bytes");
});
