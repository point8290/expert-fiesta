"""P4-S6 — Beat-synced cut suggestions.

Given the detected beats and the track duration, suggest interior cut points that
divide the song into ``segments`` even parts, each snapped to the nearest beat so
edits land on the music.
"""


def _snap(t: float, beats: list[float]) -> float:
    return min(beats, key=lambda b: abs(b - t))


def suggest_cuts(beats: list[float], duration: float, segments: int) -> list[float]:
    if not beats or segments < 2 or duration <= 0:
        return []
    step = duration / segments
    cuts: list[float] = []
    for i in range(1, segments):
        snapped = _snap(i * step, beats)
        if snapped not in cuts and 0 < snapped < duration:
            cuts.append(snapped)
    return sorted(cuts)
