import json
import subprocess
import numpy as np
import librosa

SR = 22050


def load(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


a = load(r"F:\实训伴学4\promo-video\out\promo.mp4")
b = load(r"F:\实训伴学4\promo-video\out\promo-nobgm.mp4")
n = min(len(a), len(b))
a, b = a[:n], b[:n]
diff = a - b
fps = 30.0

print(f"len_a={len(a)/SR:.2f}s len_b={len(b)/SR:.2f}s")
print(f"bgm-vs-nobgm |diff| rms={np.sqrt((diff**2).mean()):.5f}  a_rms={np.sqrt((a**2).mean()):.5f} b_rms={np.sqrt((b**2).mean()):.5f}")

# BGM 电平：取 165–190f（主角卡悬停、SFX 间隙）
s, e = int(165 / fps * SR), int(190 / fps * SR)
seg_a, seg_b = a[s:e], b[s:e]
rms_a, rms_b = np.sqrt((seg_a**2).mean()), np.sqrt((seg_b**2).mean())
print(f"window 165-190f: with_bgm={20*np.log10(rms_a+1e-9):.1f} dBFS  nobgm={20*np.log10(rms_b+1e-9):.1f} dBFS  bgm_only={20*np.log10(np.sqrt(((seg_a-seg_b)**2).mean())+1e-9):.1f} dBFS")

# BGM 拍网与 20f 梳状网格的同相检验
oenv = librosa.onset.onset_strength(y=diff, sr=SR, hop_length=256)
times = librosa.frames_to_time(np.arange(len(oenv)), sr=SR, hop_length=256)
peaks = librosa.util.peak_pick(oenv, pre_max=3, post_max=3, pre_avg=8, post_avg=8, delta=0.3, wait=5)
pt = times[peaks]

def score(phase_frames, period=20.0):
    if len(pt) == 0:
        return 0.0
    d = np.abs(((pt * fps - phase_frames + period / 2) % period) - period / 2)
    return float(np.mean(np.exp(-(d ** 2) / (2 * 1.5 ** 2))))

best = max(((p, score(p)) for p in np.arange(0, 20, 0.25)), key=lambda x: x[1])
print(f"bgm onsets={len(pt)}  comb_score(phase=0.19f)={score(0.19):.3f}  best={best[1]:.3f}@phase={best[0]:.2f}f  mean_score_all_phases={np.mean([score(p) for p in np.arange(0,20,0.25)]):.3f}")
print("peak times (s, first 12):", [round(float(t), 3) for t in pt[:12]])
print("peak frames (first 12):", [round(float(t * fps), 1) for t in pt[:12]])