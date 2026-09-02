---
title: Factory Sound Event Classifier
emoji: 🔊
colorFrom: blue
colorTo: gray
sdk: static
app_file: index.html
pinned: false
license: mit
short_description: Live microphone sound-event classification with alerts
---

# Factory Sound Event Classifier — Live Microphone Audio Classification

A **static, browser-only** app that classifies live microphone audio with a real neural
network (an Audio Spectrogram Transformer fine-tuned on AudioSet, running in-browser via
[transformers.js](https://github.com/xenova/transformers.js) / ONNX Runtime Web), showing
per-class confidence, an alert banner, and a timestamped event log. Built as the Track B
(Audio) submission for the `myTask.md` AI Solution Engineering assignment — it deliberately
uses a **different approach (ML classification) than the DSP-only reference project** one
level up in this repo, while staying a **static** Space (no server, no payment/verification
gate) like that reference project.

## 🚀 Try it live

**Live Space:** [Factory Sound Event Classifier](https://yeanhui-highintensitymachine.static.hf.space/index.html)
(also viewable, embedded, at <https://huggingface.co/spaces/yeanhui/HighIntensityMachine>)

Click **Start microphone** and allow browser access, or use the **Upload / Demo** tab (with a
bundled synthetic motor-hum clip) if you have no microphone or the browser blocks access.

## How to run locally

The app is a single self-contained `index.html` — no build step, no install:

```bash
cd new-solution
python -m http.server 8000
# open http://localhost:8000 in Chrome or Edge
```

(Or just double-click `index.html` — microphone access needs `https://`, `file://`, or
`localhost`, all of which work.) The ~100MB model downloads from the Hugging Face Hub via
CDN on first load and is cached by the browser afterward.

## What it does

| Element | What it shows |
|---|---|
| Live microphone tab | Streaming mic audio classified ~once per second, entirely client-side |
| Top sound classes | Confidence bars (0–100%) per class, not just a single tag |
| Alert banner | Turns red when a predicted label matches an "alert keyword" (Alarm, Siren, Explosion, …) above a confidence threshold |
| Event log | Timestamped table of the top detection each cycle, newest first |
| Export CSV | Downloads the full session log |
| Settings | Alert confidence threshold slider + alert-keyword list |
| Upload / Demo tab | Analyze an uploaded clip or the bundled demo sound — works with zero microphone access |

## Data / model used

- **Model**: [`Xenova/ast-finetuned-audioset-10-10-0.4593`](https://huggingface.co/Xenova/ast-finetuned-audioset-10-10-0.4593)
  (Audio Spectrogram Transformer, ONNX-converted for browser inference)
- **Training data**: Google **AudioSet** — 527 general-purpose sound-event classes
  (engines, alarms, sirens, tools, mechanical fans, speech, etc.)
- **Inference**: runs entirely in the visitor's browser (WebAssembly via ONNX Runtime Web);
  no server, no GPU, no data leaves the device

See the **"How it works"** tab inside the app for the full pipeline explanation and limitations.

## Deployment — Hugging Face Space (auto-deploy)

Every push to `main` that touches `new-solution/**` triggers
[`.github/workflows/deploy-new-solution.yml`](../.github/workflows/deploy-new-solution.yml), which:

1. **Verifies** — required files exist, the Space config in this README's front matter is
   valid, and `index.html` contains the expected app structure (a Python-run check, per
   assignment rules, even though the app itself needs no Python dependencies).
2. **Deploys** — copies just this `new-solution/` folder into a clean git history and
   force-pushes it to the Hugging Face Space root, using an `HF_TOKEN` repository secret.

One-time setup: create a **write** token at <https://huggingface.co/settings/tokens> and save
it as a GitHub Actions secret named `HF_TOKEN`.

> Per the assignment rules, this is meant to end up in its **own clean GitHub repository**
> before final submission — this `new-solution/` folder is self-contained (just
> `index.html` + `README.md`) so it can be copied out directly.

## Limitations

- AudioSet's classes are general-purpose, not manufacturing-specific.
- Model load + first inference can take tens of seconds on slower devices/connections.
- Browser microphones are consumer-grade and band-limited (~20 kHz).
