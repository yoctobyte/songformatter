# Handover

## Current Branch / Commit

- Branch: `dev`
- Commit: `a5c55bd`
- Commit message: `Add multi-document workflow and key analysis framework`

## What Changed

- Added a local source runner:
  - `run.sh`
  - `requirements.txt`
- Added `.gitignore` for:
  - `.venv/`
  - Python cache files
  - app-local runtime/workspace files
- Removed the stale `test2` import and made `SongFormatter.py` explicit about its imports.

## UI / Workflow Changes

- The app is now multi-document.
- Main shell is in `SongFormatter.py`.
- Documents live in a document notebook under the `Documents` tab.
- Added:
  - `New`
  - `Load`
  - `Paste As New`
  - `Close`
  - `Save`
  - `Save As`
  - `Save PDF`
  - `Export Both`
- Session restore is implemented via `.songformatter_workspace/session.json`.
- Document tabs track dirty state and show `*` in tab titles.
- Reusable blank tab logic exists for:
  - `New`
  - `Load`
  - `Paste As New`
- Tab interactions:
  - middle click closes a tab
  - right click opens a small tab context menu

## Settings Changes

- `settings.py` now defines explicit default settings via `DEFAULT_SETTINGS`.
- Settings UI is scrollable.
- Boolean settings render as checkboxes.
- Settings now map directly to real renderer defaults instead of relying on ad hoc key creation.

## Key Analysis Architecture

- New module: `key_analysis.py`
- Structured result model:
  - `KeyCandidate`
  - `DetectorResult`
  - `KeyAnalysisResult`
- Each detector returns the same structure.
- `weighted` is also a normal detector result.

## Active Key Detectors

- `note_counting`
- `note_count_circle_of_fifths`
- `functional_harmony`
- `cadence`
- `tonic_emphasis`
- `scale_fit`
- `violation_count`
- `weighted`

## Key Analysis UI

- Key analysis now autoruns during preview rendering.
- Each `FormatText` document caches its latest analysis in:
  - `self.last_key_analysis`
- Bottom status bar shows a compact summary:
  - final key
  - alternate candidate
  - detector agreement count
- `Tools > Key Analysis` opens a modeless analysis window.
- That window is grouped into:
  - `Tonal Detectors`
  - `Modal Detectors`
  - `Combined`

## Current State Of Key Detection

- The framework is working and useful for comparison/debugging.
- It is not fully trustworthy yet for final musical output.
- The biggest current issue is distinguishing:
  - shared pitch collection
  - actual tonal center
- Example already discussed in-session:
  - a song that feels like `Am`
  - but local `Dm -> G -> C` motion still pulls some detectors toward `C`

### Important Notes

- `scale_fit` and `violation_count` are currently best understood as collection/mode-family detectors.
- They are not yet strong center detectors.
- `functional_harmony`, `cadence`, and `tonic_emphasis` are more center-oriented.
- `weighted` now:
  - discounts flat/ambiguous detectors via a decisiveness factor
  - includes a relative major/minor resolver
  - uses center-oriented detectors to break close relative-pair ties

## Section Awareness

- `analyze_song_key()` in `convertrawtext.py` now extracts sections from:
  - blank lines
  - lines starting with `*`
  - lines starting with `-`
- Those sections are passed into `key_analysis.analyze_key(...)`.
- Section starts and ends now influence:
  - `functional_harmony`
  - `cadence`
  - `tonic_emphasis`

## Still Pending / Worth Doing Next

1. Improve center detection for relative major/minor cases.
   - Current issue: local `ii-V-I` style motion can still outweigh broader section/home evidence.

2. Decide whether modal detectors should:
   - stay collection detectors only
   - or become true center detectors too

3. Remove legacy dead code from `convertrawtext.py`.
   - Old functions like `determine_key()` / `make_key_suggestions()` still exist but are no longer the active path.

4. Move key debug text fully out of the preview PDF.
   - User explicitly said this should eventually happen.
   - For now it intentionally still remains in the preview.

5. Consider future key metadata behavior.
   - Auto-filling `Key: X` in the header was discussed.
   - This should only happen after analysis becomes trustworthy enough.

## Verification Already Done

- `python3 -m py_compile SongFormatter.py convertrawtext.py settings.py pdfviewer.py key_analysis.py`
  passed after the latest changes.

## Practical Advice For The Next Agent

- Do not treat the current weighted result as “correct”; treat it as the current best combiner.
- Use the analysis window to compare detector behavior before changing weights.
- The simplest detector (`note_counting`) is still a useful baseline and is sometimes closest to the musically correct answer.
