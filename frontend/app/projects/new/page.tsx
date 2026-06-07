"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { ProjectCreate, ProjectTemplate } from "@/lib/types";

const EMPTY: ProjectCreate = {
  title: "",
  idea: "",
  genre: "",
  mood: "",
  visualStyle: "",
  targetDuration: 60,
  aspectRatio: "16:9",
};

export default function NewProjectPage() {
  const router = useRouter();
  const [form, setForm] = useState<ProjectCreate>(EMPTY);
  const [templates, setTemplates] = useState<ProjectTemplate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.listTemplates().then(setTemplates).catch(() => {});
  }, []);

  function set<K extends keyof ProjectCreate>(key: K, value: ProjectCreate[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function applyTemplate(id: string) {
    const t = templates.find((t) => t.id === id);
    if (!t) return;
    setForm((f) => ({
      ...f,
      genre: t.genre,
      mood: t.mood,
      visualStyle: t.visualStyle,
      aspectRatio: t.aspectRatio,
      targetDuration: t.targetDuration,
    }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const project = await api.createProject(form);
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(String((err as Error)?.message ?? err));
      setSaving(false);
    }
  }

  return (
    <main>
      <h1>New Project</h1>
      <form onSubmit={submit} className="section">
        {templates.length > 0 && (
          <>
            <label>Start from a template (optional)</label>
            <select
              defaultValue=""
              onChange={(e) => applyTemplate(e.target.value)}
            >
              <option value="">— none —</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </>
        )}
        <label>Title</label>
        <input
          value={form.title}
          onChange={(e) => set("title", e.target.value)}
          required
        />
        <label>Song idea</label>
        <textarea
          value={form.idea}
          onChange={(e) => set("idea", e.target.value)}
          rows={3}
          required
        />
        <div className="grid">
          <div>
            <label>Genre</label>
            <input
              value={form.genre}
              onChange={(e) => set("genre", e.target.value)}
            />
          </div>
          <div>
            <label>Mood</label>
            <input
              value={form.mood}
              onChange={(e) => set("mood", e.target.value)}
            />
          </div>
          <div>
            <label>Visual style</label>
            <input
              value={form.visualStyle}
              onChange={(e) => set("visualStyle", e.target.value)}
            />
          </div>
          <div>
            <label>Target duration (s)</label>
            <input
              type="number"
              value={form.targetDuration}
              onChange={(e) => set("targetDuration", Number(e.target.value))}
            />
          </div>
          <div>
            <label>Aspect ratio</label>
            <select
              value={form.aspectRatio}
              onChange={(e) => set("aspectRatio", e.target.value)}
            >
              <option value="16:9">16:9</option>
              <option value="9:16">9:16</option>
              <option value="1:1">1:1</option>
              <option value="4:3">4:3</option>
            </select>
          </div>
        </div>
        {error && <p className="error">{error}</p>}
        <div style={{ marginTop: 16 }}>
          <button className="btn" type="submit" disabled={saving}>
            {saving ? "Creating…" : "Create Project"}
          </button>
        </div>
      </form>
    </main>
  );
}
