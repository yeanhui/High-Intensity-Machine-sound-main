#!/usr/bin/env python3
"""Factory Acoustic Monitor - machine sound frequency recorder (desktop version).

Live microphone analysis for industrial condition monitoring:
  * FFT spectrum with spectral-centroid marker
  * Scrolling spectrogram
  * Acoustic-feature trail (time x centroid, sized by level, colored by spread)
  * Per-frame feature logging to CSV and WAV audio recording
  * Healthy-baseline capture with deviation alerting

Usage:
    pip install sounddevice numpy matplotlib
    python monitor.py                 # default input device
    python monitor.py --list          # list audio devices
    python monitor.py --device 3      # specific input device
    python monitor.py --rate 48000

Keys (in the plot window):
    b = capture healthy baseline      r = start/stop WAV recording
    c = export feature CSV            q = quit (auto-exports CSV)
"""

import argparse
import csv
import datetime as dt
import queue
import sys
import wave

import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sys.exit("Missing dependency: pip install sounddevice numpy matplotlib")

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

FFT_SIZE = 4096
HOP_SECONDS = 0.1          # feature frame rate ~10 Hz
SPEC_COLS = 300            # spectrogram history columns
TRAIL_LEN = 600            # manifold trail points
DEV_ALERT_PCT = 25.0       # baseline deviation alert threshold


def now_stamp():
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


class Analyzer:
    def __init__(self, rate):
        self.rate = rate
        self.window = np.hanning(FFT_SIZE)
        self.freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / rate)
        self.baseline = None

    def features(self, block):
        """block: float32 mono samples, length >= FFT_SIZE."""
        x = block[-FFT_SIZE:] * self.window
        spec = np.abs(np.fft.rfft(x)) / FFT_SIZE
        mag = spec + 1e-12
        db_spec = 20 * np.log10(mag)

        total = mag[1:].sum()
        centroid = float((self.freqs[1:] * mag[1:]).sum() / total)
        spread = float(np.sqrt(((self.freqs[1:] - centroid) ** 2 * mag[1:]).sum() / total))
        flatness = float(np.exp(np.mean(np.log(mag[1:]))) / np.mean(mag[1:]))
        cumsum = np.cumsum(mag[1:])
        rolloff = float(self.freqs[1 + int(np.searchsorted(cumsum, 0.85 * total))])
        peak_hz = float(self.freqs[int(np.argmax(mag[1:])) + 1])

        rms = float(np.sqrt(np.mean(block ** 2)))
        level_db = 20 * np.log10(rms + 1e-9)
        crest = float(np.max(np.abs(block)) / (rms + 1e-9))

        dev = None
        if self.baseline is not None:
            dev = float(np.mean(np.abs(db_spec - self.baseline)) / 60.0 * 100.0)

        return {
            "level_dbfs": level_db, "dominant_hz": peak_hz,
            "centroid_hz": centroid, "spread_hz": spread,
            "flatness": flatness, "crest": crest,
            "rolloff85_hz": rolloff, "baseline_dev_pct": dev,
        }, db_spec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--device", type=int, default=None, help="input device index")
    ap.add_argument("--rate", type=int, default=48000, help="sample rate (Hz)")
    ap.add_argument("--list", action="store_true", help="list audio devices and exit")
    args = ap.parse_args()

    if args.list:
        print(sd.query_devices())
        return

    rate = args.rate
    hop = int(rate * HOP_SECONDS)
    ana = Analyzer(rate)
    audio_q = queue.Queue()
    ring = np.zeros(FFT_SIZE, dtype=np.float32)

    log_rows = []
    rec_frames = []
    state = {"recording": False, "last_spec": None}

    spec_img = np.full((FFT_SIZE // 8, SPEC_COLS), -100.0)
    trail_t, trail_c, trail_a, trail_s = [], [], [], []
    t0 = dt.datetime.now()

    def audio_cb(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        audio_q.put(indata[:, 0].copy())

    stream = sd.InputStream(device=args.device, channels=1, samplerate=rate,
                            blocksize=hop, callback=audio_cb)

    # ---------- figure ----------
    matplotlib.rcParams.update({"toolbar": "none"})
    plt.style.use("dark_background")
    fig = plt.figure("Factory Acoustic Monitor", figsize=(13, 8))
    fig.patch.set_facecolor("#2c2c2e")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1], hspace=0.35, wspace=0.25)
    ax_man = fig.add_subplot(gs[0, :])
    ax_fft = fig.add_subplot(gs[1, 0])
    ax_gram = fig.add_subplot(gs[1, 1])
    for ax in (ax_man, ax_fft, ax_gram):
        ax.set_facecolor("#242426")

    ax_man.set_title("ACOUSTIC MANIFOLD - time x centroid (size=level, color=spread)", fontsize=9, loc="left")
    ax_man.set_xlabel("time (s)"), ax_man.set_ylabel("spectral centroid (Hz)")
    scat = ax_man.scatter([], [], s=[], c=[], cmap="plasma", vmin=0, vmax=6000, alpha=0.8)
    (trail_line,) = ax_man.plot([], [], lw=0.5, color="w", alpha=0.3)

    show_bins = FFT_SIZE // 8  # up to rate/16 ~ 3-6 kHz... use /4 of nyquist
    fmax = rate / 2 / 4
    ax_fft.set_title("LIVE SPECTRUM (FFT)", fontsize=9, loc="left")
    ax_fft.set_xlim(0, fmax), ax_fft.set_ylim(-100, -20)
    ax_fft.set_xlabel("Hz"), ax_fft.set_ylabel("dB")
    (fft_line,) = ax_fft.plot([], [], lw=0.8, color="#c07dff")
    cent_line = ax_fft.axvline(0, color="#ffd166", ls="--", lw=1)

    ax_gram.set_title("SPECTROGRAM", fontsize=9, loc="left")
    im = ax_gram.imshow(spec_img, aspect="auto", origin="lower", cmap="magma",
                        vmin=-95, vmax=-35, extent=[-SPEC_COLS * HOP_SECONDS, 0, 0, fmax])
    ax_gram.set_xlabel("seconds ago"), ax_gram.set_ylabel("Hz")

    txt = fig.text(0.01, 0.005, "keys: [b]aseline  [r]ecord  [c]sv  [q]uit", fontsize=8, color="#9a9aa0")
    banner = fig.text(0.5, 0.965, "", fontsize=11, color="#ff6b60", ha="center", weight="bold")

    def export_csv():
        if not log_rows:
            return
        name = f"machine-features-{now_stamp()}.csv"
        with open(name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(log_rows[0].keys()))
            w.writeheader(), w.writerows(log_rows)
        print(f"Exported {len(log_rows)} rows -> {name}")

    def save_wav():
        if not rec_frames:
            return
        name = f"machine-recording-{now_stamp()}.wav"
        data = np.concatenate(rec_frames)
        with wave.open(name, "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
            w.writeframes((np.clip(data, -1, 1) * 32767).astype(np.int16).tobytes())
        rec_frames.clear()
        print(f"Saved recording -> {name}")

    def on_key(event):
        if event.key == "b" and state["last_spec"] is not None:
            ana.baseline = state["last_spec"].copy()
            print("Healthy baseline captured.")
        elif event.key == "r":
            state["recording"] = not state["recording"]
            print("Recording ON" if state["recording"] else "Recording OFF")
            if not state["recording"]:
                save_wav()
        elif event.key == "c":
            export_csv()
        elif event.key == "q":
            plt.close(fig)

    fig.canvas.mpl_connect("key_press_event", on_key)

    def update(_):
        nonlocal ring
        got = False
        while not audio_q.empty():
            blk = audio_q.get()
            ring = np.roll(ring, -len(blk)); ring[-len(blk):] = blk
            if state["recording"]:
                rec_frames.append(blk.copy())
            got = True
        if not got:
            return
        f, db_spec = ana.features(ring)
        state["last_spec"] = db_spec
        elapsed = (dt.datetime.now() - t0).total_seconds()
        f_row = {"timestamp": dt.datetime.now().isoformat(), "elapsed_s": round(elapsed, 2),
                 **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in f.items()}}
        log_rows.append(f_row)

        # manifold trail
        trail_t.append(elapsed), trail_c.append(f["centroid_hz"])
        trail_a.append(max(5, (f["level_dbfs"] + 80) * 4)), trail_s.append(f["spread_hz"])
        for lst in (trail_t, trail_c, trail_a, trail_s):
            del lst[:-TRAIL_LEN]
        scat.set_offsets(np.c_[trail_t, trail_c])
        scat.set_sizes(np.asarray(trail_a)), scat.set_array(np.asarray(trail_s))
        trail_line.set_data(trail_t, trail_c)
        ax_man.set_xlim(max(0, elapsed - TRAIL_LEN * HOP_SECONDS), max(10, elapsed))
        lo, hi = min(trail_c), max(trail_c)
        pad = max(200, (hi - lo) * 0.2)
        ax_man.set_ylim(max(0, lo - pad), hi + pad)

        # fft + spectrogram (lower quarter of the band, where machine energy lives)
        nb = len(db_spec) // 4
        fft_line.set_data(ana.freqs[:nb], db_spec[:nb])
        cent_line.set_xdata([f["centroid_hz"]])
        spec_img[:, :-1] = spec_img[:, 1:]
        col = db_spec[:nb]
        idx = np.linspace(0, nb - 1, spec_img.shape[0]).astype(int)
        spec_img[:, -1] = col[idx]
        im.set_data(spec_img)

        dev = f["baseline_dev_pct"]
        rec = " REC" if state["recording"] else ""
        if dev is not None and dev > DEV_ALERT_PCT:
            banner.set_text(f"DEVIATION {dev:.0f}% FROM HEALTHY BASELINE - INSPECT MACHINE{rec}")
        else:
            banner.set_text(("baseline dev %.1f%%" % dev if dev is not None else "no baseline set") + rec)
        txt.set_text(f"level {f['level_dbfs']:6.1f} dBFS | dominant {f['dominant_hz']:7.1f} Hz | "
                     f"centroid {f['centroid_hz']:7.1f} Hz | spread {f['spread_hz']:7.1f} Hz | "
                     f"flatness {f['flatness']:.3f} | crest {f['crest']:.2f}   "
                     "keys: [b]aseline [r]ecord [c]sv [q]uit")

    ani = FuncAnimation(fig, update, interval=int(HOP_SECONDS * 1000), cache_frame_data=False)
    print("Starting audio stream... close window or press q to stop.")
    with stream:
        plt.show()
    if state["recording"]:
        save_wav()
    export_csv()


if __name__ == "__main__":
    main()
