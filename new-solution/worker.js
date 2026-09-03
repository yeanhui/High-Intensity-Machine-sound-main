// Runs the audio classifier off the main UI thread so button clicks / tab
// switches stay responsive while classification is in progress.
import { pipeline, env } from "https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2";

env.allowLocalModels = false;

const MODEL_ID = "Xenova/ast-finetuned-audioset-10-10-0.4593";
let classifierPromise = null;

function getClassifier() {
  if (!classifierPromise) classifierPromise = pipeline("audio-classification", MODEL_ID);
  return classifierPromise;
}

self.onmessage = async (e) => {
  const { type, id, audio } = e.data;

  if (type === "load") {
    try {
      await getClassifier();
      self.postMessage({ type: "ready" });
    } catch (err) {
      self.postMessage({ type: "error", error: String(err && err.message ? err.message : err) });
    }
    return;
  }

  if (type === "classify") {
    try {
      const classifier = await getClassifier();
      const results = await classifier(audio, { topk: 5 });
      self.postMessage({ type: "result", id, results });
    } catch (err) {
      self.postMessage({ type: "error", id, error: String(err && err.message ? err.message : err) });
    }
  }
};
