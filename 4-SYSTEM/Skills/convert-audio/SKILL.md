---
name: convert-audio
description: >
  Convert recitation recordings (WAV/AIFF) to small AAC .m4a files with exactly the same
  length, on Windows or macOS, with nothing to install. Trigger whenever someone wants to
  convert, compress or shrink audio recordings, turn WAV into m4a/AAC, or has a recording
  too big to upload ("over 50 MB", "413", "file too large").
---

# convert-audio

The library takes uploads up to about **50 MB**. Studio recordings are uncompressed WAV,
about 23 MB per minute. AAC (.m4a) makes them about **24× smaller** (a 26-minute, 579 MB
WAV becomes 24 MB) with no audible difference for recitation, and the converted file has
exactly the same number of samples, so timestamps and cues made on the WAV stay right.

The conversion runs on the person's own computer with the encoder that comes with the
operating system: nothing to install, and the audio never goes to any website. Your job is
to run the right script and explain the result — never open or read the audio itself.

## Inputs

- The recordings: `.wav` (and `.aif` / `.aiff` on a Mac) files or folders, as the person names them.
- The operating system, from your environment info.

## Output

An `.m4a` next to each original (or under `-OutDir` / `-o`), with the folder layout kept.
The originals are never changed, moved or deleted.

## Output file format

AAC-LC in an MP4 container, 128 kbps by default, the source's sample rate (48/44.1 kHz)
and channels, and an edit list marking the encoder's padding, so the file plays exactly
the source's samples.

## Rules

1. Only WAV/AIFF are converted. MP3, M4A and FLAC are already compressed: converting again
   only loses quality; if one is over 50 MB, tell the person instead.
2. Keep 128 kbps unless the person asks, or a file is still over 50 MB (then 96, or 64 for speech).
3. Never delete, rename or move an original; remind the person to keep the WAVs as masters.
4. Do not upload anything; that is skill `library-upload`, a separate step.

## Procedure

1. Which computer: `win32` → Windows script; `darwin` → Mac script; anything else → stop
   (only Windows and macOS). If unsure, `uname` prints `Darwin` on a Mac and fails on Windows.
2. Which files: ask if the person has not said. A folder is searched through its subfolders.
3. Run — **Windows** (always `powershell`, the built-in Windows PowerShell, never `pwsh`;
   `-ExecutionPolicy Bypass` is for this run only and changes no setting; options before the paths):

   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File "4-SYSTEM/Skills/convert-audio/scripts/convert-audio-windows.ps1" "<file or folder>"
   powershell -NoProfile -ExecutionPolicy Bypass -File "4-SYSTEM/Skills/convert-audio/scripts/convert-audio-windows.ps1" -OutDir "<folder>" -Bitrate 128 "<file or folder>"
   ```

   **macOS**:

   ```
   bash "4-SYSTEM/Skills/convert-audio/scripts/convert-audio-mac.sh" "<file or folder>"
   bash "4-SYSTEM/Skills/convert-audio/scripts/convert-audio-mac.sh" -o "<folder>" -b 128 "<file or folder>"
   ```

   `-Force` / `-f` re-converts files that already have an .m4a. About 10 seconds per 25
   minutes of audio; a re-run skips what is done, so an interrupted run can be restarted.
4. Read the output: `OK` (length read back and equal to the source), `SKIP` (done before,
   or already compressed), `FAIL … length check failed` (the new file was removed — report
   it, do not retry other settings), `WARNING: still over the 50 MB`.
5. In a vault, if the notes describe the WAVs: the vault script
   `python 4-SYSTEM/scripts/audio_notes_to_m4a.py --write` points them at the .m4a
   (the WAV's details are kept under `converted_from:`).
6. Report in plain words: how many converted, name / size before → after, where the files
   are, every `FAIL` quoted with its meaning.

## Completion check

- [ ] The right script for the computer was used.
- [ ] Every `OK` line shows the converted length equal to the source.
- [ ] Originals untouched; the person reminded to keep them.
- [ ] Every `FAIL` reported.

The Mac script has not been run on a Mac yet: on the first run there, check one file's
`OK … length X s = source X s` line before converting a whole folder.
