"use client";

import { useEffect, useState } from "react";

import { ProjectCard } from "@/components/ProjectCard";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch((e) => setError(String(e?.message ?? e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main>
      <h1>Projects</h1>
      {loading && <p className="muted">Loading…</p>}
      {error && <p className="error">Could not load projects: {error}</p>}
      {!loading && !error && projects.length === 0 && (
        <p className="muted">No projects yet. Create one to get started.</p>
      )}
      <div className="grid">
        {projects.map((p) => (
          <ProjectCard key={p.id} project={p} />
        ))}
      </div>
    </main>
  );
}
