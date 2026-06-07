"""P4-S4 — Character consistency scoring.

Compares a generated keyframe against a character's approved reference via face
embeddings and returns a cosine similarity in [0, 1]. The pipeline depends only
on the ``ConsistencyScorer`` protocol so tests inject a fake and the embedding
model stays an isolated runtime detail.
"""
from typing import Protocol


class ConsistencyScorer(Protocol):
    def score(self, reference_path: str, candidate_path: str) -> float:
        ...


class FaceEmbeddingScorer:
    """Real scorer using a face-embedding model. Not exercised by unit tests."""

    def score(self, reference_path: str, candidate_path: str) -> float:
        import numpy as np
        from insightface.app import FaceAnalysis  # heavy, runtime-only

        app = getattr(self, "_app", None)
        if app is None:
            app = FaceAnalysis(name="buffalo_l")
            app.prepare(ctx_id=-1)
            self._app = app

        def embed(path: str):
            import cv2

            faces = app.get(cv2.imread(path))
            return faces[0].normed_embedding if faces else None

        a, b = embed(reference_path), embed(candidate_path)
        if a is None or b is None:
            return 0.0
        return float(np.dot(a, b))  # both are L2-normalized
