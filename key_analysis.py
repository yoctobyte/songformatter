import re
from dataclasses import dataclass, field
from typing import Any, Callable
from collections import Counter

ALL_NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
NOTE_VALUES = {
    'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5,
    'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
}
MODE_INTERVALS = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
}
MAJOR_KEYS = ALL_NOTES
MINOR_KEYS = [note + "m" for note in ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']]
MAJOR_MINOR_KEYS = MAJOR_KEYS + MINOR_KEYS
MODAL_KEYS = []
for note in ALL_NOTES:
    MODAL_KEYS.append(note)
    MODAL_KEYS.append(note + "m")
    for mode_name in ["dorian", "mixolydian", "lydian", "phrygian", "locrian"]:
        MODAL_KEYS.append(f"{note} {mode_name}")
ALL_KEYS = list(dict.fromkeys(MODAL_KEYS))


@dataclass
class KeyCandidate:
    tonic: str
    mode: str
    label: str
    score: float
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        confidence_text = f"{self.confidence:.0%}" if self.confidence > 0 else f"score={self.score:.2f}"
        return f"{self.label} ({confidence_text})"


@dataclass
class DetectorResult:
    detector: str
    winner: KeyCandidate | None
    candidates: list[KeyCandidate]
    summary: str
    evidence: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)

    def to_text(self, verbose: bool = False) -> str:
        if not verbose:
            return f"{self.detector}: {self.summary}"

        lines = [f"{self.detector}: {self.summary}"]
        if self.candidates:
            lines.append("Top candidates: " + ", ".join(candidate.to_text() for candidate in self.candidates[:5]))
        if self.evidence:
            lines.append("Evidence: " + "; ".join(self.evidence))
        return " | ".join(lines)


@dataclass
class KeyAnalysisResult:
    detectors: list[DetectorResult]
    final: DetectorResult

    def to_text(self, verbose: bool = False) -> str:
        if not verbose:
            return self.final.to_text(verbose=False)
        return " || ".join(detector.to_text(verbose=True) for detector in self.detectors)


def _key_label_to_parts(label: str) -> tuple[str, str]:
    if label.endswith("m") and " " not in label:
        return (label[:-1], "minor")
    if " " in label:
        tonic, mode = label.split(" ", 1)
        return tonic, mode
    return (label, "major")


def _parts_to_label(tonic: str, mode: str) -> str:
    if mode == "major":
        return tonic
    if mode == "minor":
        return tonic + "m"
    return f"{tonic} {mode}"


def _scale_pitch_classes(label: str) -> list[int]:
    tonic, mode = _key_label_to_parts(label)
    root = NOTE_VALUES[tonic]
    intervals = MODE_INTERVALS[mode]
    return [(root + interval) % 12 for interval in intervals]


def _scale_intervals_for_mode(mode: str) -> set[int]:
    return set(MODE_INTERVALS[mode])


def _quality_bucket(chord: str) -> tuple[str | None, str]:
    match = re.match(r'^([A-G][b#]?)(.*?)(?:/([A-G][b#]?))?$', chord)
    if not match:
        return None, "unknown"

    suffix = match.group(2) or ""
    suffix_lower = suffix.lower()

    if suffix == "":
        return match.group(1), "major"
    if suffix_lower.startswith(("maj7", "maj9", "maj11")) or suffix.startswith(("M7", "M9", "M11")):
        return match.group(1), "major"
    if suffix_lower.startswith(("m7", "m9", "m6", "m11", "m13")) or suffix_lower == "m":
        return match.group(1), "minor"
    if suffix_lower.startswith("m"):
        return match.group(1), "minor"
    if "dim" in suffix_lower:
        return match.group(1), "diminished"
    if "aug" in suffix_lower or "+5" in suffix_lower or "7+" in suffix_lower:
        return match.group(1), "augmented"
    if "sus" in suffix_lower:
        return match.group(1), "suspended"
    if "7" in suffix_lower or "9" in suffix_lower or "11" in suffix_lower or "13" in suffix_lower:
        return match.group(1), "dominant"
    if "6" in suffix_lower:
        return match.group(1), "major"

    return match.group(1), "other"


def _degree_for_key(root: str, key_label: str) -> int | None:
    tonic, _mode = _key_label_to_parts(key_label)
    if root not in NOTE_VALUES:
        return None
    return (NOTE_VALUES[root] - NOTE_VALUES[tonic]) % 12


def _candidate_summary(prefix: str, winner: KeyCandidate | None, runner_up: KeyCandidate | None = None) -> str:
    if winner is None:
        return f"{prefix}: no key candidates"
    if runner_up is None:
        return f"{prefix}: {winner.label}"
    return f"{prefix}: {winner.label}, close to {runner_up.label}"


def _relative_partner(label: str) -> str | None:
    tonic, mode = _key_label_to_parts(label)
    if mode == "major":
        partner_pitch = (NOTE_VALUES[tonic] + 9) % 12
        return _parts_to_label(ALL_NOTES[partner_pitch], "minor")
    if mode == "minor":
        partner_pitch = (NOTE_VALUES[tonic] + 3) % 12
        return _parts_to_label(ALL_NOTES[partner_pitch], "major")
    return None


def _detector_decisiveness(result: DetectorResult) -> float:
    if not result.candidates:
        return 0.0
    top = result.candidates[0].confidence
    second = result.candidates[1].confidence if len(result.candidates) > 1 else 0.0
    gap = max(0.0, top - second)
    return 0.2 + 0.8 * gap


def _candidate_confidence_map(result: DetectorResult) -> dict[str, float]:
    return {candidate.label: candidate.confidence for candidate in result.candidates}


def _candidate_from_score(label: str, score: float, top_score: float, reason: str = "") -> KeyCandidate:
    tonic, mode = _key_label_to_parts(label)
    confidence = (score / top_score) if top_score > 0 else 0.0
    reasons = [reason] if reason else []
    return KeyCandidate(
        tonic=tonic,
        mode=mode,
        label=label,
        score=score,
        confidence=confidence,
        reasons=reasons,
    )


class NoteCountingDetector:
    name = "note_counting"

    def analyze(self, chords: list[str], chord_to_notes: Callable[[str], list[str]], sections: list[list[str]] | None = None) -> DetectorResult:
        del sections
        major_scales = {key: [ALL_NOTES[pitch] for pitch in _scale_pitch_classes(key)] for key in MAJOR_KEYS}
        minor_scales = {key: [ALL_NOTES[pitch] for pitch in _scale_pitch_classes(key)] for key in MINOR_KEYS}
        weights = [2, 2, 2, 1, 1, 1]

        note_counts = Counter()
        for chord in chords:
            note_counts.update(chord_to_notes(chord))

        key_scores = {}
        for key, scale in {**major_scales, **minor_scales}.items():
            key_scores[key] = sum(note_counts[note] * weights[i % len(weights)] for i, note in enumerate(scale))

        sorted_keys = sorted(key_scores.items(), key=lambda item: item[1], reverse=True)
        top_score = sorted_keys[0][1] if sorted_keys else 0.0
        candidates = [
            _candidate_from_score(
                key,
                score,
                top_score,
                reason="Weighted pitch collection overlap",
            )
            for key, score in sorted_keys[:6]
        ]
        winner = candidates[0] if candidates else None
        summary = _candidate_summary("Best pitch fit", winner, candidates[1] if len(candidates) > 1 else None)
        evidence = [
            "Counts chord tones across the full song",
            "Scores major and minor scales by weighted note overlap",
        ]

        return DetectorResult(
            detector=self.name,
            winner=winner,
            candidates=candidates,
            summary=summary,
            evidence=evidence,
            debug={
                "note_counts": dict(note_counts),
                "key_scores": key_scores,
            },
        )


class NoteCountingCircleOfFifthsDetector:
    name = "note_count_circle_of_fifths"

    def analyze(self, chords: list[str], chord_to_notes: Callable[[str], list[str]], sections: list[list[str]] | None = None) -> DetectorResult:
        del sections
        base_result = NoteCountingDetector().analyze(chords, chord_to_notes)
        key_scores = dict(base_result.debug.get("key_scores", {}))
        sorted_keys = sorted(key_scores.items(), key=lambda item: item[1], reverse=True)
        keys_in_order = [key for key, _ in sorted_keys]

        circle_of_fifths = [
            'F', 'Dm', 'C', 'Am', 'G', 'Em', 'D', 'Bm',
            'A', 'F#m', 'E', 'C#m', 'B', 'G#m', 'F#', 'D#m',
            'C#', 'A#m', 'G#', 'Fm', 'D#', 'Cm', 'A#', 'Gm'
        ]

        top_keys = keys_in_order[:6]
        best_match_score = -1
        best_index = 0

        for index in range(0, len(circle_of_fifths), 2):
            rotated_circle = circle_of_fifths[index:] + circle_of_fifths[:index]
            match_score = sum(rotated_circle[position] in top_keys for position in range(6))
            if match_score > best_match_score:
                best_match_score = match_score
                best_index = index

        likely_root_major_key = circle_of_fifths[best_index]
        likely_root_minor_key = circle_of_fifths[(best_index + 1) % len(circle_of_fifths)]
        major_count = chords.count(likely_root_major_key)
        minor_count = chords.count(likely_root_minor_key)
        winner_label = likely_root_major_key if major_count >= minor_count else likely_root_minor_key

        if winner_label in key_scores:
            boost = max(key_scores.values()) + 1.0 if key_scores else 1.0
            key_scores[winner_label] = boost

        sorted_keys = sorted(key_scores.items(), key=lambda item: item[1], reverse=True)
        top_score = sorted_keys[0][1] if sorted_keys else 0.0
        candidates = [
            _candidate_from_score(
                key,
                score,
                top_score,
                reason="Original circle-of-fifths post-processing",
            )
            for key, score in sorted_keys[:6]
        ]
        winner = next((candidate for candidate in candidates if candidate.label == winner_label), candidates[0] if candidates else None)
        summary = _candidate_summary("Circle-of-fifths fit", winner, candidates[1] if len(candidates) > 1 else None)

        return DetectorResult(
            detector=self.name,
            winner=winner,
            candidates=candidates,
            summary=summary,
            evidence=[
                f"Top note-count keys: {', '.join(top_keys)}",
                f"Circle pair: {likely_root_major_key} / {likely_root_minor_key}",
                f"Chord count tie-break: major={major_count}, minor={minor_count}",
            ],
            debug={
                "base_key_scores": base_result.debug.get("key_scores", {}),
                "top_keys": top_keys,
                "best_circle_index": best_index,
                "major_count": major_count,
                "minor_count": minor_count,
                "winner_label": winner_label,
            },
        )


class FunctionalHarmonyDetector:
    name = "functional_harmony"

    def analyze(self, chords: list[str], chord_to_notes: Callable[[str], list[str]], sections: list[list[str]] | None = None) -> DetectorResult:
        del chord_to_notes
        key_scores: dict[str, float] = {}
        key_evidence: dict[str, list[str]] = {}

        major_function_weights = {
            (0, "major"): 5.0,
            (7, "major"): 4.5,
            (5, "major"): 3.0,
            (2, "minor"): 2.5,
            (9, "minor"): 2.5,
            (4, "minor"): 1.5,
            (11, "diminished"): 1.0,
            (10, "major"): 1.5,
            (8, "major"): 1.2,
            (5, "minor"): 1.2,
        }
        minor_function_weights = {
            (0, "minor"): 5.0,
            (7, "minor"): 4.0,
            (7, "dominant"): 5.0,
            (5, "minor"): 3.0,
            (3, "major"): 2.5,
            (8, "major"): 2.5,
            (10, "major"): 1.5,
            (2, "diminished"): 1.2,
            (2, "minor"): 1.2,
        }

        for key in MAJOR_MINOR_KEYS:
            tonic, mode = _key_label_to_parts(key)
            del tonic
            key_scores[key] = 0.0
            key_evidence[key] = []
            function_weights = major_function_weights if mode == "major" else minor_function_weights

            for chord in chords:
                root, quality = _quality_bucket(chord)
                if root is None:
                    continue

                degree = _degree_for_key(root, key)
                base = function_weights.get((degree, quality))
                if base is None:
                    if degree in _scale_intervals_for_mode(mode):
                        base = 0.6
                    else:
                        base = -0.5

                key_scores[key] += base
                if base >= 3.5:
                    key_evidence[key].append(f"{chord} acts strongly in {key}")

            if sections:
                for section in sections:
                    if not section:
                        continue
                    section_start = section[0]
                    section_end = section[-1]
                    for anchor, weight, label in ((section_start, 1.0, "section start"), (section_end, 1.5, "section end")):
                        root, quality = _quality_bucket(anchor)
                        if root is None:
                            continue
                        degree = _degree_for_key(root, key)
                        if mode == "major" and degree == 0 and quality in {"major", "suspended"}:
                            key_scores[key] += weight
                            key_evidence[key].append(f"{label} on {anchor}")
                        elif mode == "minor" and degree == 0 and quality in {"minor", "suspended"}:
                            key_scores[key] += weight
                            key_evidence[key].append(f"{label} on {anchor}")

        sorted_keys = sorted(key_scores.items(), key=lambda item: item[1], reverse=True)
        top_score = sorted_keys[0][1] if sorted_keys else 0.0
        candidates = [
            _candidate_from_score(key, score, top_score, reason="Chord-function fit")
            for key, score in sorted_keys[:6]
        ]
        winner = candidates[0] if candidates else None
        summary = _candidate_summary("Functional harmony", winner, candidates[1] if len(candidates) > 1 else None)

        return DetectorResult(
            detector=self.name,
            winner=winner,
            candidates=candidates,
            summary=summary,
            evidence=key_evidence.get(winner.label, [])[:4] if winner else [],
            debug={"key_scores": key_scores},
        )


class CadenceDetector:
    name = "cadence"

    def analyze(self, chords: list[str], chord_to_notes: Callable[[str], list[str]], sections: list[list[str]] | None = None) -> DetectorResult:
        del chord_to_notes
        key_scores = {key: 0.0 for key in MAJOR_MINOR_KEYS}
        cadence_hits = {key: [] for key in MAJOR_MINOR_KEYS}

        progressions = list(zip(chords, chords[1:]))
        weighted_progressions = []
        for index, pair in enumerate(progressions):
            weight = 1.0
            if index >= max(0, len(progressions) - 4):
                weight += 1.5
            weighted_progressions.append((pair[0], pair[1], weight))

        if sections:
            for section in sections:
                for index, pair in enumerate(zip(section, section[1:])):
                    weight = 1.5
                    if index >= max(0, len(section) - 3):
                        weight += 2.0
                    weighted_progressions.append((pair[0], pair[1], weight))

        for key in MAJOR_MINOR_KEYS:
            tonic, mode = _key_label_to_parts(key)
            del tonic
            for first, second, weight in weighted_progressions:
                first_root, first_quality = _quality_bucket(first)
                second_root, second_quality = _quality_bucket(second)
                if first_root is None or second_root is None:
                    continue

                first_degree = _degree_for_key(first_root, key)
                second_degree = _degree_for_key(second_root, key)
                score = 0.0

                if mode == "major":
                    if first_degree == 7 and second_degree == 0 and first_quality in {"major", "dominant"} and second_quality in {"major", "suspended"}:
                        score = 5.0 * weight
                    elif first_degree == 2 and second_degree == 7 and first_quality == "minor":
                        score = 3.0 * weight
                    elif first_degree == 5 and second_degree == 0 and second_quality in {"major", "suspended"}:
                        score = 2.0 * weight
                    elif first_degree == 10 and second_degree == 0:
                        score = 1.5 * weight
                else:
                    if first_degree == 7 and second_degree == 0 and first_quality in {"major", "dominant", "minor"} and second_quality in {"minor", "suspended"}:
                        score = 4.5 * weight
                    elif first_degree == 5 and second_degree == 0 and first_quality == "minor" and second_quality in {"minor", "suspended"}:
                        score = 2.5 * weight
                    elif first_degree == 3 and second_degree == 7:
                        score = 2.0 * weight

                if score > 0:
                    key_scores[key] += score
                    cadence_hits[key].append(f"{first} -> {second}")

        sorted_keys = sorted(key_scores.items(), key=lambda item: item[1], reverse=True)
        top_score = sorted_keys[0][1] if sorted_keys else 0.0
        candidates = [
            _candidate_from_score(key, score, top_score, reason="Cadence evidence")
            for key, score in sorted_keys[:6]
        ]
        winner = candidates[0] if candidates else None
        summary = _candidate_summary("Cadence", winner, candidates[1] if len(candidates) > 1 else None)

        return DetectorResult(
            detector=self.name,
            winner=winner,
            candidates=candidates,
            summary=summary,
            evidence=cadence_hits.get(winner.label, [])[:4] if winner else [],
            debug={"key_scores": key_scores, "cadence_hits": cadence_hits},
        )


class TonicEmphasisDetector:
    name = "tonic_emphasis"

    def analyze(self, chords: list[str], chord_to_notes: Callable[[str], list[str]], sections: list[list[str]] | None = None) -> DetectorResult:
        del chord_to_notes
        key_scores = {key: 0.0 for key in MAJOR_MINOR_KEYS}
        chord_counter = Counter(chords)
        anchor_positions = []
        if chords:
            anchor_positions.append((chords[0], 3.0, "opening"))
            anchor_positions.append((chords[-1], 5.0, "ending"))
        if sections:
            for section in sections:
                if section:
                    anchor_positions.append((section[0], 2.5, "section opening"))
                    anchor_positions.append((section[-1], 3.5, "section ending"))
        for chord, count in chord_counter.items():
            if count > 1:
                anchor_positions.append((chord, min(3.0, 1.0 + count * 0.5), "repetition"))

        key_evidence = {key: [] for key in MAJOR_MINOR_KEYS}

        for key in MAJOR_MINOR_KEYS:
            for chord, weight, source in anchor_positions:
                root, quality = _quality_bucket(chord)
                if root is None:
                    continue
                degree = _degree_for_key(root, key)
                if degree == 0:
                    key_scores[key] += weight * (1.3 if quality in {"major", "minor"} else 1.0)
                    key_evidence[key].append(f"{source} anchor on {chord}")
                elif degree in {7, 5}:
                    key_scores[key] += weight * 0.4

        sorted_keys = sorted(key_scores.items(), key=lambda item: item[1], reverse=True)
        top_score = sorted_keys[0][1] if sorted_keys else 0.0
        candidates = [
            _candidate_from_score(key, score, top_score, reason="Tonic emphasis")
            for key, score in sorted_keys[:6]
        ]
        winner = candidates[0] if candidates else None
        summary = _candidate_summary("Tonic emphasis", winner, candidates[1] if len(candidates) > 1 else None)

        return DetectorResult(
            detector=self.name,
            winner=winner,
            candidates=candidates,
            summary=summary,
            evidence=key_evidence.get(winner.label, [])[:4] if winner else [],
            debug={"key_scores": key_scores},
        )


class ScaleFitDetector:
    name = "scale_fit"

    def analyze(self, chords: list[str], chord_to_notes: Callable[[str], list[str]], sections: list[list[str]] | None = None) -> DetectorResult:
        del sections
        note_counts = Counter()
        for chord in chords:
            note_counts.update(chord_to_notes(chord))

        key_scores: dict[str, float] = {}
        mode_hits: dict[str, list[str]] = {}

        for key in ALL_KEYS:
            tonic, mode = _key_label_to_parts(key)
            del tonic
            scale_notes = {ALL_NOTES[pitch] for pitch in _scale_pitch_classes(key)}
            in_scale = sum(count for note, count in note_counts.items() if note in scale_notes)
            out_scale = sum(count for note, count in note_counts.items() if note not in scale_notes)
            modal_bonus = 0.0 if mode in {"major", "minor"} else 1.0
            key_scores[key] = in_scale - (out_scale * 1.4) + modal_bonus
            mode_hits[key] = [note for note in note_counts if note in scale_notes]

        sorted_keys = sorted(key_scores.items(), key=lambda item: item[1], reverse=True)
        top_score = sorted_keys[0][1] if sorted_keys else 0.0
        candidates = [
            _candidate_from_score(key, score, top_score, reason="Scale-fit match")
            for key, score in sorted_keys[:8]
        ]
        winner = candidates[0] if candidates else None
        summary = _candidate_summary("Scale fit", winner, candidates[1] if len(candidates) > 1 else None)

        return DetectorResult(
            detector=self.name,
            winner=winner,
            candidates=candidates,
            summary=summary,
            evidence=[
                f"Scale tones matched: {', '.join(mode_hits.get(winner.label, [])[:7])}" if winner else "No scale match",
                "Tests major, minor, and common modal collections",
            ],
            debug={"key_scores": key_scores, "note_counts": dict(note_counts)},
        )


class ViolationCountDetector:
    name = "violation_count"

    def analyze(self, chords: list[str], chord_to_notes: Callable[[str], list[str]], sections: list[list[str]] | None = None) -> DetectorResult:
        del sections
        del chord_to_notes
        penalties: dict[str, float] = {}
        penalty_evidence: dict[str, list[str]] = {}

        for key in ALL_KEYS:
            tonic, mode = _key_label_to_parts(key)
            del tonic
            allowed_intervals = _scale_intervals_for_mode(mode)
            penalties[key] = 0.0
            penalty_evidence[key] = []

            for chord in chords:
                root, quality = _quality_bucket(chord)
                if root is None:
                    continue

                degree = _degree_for_key(root, key)
                penalty = 0.0

                if degree not in allowed_intervals:
                    penalty += 2.0
                else:
                    penalty += 0.0

                if mode == "major":
                    if degree == 10 and quality == "major":
                        penalty += 0.5  # bVII, common borrowed
                    elif degree == 8 and quality == "major":
                        penalty += 0.6  # bVI
                    elif degree == 5 and quality == "minor":
                        penalty += 0.5  # iv borrowed
                    elif degree == 7 and quality in {"major", "dominant"}:
                        penalty += 0.0
                    elif degree == 11 and quality == "diminished":
                        penalty += 0.1
                    elif degree in allowed_intervals and quality not in {"major", "minor", "dominant", "diminished", "suspended"}:
                        penalty += 0.4
                elif mode == "minor":
                    if degree == 7 and quality in {"major", "dominant"}:
                        penalty += 0.0  # harmonic minor dominant
                    elif degree == 7 and quality == "minor":
                        penalty += 0.4  # natural minor v
                    elif degree == 10 and quality == "major":
                        penalty += 0.2  # VII
                    elif degree == 3 and quality == "major":
                        penalty += 0.1  # III
                    elif degree == 2 and quality == "diminished":
                        penalty += 0.1
                    elif degree in allowed_intervals and quality not in {"major", "minor", "dominant", "diminished", "suspended"}:
                        penalty += 0.4
                else:
                    if degree not in allowed_intervals:
                        penalty += 0.8
                    elif quality == "dominant" and mode not in {"mixolydian"}:
                        penalty += 0.3
                    elif quality == "diminished" and mode not in {"locrian", "minor"}:
                        penalty += 0.3

                penalties[key] += penalty
                if penalty >= 1.0:
                    penalty_evidence[key].append(f"{chord}: +{penalty:.1f}")

        sorted_penalties = sorted(penalties.items(), key=lambda item: item[1])
        best_penalty = sorted_penalties[0][1] if sorted_penalties else 0.0
        transformed_scores = {key: 1.0 / (1.0 + penalty - best_penalty) for key, penalty in penalties.items()}
        top_score = max(transformed_scores.values()) if transformed_scores else 0.0
        candidates = [
            _candidate_from_score(key, transformed_scores[key], top_score, reason=f"Violation penalty={penalty:.2f}")
            for key, penalty in sorted_penalties[:8]
        ]
        winner = candidates[0] if candidates else None
        summary = _candidate_summary("Lowest violations", winner, candidates[1] if len(candidates) > 1 else None)

        return DetectorResult(
            detector=self.name,
            winner=winner,
            candidates=candidates,
            summary=summary,
            evidence=penalty_evidence.get(winner.label, [])[:6] if winner else [],
            debug={"penalties": penalties, "scores": transformed_scores},
        )


class WeightedDetector:
    name = "weighted"

    def analyze(self, detector_results: list[DetectorResult], detector_weights: dict[str, float] | None = None) -> DetectorResult:
        detector_weights = {
            "note_counting": 1.0,
            "note_count_circle_of_fifths": 1.0,
            "functional_harmony": 1.25,
            "cadence": 1.25,
            "tonic_emphasis": 1.0,
            "scale_fit": 1.5,
            "violation_count": 1.5,
            **(detector_weights or {}),
        }
        combined_scores: dict[str, float] = {}
        evidence: list[str] = []

        for result in detector_results:
            base_weight = detector_weights.get(result.detector, 1.0)
            decisiveness = _detector_decisiveness(result)
            weight = base_weight * decisiveness
            for candidate in result.candidates:
                combined_scores[candidate.label] = combined_scores.get(candidate.label, 0.0) + candidate.confidence * weight
            if result.winner is not None:
                evidence.append(f"{result.detector} -> {result.winner.label} (x{weight:.2f})")

        center_detectors = [result for result in detector_results if result.detector in {"functional_harmony", "cadence", "tonic_emphasis"}]
        center_scores: dict[str, float] = {}
        for result in center_detectors:
            local_weight = detector_weights.get(result.detector, 1.0) * _detector_decisiveness(result)
            for label, confidence in _candidate_confidence_map(result).items():
                center_scores[label] = center_scores.get(label, 0.0) + confidence * local_weight

        for label in list(combined_scores.keys()):
            partner = _relative_partner(label)
            if partner is None or partner not in combined_scores:
                continue

            pair_top = max(combined_scores[label], combined_scores[partner])
            if abs(combined_scores[label] - combined_scores[partner]) > 0.35 * max(1.0, pair_top):
                continue

            label_center = center_scores.get(label, 0.0)
            partner_center = center_scores.get(partner, 0.0)
            diff = label_center - partner_center
            if abs(diff) >= 0.15:
                bonus = min(0.6, abs(diff) * 0.5)
                favored = label if diff > 0 else partner
                combined_scores[favored] = combined_scores.get(favored, 0.0) + bonus
                evidence.append(f"relative_pair_resolver -> {favored} (+{bonus:.2f})")

        sorted_scores = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)
        top_score = sorted_scores[0][1] if sorted_scores else 0.0
        candidates = [
            _candidate_from_score(
                key,
                score,
                top_score,
                reason="Weighted detector agreement",
            )
            for key, score in sorted_scores[:6]
        ]
        winner = candidates[0] if candidates else None
        summary = f"Combined result: {winner.label}" if winner else "No combined result"

        return DetectorResult(
            detector=self.name,
            winner=winner,
            candidates=candidates,
            summary=summary,
            evidence=evidence,
            debug={
                "combined_scores": combined_scores,
                "detector_weights": detector_weights,
            },
        )


def analyze_key(
    chords: list[str],
    *,
    chord_to_notes: Callable[[str], list[str]],
    sections: list[list[str]] | None = None,
    detector_weights: dict[str, float] | None = None,
) -> KeyAnalysisResult:
    detectors = [
        NoteCountingDetector(),
        NoteCountingCircleOfFifthsDetector(),
        FunctionalHarmonyDetector(),
        CadenceDetector(),
        TonicEmphasisDetector(),
        ScaleFitDetector(),
        ViolationCountDetector(),
    ]

    detector_results = [detector.analyze(chords, chord_to_notes, sections=sections) for detector in detectors]
    final_result = WeightedDetector().analyze(detector_results, detector_weights=detector_weights)
    all_results = detector_results + [final_result]
    return KeyAnalysisResult(detectors=all_results, final=final_result)
