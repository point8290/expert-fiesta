// Mirrors the backend camelCase API contract (see backend/app/schemas.py).

export interface Project {
  id: string;
  title: string;
  idea: string;
  genre: string;
  mood: string;
  visualStyle: string;
  targetDuration: number;
  aspectRatio: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectCreate {
  title: string;
  idea: string;
  genre: string;
  mood: string;
  visualStyle: string;
  targetDuration: number;
  aspectRatio: string;
}

export interface Lyrics {
  title: string;
  structure: string[];
  body: string;
  musicPrompt: string;
  emotionalArc: string;
}

export interface Audio {
  projectId: string;
  filename: string;
  contentType: string;
  source: string;
  durationSeconds: number | null;
  bpm: number | null;
  beats: number[] | null;
  sections: Array<{ name: string; start: number; end: number }> | null;
  waveform: number[] | null;
}

export interface Scene {
  id: string;
  projectId: string;
  number: number;
  startTime: number;
  endTime: number;
  durationSeconds: number;
  sectionName: string;
  visualDescription: string;
  cameraInstruction: string;
  motionInstruction: string;
  keyframePrompt: string;
  videoPrompt: string;
  negativePrompt: string;
  keyframePath: string | null;
  keyframeStatus: string;
  clipPath: string | null;
  clipStatus: string;
}

export interface RenderResult {
  projectId: string;
  status: string;
  outputPath: string;
}
