"use client";

import { useEffect, useRef, useState } from "react";

import { CharacterCard } from "@/components/CharacterCard";
import { SceneCard } from "@/components/SceneCard";
import { api } from "@/lib/api";
import type {
  Audio,
  Character,
  ConsistencyScore,
  ExportPreset,
  Job,
  Lyrics,
  Project,
  RenderResult,
  Scene,
} from "@/lib/types";

export default function ProjectPipelinePage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
  const [project, setProject] = useState<Project | null>(null);
  const [lyrics, setLyrics] = useState<Lyrics | null>(null);
  const [audio, setAudio] = useState<Audio | null>(null);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [scores, setScores] = useState<ConsistencyScore[]>([]);
  const [cuts, setCuts] = useState<number[] | null>(null);
  const [segments, setSegments] = useState(8);
  const [presets, setPresets] = useState<ExportPreset[]>([]);
  const [preset, setPreset] = useState("");
  const [render, setRender] = useState<RenderResult | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLInputElement>(null);

  const refreshJobs = () => api.listJobs(id).then(setJobs).catch(() => {});

  useEffect(() => {
    api.getProject(id).then(setProject).catch(() => {});
    api.getLyrics(id).then(setLyrics).catch(() => {});
    api.getAudio(id).then(setAudio).catch(() => {});
    api.listCharacters(id).then(setCharacters).catch(() => {});
    api.listScenes(id).then(setScenes).catch(() => {});
    api.listExportPresets().then(setPresets).catch(() => {});
    refreshJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function guard(tag: string, fn: () => Promise<void>) {
    setBusy(tag);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(String((e as Error)?.message ?? e));
    } finally {
      setBusy(null);
    }
  }

  async function onAudio(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) await guard("audio", async () => setAudio(await api.uploadAudio(id, file)));
  }

  function patchScene(updated: Scene) {
    setScenes((cur) => cur.map((s) => (s.id === updated.id ? updated : s)));
    refreshJobs();
  }

  function patchCharacter(updated: Character) {
    setCharacters((cur) => cur.map((c) => (c.id === updated.id ? updated : c)));
  }

  async function saveSettings(patch: Partial<Project>) {
    await guard("settings", async () =>
      setProject(await api.updateProject(id, patch))
    );
  }

  const sceneLabel = (sceneId: string) =>
    `Scene ${scenes.find((s) => s.id === sceneId)?.number ?? "?"}`;
  const characterName = (characterId: string) =>
    characters.find((c) => c.id === characterId)?.name ?? characterId;

  if (!project) return <p className="muted">Loading project…</p>;

  return (
    <main>
      <h1>{project.title}</h1>
      <p className="muted">
        {project.genre} · {project.mood} · {project.visualStyle} ·{" "}
        {project.targetDuration}s · {project.aspectRatio}
      </p>
      {error && <p className="error">{error}</p>}

      {/* Settings */}
      <section className="section">
        <h2>Settings</h2>
        <div className="grid">
          <div>
            <label>Video model</label>
            <select
              value={project.videoBackend}
              disabled={busy === "settings"}
              onChange={(e) => saveSettings({ videoBackend: e.target.value })}
            >
              <option value="ltx">LTX-Video (fast)</option>
              <option value="wan">Wan 2.2</option>
              <option value="hunyuan">HunyuanVideo</option>
            </select>
          </div>
          <div>
            <label>Transition</label>
            <select
              value={project.transition}
              disabled={busy === "settings"}
              onChange={(e) => saveSettings({ transition: e.target.value })}
            >
              <option value="cut">Hard cut</option>
              <option value="crossfade">Crossfade</option>
            </select>
          </div>
        </div>
      </section>

      {/* Lyrics */}
      <section className="section">
        <div className="row">
          <h2>1 · Lyrics</h2>
          <button
            className="btn secondary"
            disabled={busy === "lyrics"}
            onClick={() =>
              guard("lyrics", async () => setLyrics(await api.generateLyrics(id)))
            }
          >
            {lyrics ? "Regenerate" : "Generate"}
          </button>
        </div>
        {lyrics && (
          <>
            <h3>{lyrics.title}</h3>
            <p className="muted">{lyrics.musicPrompt}</p>
            <pre style={{ whiteSpace: "pre-wrap" }}>{lyrics.body}</pre>
          </>
        )}
      </section>

      {/* Audio */}
      <section className="section">
        <div className="row">
          <h2>2 · Audio</h2>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="btn secondary"
              disabled={busy === "audio"}
              onClick={() => audioRef.current?.click()}
            >
              Upload
            </button>
            <button
              className="btn secondary"
              disabled={busy === "song"}
              title="Generate a song locally from the lyrics' music prompt"
              onClick={() =>
                guard("song", async () => setAudio(await api.generateSong(id)))
              }
            >
              Generate song
            </button>
            <button
              className="btn secondary"
              disabled={!audio || busy === "analyze"}
              onClick={() =>
                guard("analyze", async () =>
                  setAudio(await api.analyzeAudio(id))
                )
              }
            >
              Analyze
            </button>
            <input
              ref={audioRef}
              type="file"
              accept="audio/*"
              hidden
              onChange={onAudio}
            />
          </div>
        </div>
        {audio && (
          <p className="muted">
            {audio.filename}
            {audio.durationSeconds != null &&
              ` · ${audio.durationSeconds.toFixed(1)}s · ${
                audio.bpm?.toFixed(0) ?? "?"
              } bpm`}
          </p>
        )}
      </section>

      {/* Characters */}
      <section className="section">
        <div className="row">
          <h2>3 · Characters</h2>
          <button
            className="btn secondary"
            disabled={busy === "characters"}
            onClick={() =>
              guard("characters", async () =>
                setCharacters(await api.generateCharacters(id))
              )
            }
          >
            {characters.length ? "Regenerate bible" : "Generate bible"}
          </button>
        </div>
        {characters.length === 0 && (
          <p className="muted">No characters yet.</p>
        )}
        {characters.map((c) => (
          <CharacterCard key={c.id} character={c} onChange={patchCharacter} />
        ))}
      </section>

      {/* Storyboard */}
      <section className="section">
        <div className="row">
          <h2>4 · Storyboard</h2>
          <button
            className="btn secondary"
            disabled={busy === "storyboard"}
            onClick={() =>
              guard("storyboard", async () =>
                setScenes(await api.generateStoryboard(id))
              )
            }
          >
            {scenes.length ? "Regenerate" : "Generate"}
          </button>
        </div>
        {scenes.map((s) => (
          <SceneCard key={s.id} scene={s} onChange={patchScene} />
        ))}
      </section>

      {/* Jobs */}
      <section className="section">
        <div className="row">
          <h2>5 · Jobs</h2>
          <button className="btn secondary" onClick={refreshJobs}>
            Refresh
          </button>
        </div>
        {jobs.length === 0 && <p className="muted">No generation jobs yet.</p>}
        {jobs.map((job) => (
          <div key={job.id} className="meta">
            <span className="badge">{job.type}</span>
            <span>{job.status}</span>
            {job.status === "queued" && job.queuePosition != null && (
              <span className="muted">queue #{job.queuePosition}</span>
            )}
            {job.status === "running" && (
              <span className="muted">{Math.round(job.progress * 100)}%</span>
            )}
            {job.error && <span className="error">{job.error}</span>}
          </div>
        ))}
      </section>

      {/* Quality (Phase 4) */}
      <section className="section">
        <div className="row">
          <h2>6 · Quality</h2>
        </div>

        <div className="row" style={{ marginTop: 8 }}>
          <strong>Character consistency</strong>
          <button
            className="btn secondary"
            disabled={busy === "consistency"}
            onClick={() =>
              guard("consistency", async () =>
                setScores(await api.listConsistency(id))
              )
            }
          >
            Score keyframes
          </button>
        </div>
        {scores.length === 0 ? (
          <p className="muted">
            Generate keyframes and approve a character reference, then score.
          </p>
        ) : (
          scores.map((s, i) => (
            <div key={i} className="meta">
              <span className="badge">{sceneLabel(s.sceneId)}</span>
              <span>{characterName(s.characterId)}</span>
              <span className={s.score >= 0.6 ? "muted" : "error"}>
                {s.score.toFixed(2)}
              </span>
            </div>
          ))
        )}

        <div className="row" style={{ marginTop: 16 }}>
          <strong>Beat-synced cut suggestions</strong>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="number"
              min={2}
              value={segments}
              onChange={(e) => setSegments(Number(e.target.value))}
              style={{ width: 80 }}
            />
            <button
              className="btn secondary"
              disabled={busy === "cuts"}
              onClick={() =>
                guard("cuts", async () =>
                  setCuts((await api.getBeatCuts(id, segments)).cuts)
                )
              }
            >
              Suggest cuts
            </button>
          </div>
        </div>
        {cuts && (
          <p className="muted">
            {cuts.length
              ? cuts.map((c) => `${c.toFixed(1)}s`).join(" · ")
              : "No beats available — analyze the audio first."}
          </p>
        )}
      </section>

      {/* Render */}
      <section className="section">
        <div className="row">
          <h2>7 · Final Render</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <select value={preset} onChange={(e) => setPreset(e.target.value)}>
              <option value="">Aspect-ratio default</option>
              {presets.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.width}×{p.height})
                </option>
              ))}
            </select>
            <button
              className="btn"
              disabled={busy === "render" || scenes.length === 0}
              onClick={() =>
                guard("render", async () =>
                  setRender(await api.renderFinal(id, preset || undefined))
                )
              }
            >
              Render MP4
            </button>
          </div>
        </div>
        {render && (
          <p className="muted">
            {render.status} → {render.outputPath}
          </p>
        )}
      </section>
    </main>
  );
}
