"use client";

import { useRef, useState } from "react";

import { api } from "@/lib/api";
import type { Character } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function CharacterCard({
  character,
  onChange,
}: {
  character: Character;
  onChange: (updated: Character) => void;
}) {
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function run(fn: () => Promise<Character>) {
    setBusy(true);
    try {
      onChange(await fn());
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) await run(() => api.uploadCharacterReference(character.id, file));
  }

  return (
    <div className="scene">
      <div className="row">
        <strong>
          {character.name}
          {character.age ? `, ${character.age}` : ""}
        </strong>
        <span className="badge">ref: {character.refStatus}</span>
      </div>
      <p className="muted">
        {[character.face, character.hair, character.clothing]
          .filter(Boolean)
          .join(" · ")}
      </p>
      <p className="muted">Anchors: {character.identityAnchors.join(", ")}</p>
      {character.refImagePath && (
        <p className="muted">{character.refImagePath.split("/").pop()}</p>
      )}
      <label>LoRA path (optional)</label>
      <input
        defaultValue={character.loraPath ?? ""}
        placeholder="/loras/character.safetensors"
        disabled={busy}
        onBlur={(e) => {
          const value = e.target.value.trim();
          if (value !== (character.loraPath ?? "")) {
            run(() => api.updateCharacter(character.id, { loraPath: value || null }));
          }
        }}
      />
      <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        <button
          className="btn secondary"
          disabled={busy}
          onClick={() => run(() => api.generateCharacterReference(character.id))}
        >
          {character.refStatus === "pending" ? "Generate reference" : "Regenerate reference"}
        </button>
        <button
          className="btn secondary"
          disabled={busy || character.refStatus === "approved"}
          onClick={() => run(() => api.approveCharacterReference(character.id))}
        >
          Approve
        </button>
        <button
          className="btn secondary"
          disabled={busy}
          onClick={() => fileRef.current?.click()}
        >
          Upload
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          hidden
          onChange={onUpload}
        />
      </div>
    </div>
  );
}

export { API_BASE };
