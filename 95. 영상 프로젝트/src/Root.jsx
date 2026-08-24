// **어떤 영상들이 있는가**를 Remotion 에 알려준다.
//
// `전곡` 은 10분 19.84초 전부이고, `발췌` 는 **악장이 바뀌는 자리만 골라 본 것**이다.
// 10분을 굽는 데 40분이 걸리므로, 확인은 발췌로 하고 전곡은 마지막에 한 번 굽는다.
import { Composition } from "remotion";
import { 전곡, 총길이프레임, FPS } from "./Video.jsx";

export const Root = () => (
  <>
    <Composition
      id="jeongok"
      component={전곡}
      durationInFrames={총길이프레임}
      fps={FPS}
      width={1920}
      height={1080}
    />
  </>
);
