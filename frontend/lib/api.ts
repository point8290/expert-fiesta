// Typed client for the Local Music Video Studio backend.
import { getToken } from "./auth";
import type {
  Audio,
  AuthToken,
  BeatCuts,
  Character,
  ConsistencyScore,
  Job,
  Lyrics,
  Project,
  ProjectCreate,
  RenderResult,
  Scene,
  User,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function jsonInit(method: string, body?: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

export const api = {
  // Auth
  register: (email: string, password: string) =>
    request<AuthToken>("/auth/register", jsonInit("POST", { email, password })),
  login: (email: string, password: string) =>
    request<AuthToken>("/auth/login", jsonInit("POST", { email, password })),
  me: () => request<User>("/auth/me"),

  // Projects
  listProjects: () => request<Project[]>("/projects"),
  createProject: (data: ProjectCreate) =>
    request<Project>("/projects", jsonInit("POST", data)),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  updateProject: (id: string, data: Partial<ProjectCreate>) =>
    request<Project>(`/projects/${id}`, jsonInit("PATCH", data)),
  deleteProject: (id: string) =>
    request<void>(`/projects/${id}`, { method: "DELETE" }),

  // Lyrics
  generateLyrics: (id: string) =>
    request<Lyrics>(`/projects/${id}/lyrics`, jsonInit("POST")),
  getLyrics: (id: string) => request<Lyrics>(`/projects/${id}/lyrics`),

  // Audio
  uploadAudio: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Audio>(`/projects/${id}/audio`, {
      method: "POST",
      body: form,
    });
  },
  getAudio: (id: string) => request<Audio>(`/projects/${id}/audio`),
  analyzeAudio: (id: string) =>
    request<Audio>(`/projects/${id}/audio/analyze`, { method: "POST" }),

  // Storyboard & scenes
  generateStoryboard: (id: string) =>
    request<Scene[]>(`/projects/${id}/storyboard`, { method: "POST" }),
  listScenes: (id: string) => request<Scene[]>(`/projects/${id}/scenes`),
  getScene: (sceneId: string) => request<Scene>(`/scenes/${sceneId}`),
  updateScene: (sceneId: string, data: Partial<Scene>) =>
    request<Scene>(`/scenes/${sceneId}`, jsonInit("PATCH", data)),
  regenerateScenePrompt: (sceneId: string) =>
    request<Scene>(`/scenes/${sceneId}/regenerate-prompt`, { method: "POST" }),
  uploadClip: (sceneId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Scene>(`/scenes/${sceneId}/clip`, {
      method: "POST",
      body: form,
    });
  },
  finalizeScene: (sceneId: string) =>
    request<Scene>(`/scenes/${sceneId}/finalize`, { method: "POST" }),

  // Characters
  generateCharacters: (id: string) =>
    request<Character[]>(`/projects/${id}/characters`, { method: "POST" }),
  listCharacters: (id: string) =>
    request<Character[]>(`/projects/${id}/characters`),
  updateCharacter: (characterId: string, data: Partial<Character>) =>
    request<Character>(`/characters/${characterId}`, jsonInit("PATCH", data)),
  generateCharacterReference: (characterId: string) =>
    request<Character>(`/characters/${characterId}/reference`, {
      method: "POST",
    }),
  approveCharacterReference: (characterId: string) =>
    request<Character>(`/characters/${characterId}/reference/approve`, {
      method: "POST",
    }),
  uploadCharacterReference: (characterId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Character>(`/characters/${characterId}/reference/upload`, {
      method: "POST",
      body: form,
    });
  },

  // Keyframes
  generateKeyframe: (sceneId: string) =>
    request<Scene>(`/scenes/${sceneId}/keyframe`, { method: "POST" }),
  approveKeyframe: (sceneId: string) =>
    request<Scene>(`/scenes/${sceneId}/keyframe/approve`, { method: "POST" }),
  uploadKeyframe: (sceneId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Scene>(`/scenes/${sceneId}/keyframe/upload`, {
      method: "POST",
      body: form,
    });
  },

  // Clip generation + review
  generateClip: (sceneId: string) =>
    request<Job>(`/scenes/${sceneId}/clip/generate`, { method: "POST" }),
  approveClip: (sceneId: string) =>
    request<Scene>(`/scenes/${sceneId}/clip/approve`, { method: "POST" }),

  // Jobs
  getJob: (jobId: string) => request<Job>(`/jobs/${jobId}`),
  listJobs: (id: string) => request<Job[]>(`/projects/${id}/jobs`),

  // Phase 4 quality
  listConsistency: (id: string) =>
    request<ConsistencyScore[]>(`/projects/${id}/consistency`),
  getBeatCuts: (id: string, segments: number) =>
    request<BeatCuts>(`/projects/${id}/beat-cuts?segments=${segments}`),

  // Render
  renderFinal: (id: string) =>
    request<RenderResult>(`/projects/${id}/render`, { method: "POST" }),
};
