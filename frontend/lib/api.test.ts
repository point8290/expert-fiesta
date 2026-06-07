import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "./api";
import { clearToken, setToken } from "./auth";

function mockFetch(body: unknown, ok = true, status = 200) {
  const fn = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
  clearToken();
});

describe("api client", () => {
  it("lists projects via GET /projects", async () => {
    const fetchMock = mockFetch([{ id: "1", title: "A" }]);
    const projects = await api.listProjects();
    expect(projects).toHaveLength(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/projects$/);
    expect(init?.method ?? "GET").toBe("GET");
  });

  it("creates a project with a JSON body", async () => {
    const fetchMock = mockFetch({ id: "1", title: "A" });
    await api.createProject({
      title: "A",
      idea: "i",
      genre: "g",
      mood: "m",
      visualStyle: "v",
      targetDuration: 60,
      aspectRatio: "16:9",
    });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/projects$/);
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string).title).toBe("A");
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe(
      "application/json"
    );
  });

  it("generates a storyboard via POST", async () => {
    const fetchMock = mockFetch([{ id: "s1", number: 1 }]);
    const scenes = await api.generateStoryboard("p1");
    expect(scenes).toHaveLength(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/projects\/p1\/storyboard$/);
    expect(init?.method).toBe("POST");
  });

  it("uploads audio as multipart form data", async () => {
    const fetchMock = mockFetch({ projectId: "p1", filename: "s.wav" });
    const file = new File([new Uint8Array([1, 2, 3])], "s.wav", {
      type: "audio/wav",
    });
    await api.uploadAudio("p1", file);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/projects\/p1\/audio$/);
    expect(init?.method).toBe("POST");
    expect(init?.body).toBeInstanceOf(FormData);
  });

  it("throws ApiError with status on a failed response", async () => {
    mockFetch({ detail: "nope" }, false, 404);
    await expect(api.getProject("missing")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
    });
  });

  it("generates characters via POST", async () => {
    const fetchMock = mockFetch([{ id: "c1", name: "Aarav" }]);
    const chars = await api.generateCharacters("p1");
    expect(chars).toHaveLength(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/projects\/p1\/characters$/);
    expect(init?.method).toBe("POST");
  });

  it("generates a character reference image", async () => {
    const fetchMock = mockFetch({ id: "c1", refStatus: "generated" });
    await api.generateCharacterReference("c1");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/characters\/c1\/reference$/);
    expect(init?.method).toBe("POST");
  });

  it("generates a scene keyframe", async () => {
    const fetchMock = mockFetch({ id: "s1", keyframeStatus: "generated" });
    await api.generateKeyframe("s1");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/scenes\/s1\/keyframe$/);
    expect(init?.method).toBe("POST");
  });

  it("generates a clip and returns a job", async () => {
    const fetchMock = mockFetch({ id: "j1", type: "clip", status: "succeeded" });
    const job = await api.generateClip("s1");
    expect(job.type).toBe("clip");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/scenes\/s1\/clip\/generate$/);
    expect(init?.method).toBe("POST");
  });

  it("lists project jobs", async () => {
    const fetchMock = mockFetch([{ id: "j1", type: "clip" }]);
    const jobs = await api.listJobs("p1");
    expect(jobs).toHaveLength(1);
    const [url] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/projects\/p1\/jobs$/);
  });

  it("lists consistency scores", async () => {
    const fetchMock = mockFetch([{ sceneId: "s1", characterId: "c1", score: 0.9 }]);
    const scores = await api.listConsistency("p1");
    expect(scores[0].score).toBe(0.9);
    const [url] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/projects\/p1\/consistency$/);
  });

  it("fetches beat-synced cut suggestions with a segment count", async () => {
    const fetchMock = mockFetch({ cuts: [14.5, 29.7, 45.6] });
    const result = await api.getBeatCuts("p1", 4);
    expect(result.cuts).toHaveLength(3);
    const [url] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/projects\/p1\/beat-cuts\?segments=4$/);
  });

  it("attaches the auth token as a Bearer header when present", async () => {
    setToken("jwt-123");
    const fetchMock = mockFetch([]);
    await api.listProjects();
    const [, init] = fetchMock.mock.calls[0];
    const headers = init?.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer jwt-123");
  });

  it("sends no Authorization header when logged out", async () => {
    const fetchMock = mockFetch([]);
    await api.listProjects();
    const [, init] = fetchMock.mock.calls[0];
    const headers = (init?.headers ?? {}) as Record<string, string>;
    expect(headers["Authorization"]).toBeUndefined();
  });

  it("logs in and returns a token", async () => {
    const fetchMock = mockFetch({ accessToken: "t", tokenType: "bearer" });
    const token = await api.login("a@x.com", "secret123");
    expect(token.accessToken).toBe("t");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/auth\/login$/);
    expect(JSON.parse(init?.body as string).email).toBe("a@x.com");
  });

  it("registers a new account", async () => {
    const fetchMock = mockFetch({ accessToken: "t", tokenType: "bearer" });
    await api.register("a@x.com", "secret123");
    const [url] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/auth\/register$/);
  });
});
