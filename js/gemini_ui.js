/*
 * ComfyUI-Gemini_3x_Pro v2.0.5
 * Native Audio Recorder control.
 *
 * The Start Record button is a real LiteGraph/ComfyUI widget, so it lives
 * in the node's coordinate system and follows node resize/move operations.
 */
import { app } from "/scripts/app.js";

const RECORDER_CLASS = "Gemini Audio Recorder";
const BUTTON_NAME = "gemini_start_record";
const TRIGGER_NAME = "trigger";

function isRecorder(node) {
  return node?.comfyClass === RECORDER_CLASS;
}

function findWidget(node, name) {
  return (node.widgets || []).find((w) => w?.name === name);
}

function setButtonState(button, busy) {
  if (!button) return;
  button.value = busy ? "● Recording / Queuing…" : "🔴 Start Record";
  button.label = button.value;
  button.disabled = !!busy;
  button._geminiBusy = !!busy;
  nodeDirty(button.__geminiNode);
}

function nodeDirty(node) {
  if (!node) return;
  try {
    app.graph?.setDirtyCanvas?.(true, true);
  } catch (_) {
    // Older frontends may not expose setDirtyCanvas.
  }
}

function ensureRecorderButton(node) {
  if (!isRecorder(node)) return;
  if (findWidget(node, BUTTON_NAME)) return;

  const button = node.addWidget(
    "button",
    BUTTON_NAME,
    "🔴 Start Record",
    async () => {
      if (button._geminiBusy) return;

      const trigger = findWidget(node, TRIGGER_NAME);
      if (!trigger) {
        console.error("[Gemini Audio Recorder] trigger widget not found");
        return;
      }

      button.__geminiNode = node;
      button._geminiBusy = true;
      button.value = "● Recording / Queuing…";
      button.label = button.value;
      button.disabled = true;
      nodeDirty(node);

      // Change a real serialized execution input so a new recording run is
      // not served from the recorder's cached audio.
      const current = Number(trigger.value) || 0;
      trigger.value = current + 1;
      trigger.callback?.(trigger.value);

      try {
        // queuePrompt(0) is the supported app-level queue entry point. The
        // recorder is OUTPUT_NODE=True on the backend, preventing the
        // prompt_no_outputs validation error even when it has no downstream
        // Save/Preview node.
        if (typeof app.queuePrompt === "function") {
          await app.queuePrompt(0, 1, {
            intent: { trigger_source: "gemini_audio_recorder" },
          });
        } else if (app.api && typeof app.api.queuePrompt === "function") {
          const prompt = await app.graphToPrompt();
          await app.api.queuePrompt(0, prompt);
        } else {
          throw new Error("ComfyUI queue API is unavailable");
        }
      } catch (error) {
        console.error("[Gemini Audio Recorder] Queue failed:", error);
        button._geminiBusy = false;
        button.disabled = false;
        button.value = "🔴 Start Record";
        button.label = button.value;
        nodeDirty(node);
      }
    }
  );

  // IMPORTANT: both flags are intentional. `serialize` controls workflow
  // persistence; `options.serialize` controls API prompt inclusion.
  button.serialize = false;
  button.options ||= {};
  button.options.serialize = false;
  button.__geminiNode = node;
  button._geminiBusy = false;

  // UI-only widget must remain the LAST widget to avoid widget index drift.
  try {
    const idx = node.widgets.indexOf(button);
    if (idx !== node.widgets.length - 1) {
      node.widgets.splice(idx, 1);
      node.widgets.push(button);
    }
  } catch (_) {
    // Non-fatal on older LiteGraph builds.
  }

  node.properties ||= {};
  node.properties.gemini_v2_0_5 = true;
  node.setDirtyCanvas?.(true, true);
}

function attachExecutionReset() {
  const api = app.api;
  if (!api || api.__geminiRecorderHookInstalled) return;
  api.__geminiRecorderHookInstalled = true;

  const reset = () => {
    for (const node of app.graph?.nodes || []) {
      if (!isRecorder(node)) continue;
      const button = findWidget(node, BUTTON_NAME);
      if (!button) continue;
      button._geminiBusy = false;
      button.disabled = false;
      button.value = "🔴 Start Record";
      button.label = button.value;
    }
    nodeDirty(null);
  };

  // Events are emitted by the ComfyUI frontend API across current versions.
  for (const eventName of [
    "execution_success",
    "execution_error",
    "execution_interrupted",
  ]) {
    api.addEventListener?.(eventName, reset);
  }
}

app.registerExtension({
  name: "asirus.ComfyUI-Gemini_3x_Pro.v2.0.5",

  async nodeCreated(node) {
    if (!node) return;
    ensureRecorderButton(node);
    attachExecutionReset();
  },

  async setup() {
    attachExecutionReset();
    // Existing workflow nodes may already exist when the extension is loaded.
    for (const node of app.graph?.nodes || []) {
      ensureRecorderButton(node);
    }
  },
});
