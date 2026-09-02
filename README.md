---
title: High Intensity Machine Sound
emoji: 🏭
colorFrom: gray
colorTo: yellow
sdk: static
app_file: app.html
pinned: false
license: mit
short_description: Factory machine sound frequency monitor and recorder
---

# Factory Acoustic Monitor — Machine Sound Frequency Recorder

A browser-based prototype for **recording and visualizing machine sound frequencies** in an
electronics-manufacturing environment, inspired by spectral "acoustic manifold" visualizations
of bird song, adapted for industrial condition monitoring.

## 🚀 Try it live

**Test the app here (no install needed):**

### 👉 https://yianxingjian-highintensitymachine.static.hf.space/ 👈

Hosted on Hugging Face Spaces — Space page:
<https://huggingface.co/spaces/YianXingJian/HighIntensityMachine>

Click **Demo machine sound** to try it instantly with a synthesized motor, or
**Start microphone** to analyze real sound around you. Every chart has a **?**
button explaining what it shows and what its movement means for machine condition.

> Use the direct `.hf.space` link above for microphone access — the Space page embeds
> the app in an iframe, which some browsers restrict for mic use.

## Quick start (browser version)

The web app lives in [`app.html`](app.html) — you can also download that file and open it
locally in Chrome or Edge (no server or install needed).

> Microphone note: browsers only allow mic access on `https://` pages or on `file://` /
> `http://localhost` in Chrome/Edge. If mic access is blocked in your setup, use the
> **Python desktop version** below — it has no such restriction.

1. Click **Start microphone** near the machine (grant mic permission), or **Demo machine sound** to preview with a synthesized motor sound.
2. Click **Set healthy baseline** while the machine runs normally — future deviations are flagged with an on-screen alert.
3. **Record** saves the raw audio to a file; **Export CSV** downloads the per-frame acoustic feature log for analysis or ML training.

All processing runs locally in the browser (Web Audio API). No data leaves the device.

## Quick start (Python desktop version)

Runs directly on your machine with full microphone access — better suited for real
factory-floor capture than the browser.

```bash
pip install -r requirements.txt
python monitor.py             # start with default microphone
python monitor.py --list      # list audio input devices
python monitor.py --device 3  # use a specific device
```

On Linux, also install the PortAudio system library first:
`sudo apt-get install libportaudio2` (Windows and macOS need nothing extra —
the pip package bundles it).

In the plot window: press **b** to capture the healthy baseline, **r** to start/stop a WAV
recording, **c** to export the feature CSV, **q** to quit (CSV auto-exports on exit).

## What the prototype shows

| Panel | What it is |
|---|---|
| Acoustic manifold | Rotating 3D trajectory of the sound: time × spectral centroid × amplitude, bubble color = spectral spread (like the bird-song reference) |
| Live spectrum | Real-time FFT with spectral-centroid marker |
| Spectrogram | Frequency content over time (waterfall) |
| Multi-scale radar | The machine's acoustic "signature" across 6 features — its shape changes when machine condition changes |
| Metrics + log | Numeric features, baseline deviation %, event log |

## Information captured (per ~100 ms frame, exported to CSV)

- **Level (dBFS)** — overall loudness / energy
- **Dominant frequency (Hz)** — strongest tone, e.g. motor rotation harmonics
- **Spectral centroid (Hz)** — "brightness"; shifts when bearings wear or friction increases
- **Spectral spread (Hz)** — how wide the energy is distributed; grows with rattle/looseness
- **Spectral flatness** — tonal (healthy rotating machine) vs. noisy (grinding, air leaks)
- **Crest factor** — impulsiveness; spikes indicate impacts, knocking, bearing defects
- **Rolloff 85% (Hz)** — high-frequency energy content
- **Baseline deviation %** — distance from the saved "healthy" spectrum (simple anomaly score)
- Raw **audio recording** (WAV/WebM) with timestamps

## Technologies for a real production deployment

**Edge (on the factory floor)**
- Industrial MEMS or ICP measurement microphones (flat response, up to ultrasonic 40–100 kHz for early bearing/discharge detection), plus optional accelerometers for vibration correlation
- Edge gateway per line: Raspberry Pi / NVIDIA Jetson / industrial PC running Python (`librosa`, `scipy`, `numpy`) or C++ DSP for feature extraction on-device, so only compact features stream upstream

**Transport & backend**
- MQTT or OPC-UA to integrate with existing PLC/SCADA/MES systems
- Time-series database: InfluxDB or TimescaleDB for features; object storage (S3/MinIO) for raw audio clips around alert events
- Stream processing: Kafka + Flink (or lightweight Node/Python services) for real-time rule and threshold evaluation

**Machine learning**
- Anomaly detection: autoencoders or Gaussian-mixture models trained on the "healthy" feature distribution (unsupervised — no failure examples needed to start)
- Fault classification (once labeled data accumulates): CNNs on mel-spectrograms (the industry-standard approach, e.g. as used with the MIMII industrial-sound dataset)
- Frameworks: PyTorch / TensorFlow, ONNX for edge inference

**Dashboard & alerting**
- Grafana or a custom web app (React + WebGL/Three.js for the 3D manifold view)
- Alerts to Andon boards, email, SMS, or CMMS work-order creation (e.g. SAP PM integration)

## Business benefits for an electronics manufacturer

1. **Predictive maintenance** — detect bearing wear, motor imbalance, loose fixtures, and failing fans days or weeks before breakdown, converting unplanned downtime into scheduled maintenance. Unplanned line stops in SMT/assembly are typically the single largest avoidable cost this addresses.
2. **Quality assurance** — abnormal sounds from placement machines, presses, screwdriving, or conveyors often correlate with defective output; catching acoustic drift catches quality drift early.
3. **Non-invasive retrofit** — microphones need no machine modification, no PLC changes, and work on legacy equipment where adding vibration sensors is impractical.
4. **Process verification** — confirm operations completed correctly (e.g. a press cycle's acoustic signature) as an automated in-line check.
5. **Workplace safety & compliance** — continuous dB(A) logging documents noise-exposure compliance (hearing-conservation regulations) as a free by-product.
6. **Institutional knowledge capture** — experienced technicians "hear" problems; this system digitizes that skill so it scales across shifts and sites, and builds a labeled dataset that grows more valuable over time.
7. **Energy & OEE insight** — acoustic load signatures reveal idle-but-running equipment and feed OEE availability metrics.

## Deployment — Hugging Face Space (auto-deploy)

The live demo runs at <https://huggingface.co/spaces/YianXingJian/HighIntensityMachine>
as a **static** Space (configured by the YAML front matter at the top of this README).

Every push to `main` triggers `.github/workflows/deploy-huggingface.yml`, which:

1. **Verifies the environment** — required files exist, the Space config is valid,
   all Python libraries in `requirements.txt` install and import cleanly, and
   `monitor.py` / `index.html` pass sanity checks.
2. **Deploys** — force-pushes the repository to the Space, which rebuilds automatically.

One-time setup: create a **write** token at <https://huggingface.co/settings/tokens>
and save it as a GitHub Actions secret named `HF_TOKEN`
(GitHub repo → Settings → Secrets and variables → Actions).

> Microphone on Hugging Face: the Space page embeds the app in an iframe, which some
> browsers restrict for mic access. If the mic button does not work there, open the
> app directly at <https://yianxingjian-highintensitymachine.static.hf.space> —
> served over HTTPS without the iframe, where microphone access works normally.

## Limitations of this prototype (what production adds)

- Browser mics are consumer-grade and capped near 20 kHz; production uses calibrated industrial microphones and higher sample rates.
- Baseline deviation here is a simple spectral distance; production uses trained anomaly models robust to background noise and multiple machines.
- No persistence/backend in the prototype — data lives in the page until exported.
