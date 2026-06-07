import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CharacterCard } from "./CharacterCard";
import type { Character } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  api: {
    generateCharacterReference: vi.fn().mockResolvedValue({
      id: "c1",
      refStatus: "generated",
    }),
    approveCharacterReference: vi.fn(),
  },
}));

const character: Character = {
  id: "c1",
  projectId: "p1",
  name: "Aarav",
  age: "10",
  face: "round face",
  hair: "messy black hair",
  clothing: "yellow hoodie",
  personality: "curious",
  identityAnchors: ["yellow hoodie", "messy black hair"],
  refImagePath: null,
  refStatus: "pending",
  loraPath: null,
};

describe("CharacterCard", () => {
  it("shows the name and identity anchors", () => {
    render(<CharacterCard character={character} onChange={() => {}} />);
    expect(screen.getByText(/Aarav/)).toBeInTheDocument();
    expect(screen.getByText(/Anchors:/)).toHaveTextContent("yellow hoodie");
    expect(screen.getByText(/pending/)).toBeInTheDocument();
  });

  it("generates a reference image on click", async () => {
    const { api } = await import("@/lib/api");
    render(<CharacterCard character={character} onChange={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /reference/i }));
    expect(api.generateCharacterReference).toHaveBeenCalledWith("c1");
  });
});
