import {Config} from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);

// **색 범위를 방송 규격(제한 범위)으로 못박는다.**
//
// 안 주면 `yuvj420p` · `color_range=pc`(full) 가 나온다 — 프레임을 JPEG 로 뽑는데
// JPEG 이 풀레인지이기 때문이다. **`--pixel-format=yuv420p` 로는 안 고쳐진다**
// (2026-08-23 실측 — 줘도 `pc` 그대로였다).
//
// 유튜브 규격이 `yuv420p` 이고, 이 프로젝트의 `영상검증.py` 도 그것을 본다.
Config.setColorSpace("bt709");
