"""Cut a 30s demo music video: photos cut on the 5/4 bar grid + tango footage."""
import os
import subprocess
import glob

ROOT = "/sessions/epic-relaxed-ride/mnt/MusicVideo/2005년 12월 스페인"
OUT = "/sessions/epic-relaxed-ride/mnt/outputs"
BAR = 1.875
W, H = 1440, 1080

# one representative photo per bar, roughly following the trip
picks = []


def take(folder, n, step=1, start=0):
    fs = sorted(glob.glob(os.path.join(ROOT, folder, "*.JPG")))
    return fs[start::step][:n]


picks += take("2005.12.08-마드리드", 2, step=3)
picks += take("2005.12.09-세고비아", 2, step=6)
picks += take("2005.12.10-세비야", 3, step=7)
picks += take("2005.12.11-론다", 3, step=8)
picks += take("2005.12.12-그라나다", 3, step=20)
picks += take("2005.12.13-바르셀로나", 2, step=12)
picks += take("2005.12.14-바르셀로나", 2, step=20)
print(len(picks), "photos")

tango = sorted(glob.glob(os.path.join(ROOT, "2005.12.10-세비야 탱고동영상", "*.MOV")))

os.makedirs(f"{OUT}/clips", exist_ok=True)
seq = []

# --- bars 0-1: two slow Ken Burns establishing shots (3.75 s of fanfare)
plan = []
for i, p in enumerate(picks[:2]):
    plan.append(("img", p, BAR, 0.10))          # slow zoom
# --- bars 2-7: riff, one photo per bar
for p in picks[2:8]:
    plan.append(("img", p, BAR, 0.16))
# --- bars 8-9: tango footage during the moog lead entry
plan.append(("vid", tango[1], BAR * 2, 0))
# --- bars 10-13: faster - half-bar cuts
for p in picks[8:16]:
    plan.append(("img", p, BAR / 2, 0.20))
# --- bars 14-15: tango finale
plan.append(("vid", tango[3], BAR * 2, 0))

t_total = sum(d for _, _, d, *_ in plan)
print("planned video length %.2fs (%.1f bars)" % (t_total, t_total / BAR))

for i, item in enumerate(plan):
    kind, src, dur = item[0], item[1], item[2]
    out = f"{OUT}/clips/c{i:03d}.mp4"
    if kind == "img":
        z = item[3]
        frames = int(dur * 30)
        vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
              f"crop={W*2}:{H*2},"
              f"zoompan=z='1+{z}*on/{frames}':d={frames}:s={W}x{H}:fps=30,"
              f"eq=contrast=1.06:saturation=1.14:gamma=1.03,"
              f"unsharp=5:5:0.6")
        cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", src,
               "-t", f"{dur}", "-vf", vf, "-r", "30",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-an", out]
    else:
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"eq=contrast=1.10:saturation=1.20:gamma=1.10,"
              f"unsharp=5:5:1.0,fps=30")
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", src, "-t", f"{dur}",
               "-vf", vf, "-r", "30",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-an", out]
    subprocess.run(cmd, check=True)
    seq.append(out)

with open(f"{OUT}/clips/list.txt", "w") as f:
    for s in seq:
        f.write(f"file '{s}'\n")

subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                "-i", f"{OUT}/clips/list.txt", "-c", "copy",
                f"{OUT}/video_silent.mp4"], check=True)

subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{OUT}/video_silent.mp4",
                "-i", f"{OUT}/demo.wav", "-map", "0:v", "-map", "1:a",
                "-c:v", "libx264", "-crf", "19", "-preset", "medium",
                "-c:a", "aac", "-b:a", "224k", "-shortest",
                f"{OUT}/demo_musicvideo.mp4"], check=True)
print("done")
