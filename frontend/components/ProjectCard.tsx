import Link from "next/link";

import type { Project } from "@/lib/types";

export function ProjectCard({ project }: { project: Project }) {
  return (
    <Link href={`/projects/${project.id}`} className="card">
      <h3>{project.title}</h3>
      <p className="muted">{project.idea}</p>
      <div className="meta">
        <span className="badge">{project.status}</span>
        <span>{project.targetDuration}s</span>
        <span>{project.aspectRatio}</span>
      </div>
    </Link>
  );
}
