import sys, json
import numpy as np
import librosa

files = [
    r"F:\实训伴学4\promo-video\public\audio\bgm\fs-700896.mp3",
    r"F:\实训伴学4\promo-video\public\audio\bgm\fs-554602.mp3",
    r"F:\实训伴学4\promo-video\public\audio\bgm\fs-632131.mp3",
    r"F:\实训伴学4\promo-video\public\audio\bgm\fs-826622.mp3",
]

out = []
for f in files:
    y, sr = librosa.load(f, sr=None, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, tightness=400, units="time")
    dur = len(y) / sr
    rec = {"file": f.split("\\")[-1], "duration": round(dur, 2),
           "tempo_scalar": float(np.atleast_1d(tempo)[0]), "n_beats": int(len(beats))}
    if len(beats) > 4:
        i = np.arange(len(beats))
        A = np.vstack([i, np.ones_like(i)]).T
        (T, t0), *_ = np.linalg.lstsq(A, beats, rcond=None)
        rec.update({"bpm_fit": round(60.0 / T, 3), "t0": round(float(t0), 4),
                    "T": round(float(T), 5),
                    "resid_ms": round(float(np.abs(beats - (t0 + i * T)).max() * 1000), 1)})
    # 瞬态强度：onset envelope 的峰值/均值比，判断"有没有清晰鼓点"
    oenv = librosa.onset.onset_strength(y=y, sr=sr)
    rec["onset_peak_over_mean"] = round(float(oenv.max() / (oenv.mean() + 1e-9)), 2)
    rec["onset_rate_per_s"] = round(float(len(librosa.onset.onset_detect(onset_envelope=oenv, sr=sr)) / dur), 2)
    # 动态：RMS 波动
    rms = librosa.feature.rms(y=y)[0]
    rec["rms_db_range"] = round(float(20 * np.log10((rms.max() + 1e-9) / (rms.mean() + 1e-9))), 1)
    out.append(rec)

print(json.dumps(out, ensure_ascii=False, indent=1))