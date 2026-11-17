---
name: template-sync
description: Bring the latest rails-template updates (skills, scripts, guidelines, how-to guides, CLAUDE.md, catalog, Obsidian plugins) into a vault made from it, merging each change into the vault's own version instead of overwriting it, so the vault's customisations survive. Use when someone says "update from the template", "sync with rails-template", "get the latest skills", "pull template updates", "our vault is behind the template".
profile: rails-vault
---

# template-sync

A vault made from `rails-template` shares no git history with it, so the template's later fixes never reach the vault on their own. Copying the template's files over would erase what the vault changed in its own copies of the skills and scripts. This skill does a **three-way merge** per file — the template file as it was when the vault was made or last synced (*base*), the template file now (*template*), and the vault's file now (*vault*) — so each template improvement lands **inside** the vault's version. Correct output: every template change applied, every vault customisation still there, every real contradiction decided by a person, and the new base recorded so the next sync starts from here.

The script `scripts/template_sync.py` does all the mechanical work. The agent's job is the judgment the script cannot do: resolving conflicts, and explaining the plan and the result to the person in plain words.

---

## Inputs

| Input | What it is | Default |
|---|---|---|
| **Vault** | The vault to update: run from inside it. | the current folder |
| **Template** | The template repository, as a URL or a local path. | the URL in `.rails-template-sync.json`, else `https://github.com/WeBuddhist-Data/rails-template.git` |
| **Branch** | The template branch to sync from. | `main` |
| **Base** *(first sync only, rarely)* | The template commit the vault was made from, when the script cannot find it (the vault was copied by hand, not made with "Use this template"). Ask the person; never pick one yourself. | found automatically |

Needs git (the script also finds GitHub Desktop's copy on Windows) and access to the template repository.

## Output

- The vault's files updated in place, on a branch, uncommitted until the person approves.
- `.rails-template-sync.json` at the vault root, recording the template commit now merged in.
- While working: `0-INBOX/temp/template-sync/` (plan, report, the three versions of each conflicted file). `finish` deletes it.

---

## Output file format

`.rails-template-sync.json`:

```json
{
  "template": "https://github.com/WeBuddhist-Data/rails-template.git",
  "branch": "main",
  "synced_commit": "<full sha of the template commit merged in>",
  "synced_at": "2026-11-17",
  "exclude": []
}
```

`exclude` holds extra glob patterns (e.g. `"4-SYSTEM/Skills/format-commentary/*"`) for files this vault has taken over completely and never wants updated. The person adds them; the agent only suggests.

The plan report (`0-INBOX/temp/template-sync/report.md`) lists the template commits since the last sync, then every affected file under one action:

| Action | Meaning | What `apply` does |
|---|---|---|
| `ADD` | new in the template | adds it |
| `UPDATE` | the vault never changed it | takes the template version |
| `MERGE` | both changed it, in different places | writes the merge of both |
| `CONFLICT` | both changed the same lines | writes the merge with conflict markers, for the agent to resolve |
| `DELETE` | removed from the template, never changed in the vault | deletes it |
| `AHEAD` | the template's version is an earlier version of the vault's own file (the template copied it from this vault) | nothing: the vault already has it and more |
| `REVIEW` | deleted on one side and changed on the other, or a binary file changed on both | nothing; a person decides |
| `EXCLUDED` | vault-specific (the annex, sources, rails, plugin data, `vault-local` skills, …) and changed in the template | nothing; listed so a person can adopt the change by hand |

---

**When the vault-wide base is the wrong ancestor for a file**, the script decides that file again from its own history. This happens to a file the template copied *from* this vault after the vault was made, or one the vault copied from the template by hand. It uses only versions a side really had:

- the template's text is a past version of the vault's file → `AHEAD`
- the vault's text is a past version of the template's file → `UPDATE`
- otherwise it merges from the newest version both histories contain. If there is none, it uses the vault's earlier version that the template's text clearly matches (at least 60% of lines). Those merges are marked *"check this file"* in the report.

## Rules

1. **Never replace a vault file with the template's version when the vault changed it.** Only `UPDATE` (vault unchanged since base) takes the template file whole. Everything the vault changed is merged.
2. **Only template paths are touched.** A file that exists only in the vault is never read or written. Skills marked `profile: vault-local`, `4-SYSTEM/Guidelines/vault-annex.md`, `0-INBOX/`–`3-TRANSFORMATIONS/` content, `4-SYSTEM/Pipelines/`, plugin `data.json`, `.claude/settings*.json` and the script `output/` folders are excluded, as listed in [`Sync with rails-template`](../../How-to%20guides/Sync%20with%20rails-template.md).
3. **Resolve a conflict by keeping both intentions.** The vault's change (vault vs base) is a customisation to keep; the template's change (template vs base) is an improvement to adopt. Write the version that does both. Never settle a conflict by taking one side whole.
4. **A real contradiction goes to the person.** When the two changes cannot both hold — they set the same value differently, or one removes what the other edits — stop and ask, in plain words, with both versions shown. Never decide it silently.
5. **Placeholders stay filled.** Where the template changed a line holding `[text-slug]` or `[name of text]` and the vault had filled it in, keep the vault's name and take the template's other wording.
6. **Work on a branch, and commit nothing before the person has seen the result.**
7. **Never run in the template repository itself.** The script refuses.
8. **Never edit the base by hand, and never pass `--base` without the person confirming the commit.** A wrong base turns template changes into "vault changes" and back.
9. **The marker is written only by `finish`**, after every conflict is resolved and every touched `.py` and `.json` file still parses.
10. **A fix to a generic skill belongs upstream.** If resolving a conflict shows a vault customisation every vault would want, say so: it should go into the template (and the shared skill library), not stay a local patch.

---

## Procedure

### 0. If this vault does not have this skill yet

Vaults made before this skill existed get it from the template once. From the vault root:

```bash
git fetch https://github.com/WeBuddhist-Data/rails-template.git main
```

```bash
git show FETCH_HEAD:4-SYSTEM/Skills/template-sync/scripts/template_sync.py > 0-INBOX/temp/template_sync.py
```

Then run `python 0-INBOX/temp/template_sync.py plan` in step 2 instead of the installed path. The sync itself adds the skill to the vault (it is a template file). Delete the temporary copy afterwards.

### 1. Start clean, on a branch

1. `git status`: everything committed. If not, ask the person to commit or set the changes aside first.
2. Create a branch: `git switch -c template-sync-<YYYY-MM-DD>`.

### 2. Plan

```bash
python 4-SYSTEM/Skills/template-sync/scripts/template_sync.py plan
```

It fetches the template, finds the base, classifies every file, and writes `0-INBOX/temp/template-sync/report.md`. Nothing in the vault changes.

- *"up to date"* → tell the person and stop.
- *"No base found"* → show the person the closest template commits it lists, and ask which one the vault was made from. Re-run with `--base <commit>` only on their answer.

### 3. Explain the plan to the person

Summarise the report in plain words: what is new in the template (from the commit list), how many files are added, updated, merged; **each `CONFLICT` file and what both sides changed there**; each `REVIEW` and `EXCLUDED` file and why it is left alone. Ask before going on.

### 4. Apply

```bash
python 4-SYSTEM/Skills/template-sync/scripts/template_sync.py apply
```

It writes every `ADD`, `UPDATE`, `MERGE` and `DELETE`, and writes each `CONFLICT` file with labelled markers (`<<<<<<< vault (yours)`, `||||||| template (before)`, `>>>>>>> template (now)`). The three whole versions of each conflicted file are in `0-INBOX/temp/template-sync/conflicts/<path>.vault|.base|.template`.

### 5. Resolve each conflict

For each `CONFLICT` file:

a. Read `.base`, `.vault` and `.template`. Work out **what the vault changed** (base → vault) and **what the template changed** (base → template), as intentions, not lines.
b. Write the file so it carries both (rule 3), removing every marker. Keep the vault's wording where it customised; bring in the template's new rules, steps, fixes and sections.
c. If they contradict (rule 4), ask the person, showing the two versions side by side.
d. Show the person the result for that file (`git diff <path>`) and a one-line account: "kept your …, added the template's …".

Then read every `MERGE` the report marks *"check this file"*: it was merged from a base the script inferred. Confirm with `git diff <path>` that nothing of the vault's was lost and the template's change is in; fix it by hand if not.

### 6. Handle REVIEW and EXCLUDED

- `REVIEW`: tell the person what happened on each side and offer the choices (e.g. "the template deleted `x`; you had changed it — keep yours, or delete it?"). Do what they choose.
- `EXCLUDED`: tell the person what the template changed in that file (`git diff <base> <target> -- <path>`, using the commits in the report) and whether they may want to copy it by hand — most often the annex template gaining a new section.

### 7. Finish

```bash
python 4-SYSTEM/Skills/template-sync/scripts/template_sync.py finish
```

It refuses while a conflict marker remains or a touched `.py` / `.json` file no longer parses; fix what it names and run it again. On success it records the new base in `.rails-template-sync.json` and prints the report.

### 8. Hand over

1. Run `vault-audit` if the template added skills: every skill must have its catalog entry and `.claude/commands/` stub (both come from the template, so normally they do).
2. Show the person the full `git diff --stat` and the list of conflicts resolved.
3. On their approval, commit everything — including `.rails-template-sync.json` — with a message naming the template commit, push the branch, and open a pull request (or merge it, as the vault's practice is).

---

## Completion check

- [ ] Started from a clean tree, on a `template-sync-<date>` branch
- [ ] The person saw the plan before `apply`
- [ ] Every `CONFLICT` resolved keeping both sides' intentions; contradictions decided by the person
- [ ] Every `MERGE` marked *"check this file"* read and confirmed
- [ ] Every `REVIEW` item decided by the person; every `EXCLUDED` change reported
- [ ] `finish` succeeded: no markers left, `.py` and `.json` files parse, `.rails-template-sync.json` updated
- [ ] No vault-only file, no excluded file, no `vault-local` skill touched
- [ ] The person approved the diff before the commit
