# 4-SYSTEM/scripts

Standalone scripts that are not bundled inside a single skill — either because several skills use them, or because they are vault-maintenance tools rather than steps in a workflow.

A script that belongs to exactly one skill lives in that skill's own `scripts/` folder instead, so the skill stays self-contained and can be installed anywhere.

| Script | What it does |
| ------ | ------------ |
| `install-skills.py` | Installs skills from the shared skill library into `4-SYSTEM/Skills/`, resolving the library's logical location names to this vault's paths and writing the `.claude/commands/` stubs. See [`../How-to guides/Sync with rails-template.md`](../How-to%20guides/Sync%20with%20rails-template.md). |
| `linter-root-text/` · `linter-commentary/` | Lint a root text or a commentary in `1-SOURCES/` against the API rules (frontmatter, block IDs, TOC headings, yigchungs, durchens `[^dN]`, footnotes `[^fN]`, `tag_ids`) and write `output/<stem>.lint.json`. Run before the parser. See each folder's `README.md`. |
| `parser-root-text/` · `parser-commentary/` | Turn a linted source into the API payloads in `output/<stem>/`: text, edition, TOC, yigchungs, durchens, footnotes (by position) and, for a commentary, its alignment to the root text. The four tools share `durchen.py`, kept byte-identical. They are what the `library-upload` skill runs, so what is uploaded is exactly what this vault's linter checked and parser produced. Vendored: see each folder's `UPSTREAM.md`. |
| `linter-audio/` | Parse (`audio_note.py`) and lint (`lint_audio.py`) the audio notes in `1-SOURCES/Audio/` against the v2 audio API and build their upload payloads; with `--live --host dev\|testing\|prod` it also places every timed Mapping row in the live edition (the cue spans). What the `library-upload` skill runs for audio. See its `README.md`. |
| `otr_to_mapping.py` | Fill an audio note's Mapping table from its oTranscribe `.otr` timestamps (skill `otr-to-mapping`). Dry run unless `--write`; checks the rebuilt note with `linter-audio` first. |
| `audio_notes_to_m4a.py` | After the WAVs are converted (skill `convert-audio`), point each audio note at its `.m4a` and keep the WAV's details under `converted_from:`. Dry run unless `--write`. |
| `uploader-root-text/` | **Superseded by the `library-upload` skill** — use that. Kept for reference: posts a parser output folder to the library API (text, edition, TOC, alignment) and writes the ids into the frontmatter. **It sends for real unless you pass `--dry-run`**, and its `--recreate` **deletes** the edition and the text and creates new ones (new ids, broken links) — never use it on a published text. Vendored: see its `UPSTREAM.md` and `README.md`. |
## Conventions

**Vendored code records its upstream.** If you copy a tool in from another repository rather than writing it here, put an `UPSTREAM.md` beside it recording the source repository, the path, the commit it was pinned at, and the date. Make the first commit byte-identical to upstream so that every later commit reads as your delta — then a re-sync is a diff rather than an archaeology exercise. Say in the same file *why* it was forked, and whether the changes should be offered back upstream.

**Nothing here writes to `1-SOURCES/` in place.** Scripts may create whole files from reviewed inbox material; they may not rewrite a source file's content. Two exceptions, both dry runs unless `--write`: `otr_to_mapping.py` and `audio_notes_to_m4a.py` rewrite the metadata of audio notes (the Mapping times, the recording's file details), never a text.

**Credentials never live in the repository.** A script that needs one reads it from the environment or from a `.env` file that is git-ignored, and ships a `.env.example` containing **placeholders only** — never a real address, password or token, even an expired one.

**A linter's or parser's output goes in its own `output/` folder** (`linter-root-text/output/`, `parser-root-text/output/`, `linter-audio/output/`, …): other tools read it from there (`library-upload`, `translation-alignment-check`). It is not git-ignored: it stays untracked while texts are only on dev/testing and is committed once they are on prod. Any other generated output goes to `0-INBOX/`, not into this folder.
