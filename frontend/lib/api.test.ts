import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "./api";

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
});
