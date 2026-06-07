import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProjectCard } from "./ProjectCard";
import type { Project } from "@/lib/types";

const project: Project = {
  id: "p1",
  title: "Wings We Leave Behind",
  idea: "childhood friends",
  genre: "pop rock",
  mood: "bittersweet",
  visualStyle: "2D",
  targetDuration: 60,
  aspectRatio: "16:9",
  status: "draft",
  videoBackend: "ltx",
  transition: "cut",
  transitionDuration: 0.5,
  createdAt: "2026-06-06T00:00:00Z",
  updatedAt: "2026-06-06T00:00:00Z",
};

describe("ProjectCard", () => {
  it("shows the title, status and duration", () => {
    render(<ProjectCard project={project} />);
    expect(screen.getByText("Wings We Leave Behind")).toBeInTheDocument();
    expect(screen.getByText(/draft/i)).toBeInTheDocument();
    expect(screen.getByText(/60s/)).toBeInTheDocument();
  });

  it("links to the project pipeline page", () => {
    render(<ProjectCard project={project} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/projects/p1");
  });
});
