"use client";

import { useRef, useState } from "react";

import { api } from "@/lib/api";
import type { Scene } from "@/lib/types";

export function SceneCard({
  scene,
  onChange,
}: {
  scene: Scene;
  onChange: (updated: Scene) => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const clipRef = useRef<HTMLInputElement>(null);
  const keyframeRef = useRef<HTMLInputElement>(null);

  async function run(tag: string, fn: () => Promise<Scene>) {
    setBusy(tag);
    try {
      onChange(await fn());
    } finally {
      setBusy(null);
    }
  }

  async function generateClip() {
    setBusy("clip");
    try {
      await api.generateClip(scene.id);
      onChange(await api.getScene(scene.id));
    } finally {
      setBusy(null);
    }
  }

  async function onClipUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) await run("clip", () => api.uploadClip(scene.id, file));
  }

  async function onKeyframeUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) await run("kf", () => api.uploadKeyframe(scene.id, file));
  }

  return (
    <div className="scene">
      <div className="row">
        <strong>
          Scene {scene.number} · {scene.sectionName}
        </strong>
        <span className="muted">
          {scene.startTime}s – {scene.endTime}s
        </span>
      </div>
      <p className="muted">{scene.visualDescription}</p>
      <div className="meta">
        <span className="badge">keyframe: {scene.keyframeStatus}</span>
        <span className="badge">clip: {scene.clipStatus}</span>
      </div>

      {/* Keyframe (Phase 2) */}
      <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        <button
          className="btn secondary"
          disabled={busy !== null}
          onClick={() => run("kf", () => api.generateKeyframe(scene.id))}
        >
          {scene.keyframeStatus === "pending" ? "Generate keyframe" : "Regenerate keyframe"}
        </button>
        <button
          className="btn secondary"
          disabled={busy !== null || scene.keyframeStatus !== "generated"}
          onClick={() => run("kf", () => api.approveKeyframe(scene.id))}
        >
          Approve keyframe
        </button>
        <button
          className="btn secondary"
          disabled={busy !== null}
          onClick={() => keyframeRef.current?.click()}
        >
          Upload keyframe
        </button>
      </div>

      {/* Clip (Phase 3) */}
      <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
        <button
          className="btn secondary"
          disabled={busy !== null || scene.keyframeStatus !== "approved"}
          title={
            scene.keyframeStatus !== "approved"
              ? "Approve a keyframe first"
              : undefined
          }
          onClick={generateClip}
        >
          Generate clip
        </button>
        <button
          className="btn secondary"
          disabled={busy !== null || scene.clipStatus === "pending"}
          onClick={() => run("clip", () => api.approveClip(scene.id))}
        >
          Approve clip
        </button>
        <button
          className="btn secondary"
          disabled={busy !== null}
          onClick={() => clipRef.current?.click()}
        >
          Upload clip
        </button>
        <button
          className="btn secondary"
          disabled={busy !== null || scene.clipStatus === "pending"}
          onClick={() => run("clip", () => api.finalizeScene(scene.id))}
        >
          Mark final
        </button>
      </div>

      <input ref={keyframeRef} type="file" accept="image/*" hidden onChange={onKeyframeUpload} />
      <input ref={clipRef} type="file" accept="video/*" hidden onChange={onClipUpload} />
    </div>
  );
}
