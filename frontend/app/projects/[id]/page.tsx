"use client";

import { useEffect, useRef, useState } from "react";

import { CharacterCard } from "@/components/CharacterCard";
import { SceneCard } from "@/components/SceneCard";
import { api } from "@/lib/api";
import type {
  Audio,
  Character,
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

  if (!project) return <p className="muted">Loading project…</p>;

  return (
    <main>
      <h1>{project.title}</h1>
      <p className="muted">
        {project.genre} · {project.mood} · {project.visualStyle} ·{" "}
        {project.targetDuration}s · {project.aspectRatio}
      </p>
      {error && <p className="error">{error}</p>}

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

      {/* Render */}
      <section className="section">
        <div className="row">
          <h2>6 · Final Render</h2>
          <button
            className="btn"
            disabled={busy === "render" || scenes.length === 0}
            onClick={() =>
              guard("render", async () => setRender(await api.renderFinal(id)))
            }
          >
            Render MP4
          </button>
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
