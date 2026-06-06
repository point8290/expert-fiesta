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
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function run(fn: () => Promise<Scene>) {
    setBusy(true);
    try {
      onChange(await fn());
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) await run(() => api.uploadClip(scene.id, file));
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
        <span className="badge">clip: {scene.clipStatus}</span>
        {scene.clipPath && <span>{scene.clipPath.split("/").pop()}</span>}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        <button
          className="btn secondary"
          disabled={busy}
          onClick={() => run(() => api.regenerateScenePrompt(scene.id))}
        >
          Regenerate prompt
        </button>
        <button
          className="btn secondary"
          disabled={busy}
          onClick={() => fileRef.current?.click()}
        >
          Upload clip
        </button>
        <button
          className="btn secondary"
          disabled={busy || scene.clipStatus === "pending"}
          onClick={() => run(() => api.finalizeScene(scene.id))}
        >
          Mark final
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="video/*"
          hidden
          onChange={onUpload}
        />
      </div>
    </div>
  );
}
