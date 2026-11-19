# Upstream

| | |
|---|---|
| Source repository | https://github.com/WeBuddhist-Data/pali-chanting-text |
| Path | `4-SYSTEM/scripts/uploader-root-text/` |
| Pinned commit | `e3d1c41` (2026-11-10, "Stop uploader writing ids.json sidecars") |
| Copied | 2026-11-16 |

`upload.py` and `README.md` are copied byte-identical. Every later commit here is a local delta.

**Why vendored:** it is the third step after `linter-root-text` and `parser-root-text`. It takes a parser output folder (`parser-root-text/output/<stem>/`) and posts text → edition → TOC, plus the alignment for a translation, to the library API. It writes the returned `text_id` / `edition_id` / `toc_id` into the source `.md` frontmatter, which is the only record it keeps.

**Not specific to pali-chanting-text.** The file names in the README examples and the `--help` epilog (`तिसरण–पञ्चशील_hi`) come from that vault. The code only assumes the standard layout: `1-SOURCES/` at the vault root, and the parser output in `4-SYSTEM/scripts/parser-root-text/output/`.

**Superseded by `Skills/library-upload`** (2026-11-19), which builds payloads with the same shared `scripts/` linter and parser, keeps dev and prod apart, shows a plan before sending, patches in place instead of re-creating, and never deletes a text. (Before that, `Skills/root-text-upload` and `Skills/translation-upload` covered the same calls with their own copies of the linter and parser.) This uploader is the plain script-level version, kept for reference: it sends calls unless you pass `--dry-run`, and its `--recreate` deletes and re-creates texts — do not use it on published texts.

## Local changes

None yet.
