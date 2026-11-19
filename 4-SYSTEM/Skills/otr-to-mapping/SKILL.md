---
name: otr-to-mapping
description: >
  Fill an audio note's Mapping table (Start/End per root-text block) from its oTranscribe
  .otr timestamps, check it with the audio linter, and prepare the cues for upload.
  Trigger whenever asked to read an .otr, add or update timestamps / cues / the Mapping
  table of a *-recitation.md audio note, or when new .otr files have arrived in
  1-SOURCES/Audio/<text>/otr/. Needs skill library-upload installed (its scripts).
---

# otr-to-mapping

Recordings are transcribed in oTranscribe; each text folder may get an `otr/<name>.otr`
(JSON: the transcript as HTML with `<span class="timestamp" data-timestamp="SECONDS">`
marks). The .otr files arrive a few at a time, so audio is uploaded first (audio +
recording, skill `library-upload`) and the cues follow when the timestamps exist.

## Inputs

```
1-SOURCES/Audio/<text>/audio/<lang>-<artist>-recitation.md   ← Mapping table here
1-SOURCES/Audio/<text>/otr/<name>.otr                        ← timestamps
1-SOURCES/Text/<text>.md                                     ← block ids ^id (the note's root_text)
```

The script ships with `library-upload` (it uses that skill's audio parser and linter):
`4-SYSTEM/Skills/library-upload/scripts/otr_to_mapping.py`.

## Output

The note's `## Mapping` table, rewritten in place (only with `--write`).

## Output file format

```
| #   | Section | Text (first line)              | Start    | End      |
| --- | ------- | ------------------------------ | -------- | -------- |
| 0   | ^0      | ༄༅། །ཁྱུང་པོའི་སྨོན་ལམ།        |          |          |
| 1   | ^1      | སྐུ་གསུམ་མཁྱེན་བཅུ་ཆོས་ཀྱི་རྗེ། ། | 0:05.427 | 0:15.812 |
```

`#` = row number from 0, **Section = the root block id (`^id`)**, Text = first line,
Start/End in `m:ss.sss`. Untimed rows (title, colophon) stay, empty.

## Rules

1. Never edit the .otr files, and never hand-edit Start/End to make a check pass.
2. One cue covers one whole block: a timestamp inside a block (a refrain, a split line) is
   reported and not used.
3. Start = the block's timestamp, End = the next timed block's Start; the last ends with the
   recording (`duration_seconds`).
4. The rebuilt note goes through the audio linter before it is written; a Mapping or cue
   error means it is not written.

## Procedure

1. Dry run — what would change, for every note with an .otr (or one text folder):
   `python 4-SYSTEM/Skills/library-upload/scripts/otr_to_mapping.py --live ["1-SOURCES/Audio/<text>"]`
   (`--live` checks every timed block's text in the root's live edition on dev, which is
   where the cue spans come from; use it unless offline).
2. Write: `… otr_to_mapping.py --live --write "1-SOURCES/Audio/<text>"`. A note already up to
   date prints `up to date`; running twice changes nothing.
3. Differences between transcript and root text: `… otr_to_mapping.py --detail "1-SOURCES/Audio/<text>"`.
4. Send the cues with `library-upload` (recording already uploaded), after the person's yes:
   `python 4-SYSTEM/Skills/library-upload/scripts/library.py audio push --env dev --only cues "1-SOURCES/Audio/<text>"`
   then the same with `--yes`.

| Line | Meaning |
|------|---------|
| `N timestamps, M block starts` | M < N when some stamps fall inside blocks |
| `timestamp(s) inside a block` | sub-block stamps, ignored; fine for refrains |
| `spoken blocks with no timestamp` | usually the colophon or a title, not recited |
| `text difference(s)` | transcript and root text differ; `--detail` |
| `W [mapping-short]` | a cue under 1 s: two stamps almost on top of each other — check in oTranscribe |
| `W [cue-partial]` | the live edition merges/splits that block differently; the cue still gets a span |
| `E [cue-text]` | the block's text is not in the live edition: not written |
| `E … matches no block` | a table row the script cannot place; fix the row by hand first |

## Completion check

- [ ] Which notes were written, how many rows got times — reported.
- [ ] Every `E` / `W` line quoted.
- [ ] Cues sent only after the person's yes, via `library-upload`.
