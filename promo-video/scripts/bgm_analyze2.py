import json
import numpy as np
import librosa

files = [
    r"F:\实训伴学4\promo-video\public\audio\bgm\fs-629161.mp3",
    
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
        residual = beats - (t0 + i * T)
        rec.update({"bpm_fit": round(60.0 / T, 3), "t0": round(float(t0), 4),
                    "T": round(float(T), 5),
                    "resid_ms_max": round(float(np.abs(residual).max() * 1000), 1),
                    "resid_ms_std": round(float(residual.std() * 1000), 1)})
        # 切点落在拍网上的最近距离（用拟合网格，帧）
        cuts = [0, 220, 275, 465, 565, 620, 725, 775, 885, 940, 1085]
        Tf = T * 30.0
        rec["cut_beat_error_frames"] = [
            round(abs(c / Tf - round(c / Tf)) * Tf, 1) for c in cuts]
    oenv = librosa.onset.onset_strength(y=y, sr=sr)
    rec["onset_peak_over_mean"] = round(float(oenv.max() / (oenv.mean() + 1e-9)), 2)
    out.append(rec)

print(json.dumps(out, ensure_ascii=False, indent=1))