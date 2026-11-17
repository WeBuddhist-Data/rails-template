# Start a vault and format its texts

This guide has two parts:

1. **[Make your own vault](#part-1--make-your-own-vault-from-rails-template)** from `rails-template`, clone it, and make it yours.
2. **[Bring a text into the vault](#part-2--bring-a-text-into-the-vault)**: turn a raw file into the format the linter and parser read, check it, and upload it. It includes [example requests to copy](#how-to-ask-the-ai), and [how to describe your own file's structure](#if-your-file-has-its-own-structure-describe-it-in-the-prompt) to the AI.

Part 2 describes the format the way the tools actually read it. Every rule below comes from `4-SYSTEM/scripts/linter-*` and `parser-*`, and the example files in [§2.7](#27-a-complete-example) pass both.

---

## Part 1 — Make your own vault from rails-template

One vault holds one text: its root text, its commentaries and translations, and everything built from them. Name it after the text: `<text-slug>-rails`, e.g. `bodhisattvacharyavatara-rails`.

### 1.1 Create the repository on GitHub

1. Open [github.com/WeBuddhist-Data/rails-template](https://github.com/WeBuddhist-Data/rails-template).
2. Click **Use this template → Create a new repository**.
3. Owner: `WeBuddhist-Data` (or your own account). Name: `<text-slug>-rails`. Choose Private or Public. Leave **Include all branches** off.
4. Click **Create repository**.

Or from a terminal, with [GitHub CLI](https://cli.github.com/):

```bash
gh repo create WeBuddhist-Data/<text-slug>-rails --private --template WeBuddhist-Data/rails-template
```

> **No "Use this template" button?** The repository is not marked as a template. An admin turns it on under **Settings → General → Template repository**.

A repository made from a template starts with one fresh commit and no shared history: changes in `rails-template` do not reach it by themselves. See [1.5](#15-later-pull-template-updates).

### 1.2 Clone it

If Git, GitHub CLI and Obsidian are not installed yet, follow [Set up the vault](Set%20up%20the%20vault.md) §1–3 first. Then, in the folder where the vault should live:

```bash
git clone https://github.com/WeBuddhist-Data/<text-slug>-rails.git
```

Open the new folder in Obsidian (**Open folder as vault**) and click **Trust author & enable plugins** ([Set up the vault](Set%20up%20the%20vault.md) §5–6).

### 1.3 Install the tools' Python packages

The linter and parser need Python 3.8+ and three packages:

```bash
pip install -r 4-SYSTEM/scripts/linter-root-text/requirements.txt
```

### 1.4 Make it yours

Do this once, in the first commit of the new vault.

1. **Replace the placeholders** `[text-slug]` and `[name of text]` in:
   - `README.md` (and delete its "Using this template" note)
   - `4-SYSTEM/CLAUDE.md`
   - `4-SYSTEM/Guidelines/vault-annex.md`
   - `4-SYSTEM/Guidelines/0-VAULT-Structure.md`
   - `4-SYSTEM/gemini-scribe/AGENTS.md`

   To find them all (the copies inside `4-SYSTEM/Skills/` are examples; leave them):

   ```bash
   git grep -nF -e "[text-slug]" -e "[name of text]" -- . ":!4-SYSTEM/Skills"
   ```

2. **Fill in `4-SYSTEM/Guidelines/vault-annex.md`**: the addressing scheme (`verse_id_format`), the registered commentary IDs, the language tracks, and the filename convention if you use native-script or catalog-code names (see [`1-SOURCES/About Sources.md`](../../1-SOURCES/About%20Sources.md), *Naming rules*).
3. Commit and push:

   ```bash
   git add -A
   ```

   ```bash
   git commit -m "Set up <text-slug>-rails from rails-template"
   ```

   ```bash
   git push
   ```

### 1.5 Later: pull template updates

When `rails-template` gains a new skill or a fixed script, ask the AI for it:

```text
/template-sync
Bring this vault up to date with rails-template. Explain the plan to me before
changing anything, and keep every change we made to our own skills and scripts.
```

The `template-sync` skill does not copy the template's files over yours. It works out what the template changed and what you changed in each file, and keeps both. You decide anything that genuinely clashes, and you see the full result before it is committed. It never touches your texts, rails, outputs, vault annex, or skills marked `vault-local`. The lists of what is synced and what never is are in [Sync with rails-template](Sync%20with%20rails-template.md).

---

## Part 2 — Bring a text into the vault

### 2.1 The path of a file

```
received file ──► 0-INBOX/            raw, as received; never cited
                    │  intake + format skills
                    ▼
                  1-SOURCES/<folder>/   formatted: frontmatter, headings, block IDs
                    │  linter  →  parser
                    ▼
                  output/<stem>/*.json  API payloads
                    │  upload skill
                    ▼
                  library API           text_id / edition_id / toc_id written back
```

Put the received file in `0-INBOX/raw-data/` first, and never edit it there: it is your untouched original. The skills read it there and write the formatted file into `1-SOURCES/`:

| Folder | What goes in it |
|---|---|
| `1-SOURCES/Text/` | root texts |
| `1-SOURCES/Commentaries/` | commentaries |
| `1-SOURCES/Translations/` | existing human translations |
| `1-SOURCES/References/` | dictionaries, secondary literature |

Name files the way [`About Sources.md`](../../1-SOURCES/About%20Sources.md) says: lowercase, hyphenated, no diacritics, with a language tag (`-bo`, `-sk`, `-pi`, `-en`, …), unless the vault annex declares native-script or catalog-code names.

### 2.2 Convert it: which skill for which file

You do not run these skills yourself: you ask the AI to, in plain words (see [How to ask the AI](#how-to-ask-the-ai) below). The tables tell you which skill to name. Each skill's `SKILL.md` in `4-SYSTEM/Skills/` says exactly what it does.

**First, get it into Markdown:**

| You have | Skill |
|---|---|
| An EPUB | `epub-to-markdown` |
| A JSON export of a root text | `json-to-source-text` |
| A JSON export of a commentary | `json-to-commentary` |
| A plain-text, OCR or segmentation file | `raw-to-sources` (first `tibetan-ocr-quality` for a Tibetan scan; `clean-raw-text` for page numbers, running headers and stray spacing) |
| A Word file (`.docx`) | Save it as plain text (UTF-8), then `raw-to-sources` |
| A corpus already segmented and aligned by people (OpenPecha download, Google-Docs alignment) | `aligned-corpus-intake` |
| A translation with the root lines inline | `bilingual-to-transclusion` |

**Then give it structure** (headings, blocks, block IDs):

| Text | Skill |
|---|---|
| Tibetan root text | `root-text-pipeline` (all steps), or `format-tibetan-root-text` |
| Sanskrit root text | `format-sanskrit-root-text` |
| Any other root text | `format-root-text` |
| Tibetan commentary | `commentary-pipeline` (all steps: segment, sa bcad tree, headings, block IDs) |
| Any other commentary | `format-commentary` |
| Frontmatter of any file | `frontmatter` |
| Commentary → root text links | `transclusion`, **Mode 5** when the commentary will be uploaded |

The skills produce the format below. Read it anyway: you check their output, and you fix by hand what they could not decide.

#### How to ask the AI

**Where to type.** Open the vault folder in Claude Code — the **Code** tab of the Claude desktop app, or type `claude` in a terminal opened in the vault folder — and type your request in the chat box. The AI reads the vault's rules (`CLAUDE.md`) by itself.

**Two ways to call a skill.** Type `/` and the skill's name, then your request in plain words. Or just name it in a sentence. Both work the same:

```text
/frontmatter 1-SOURCES/Text/sgrol-ma-bstod-pa-bo.md
```

```text
Please use the frontmatter skill on 1-SOURCES/Text/sgrol-ma-bstod-pa-bo.md
```

**What a good request says.** You do not need technical words. Tell the AI:

1. **Which file** — its path in the vault, e.g. `1-SOURCES/Text/<file>.md` (in Obsidian: right-click the file → **Copy path** → the path from the vault folder).
2. **What it is** — root text, commentary or translation; its language; for a commentary, which root text it explains.
3. **What you already know** — title, author, where the text came from (a link). The AI must not guess these, so give them or let it leave them empty.
4. **What you want back** — "show me first", "only chapter 1", "explain in simple words".

**Example requests** — copy one and change the parts in `<…>`:

*Not sure where to start:*

```text
I put a file in 0-INBOX/raw-data/<file name>. It is a Tibetan commentary on
1-SOURCES/Text/<root text>.md. Which skills do I need, in what order?
Don't change anything yet.
```

*Bring a raw text into the vault:*

```text
/raw-to-sources 0-INBOX/raw-data/<file name>
This is a root text (type: root). Title: <title>. Author: <author>.
Source: <link>. Keep every word as it is.
```

*Structure a Tibetan commentary, one step at a time:*

```text
/commentary-pipeline 1-SOURCES/Commentaries/<file>.md
Stop after each step and tell me what you did, so I can check it.
```

*Link a commentary to its root text for upload:*

```text
/transclusion 1-SOURCES/Commentaries/<file>.md with root 1-SOURCES/Text/<root>.md.
It will be uploaded, so use Mode 5. Show me the mapping before writing anything.
```

*Check a file:*

```text
Run the linter on 1-SOURCES/Text/<file>.md and explain each error in simple
words. Don't fix anything yet.
```

…then, after reading the answer: `Fix errors 1 and 3. Leave error 2: the heading is correct.`

*Upload (a test run first):*

```text
/root-text-upload 1-SOURCES/Text/<file>.md — dry run only.
```

**Tips**

- **One file at a time**, and ask for a preview ("show me first", "only the first chapter") before a big change.
- **When something is wrong, say exactly what**: not "the headings are wrong" but "`ཞལ་གྱི་ཡོན་ཏན།` should be under `སྐུའི་ཡོན་ཏན།`, one level deeper".
- **Ask it to undo** if a change went badly: "Undo your last change to this file."
- **Ask it to explain** anything you do not understand: "What does this error mean, in simple words?"
- **Never let it guess** a title, author, date or link: "If you can't find it in the text, leave it empty."

#### If your file has its own structure: describe it in the prompt

Many files already show their structure, just not in Markdown: chapter lines that start with a word, numbered sections, an empty line before each new part. The AI cannot know your file's habits. **Describe them the way you would explain the file to a new colleague**, and it will use your structure instead of guessing one.

Say four things:

1. **Each kind of line, and how to recognise it** — the title, each heading level, verses, prose, anything to remove. Recognise by what the line starts with, its numbering, a symbol, bold, indentation, or what comes before or after it.
2. **Which vault level each one becomes.** The title is always `#`, so **your first heading level is `##`**, the next `###`, and so on.
3. **What must not change** — every word; and anything that looks like noise but is structure (e.g. "keep the numbers at the start of heading lines").
4. **What to do when unsure** — "if you can't tell whether a line is a heading, list it for me instead of guessing."

**Example.** A commentary saved as plain text, `0-INBOX/raw-data/tara-commentary.txt` (the `←` notes are only for this guide):

```text
སྒྲོལ་མ་ཉེར་གཅིག་ལ་བསྟོད་པའི་འགྲེལ་པ།                ← the title

ལེའུ་དང་པོ། བསྟོད་པ་དངོས།                             ← a chapter
༡ མདོར་བསྟན་པ།                                        ← the chapter's list of its sections
༢ རྒྱས་པར་བཤད་པ།
༣ མཇུག་བསྡུ་བ།

༡ མདོར་བསྟན་པ།                                        ← a section really starts here
༡.༡ ཕྱག་འཚལ་བའི་དོན།                                  ← a sub-section
ཕྱག་འཚལ་ཞེས་པ་ནི་གུས་པས་འདུད་པའོ། །                     ← commentary text
ཕྱག་འཚལ་སྒྲོལ་མ་མྱུར་མ་དཔའ་མོ། །                         ← a quoted verse, 4 lines
སྤྱན་ནི་སྐད་ཅིག་གློག་དང་འདྲ་མ། །
འཇིག་རྟེན་གསུམ་མགོན་ཆུ་སྐྱེས་ཞལ་གྱི། །
གེ་སར་ཕྱེ་བ་ལས་ནི་བྱུང་མ། །
```

The prompt:

```text
Please bring 0-INBOX/raw-data/tara-commentary.txt into the vault with the
raw-to-sources skill, then format it with format-commentary.

It is a Tibetan commentary (type: commentary) on 1-SOURCES/Text/sgrol-ma-bstod-pa-bo.md.
Source: https://webuddhist.com/. Leave the author empty.

The file is plain text. Its structure:
- Line 1 is the title of the work.
- A line starting with "ལེའུ་" is a chapter.
- A line starting with one Tibetan number and a space (༡ , ༢ …) is a section.
- A line starting with two numbers joined by a dot (༡.༡ , ༢.༣ …) is a sub-section.
- Right after each chapter line comes a list of that chapter's sections. That
  list is text, not headings: put it on one line as one paragraph. A section
  really starts where its line appears again, after an empty line.
- A group of 4 lines that each end in "། །" is a quoted verse: keep the 4 lines
  together as one block.
- Every other line is commentary text, one paragraph per line.

Make it the vault format:
- title = #, chapter = ##, section = ###, sub-section = ####.
- Give the title ^0. Heading IDs follow the numbering: chapter 1 = ^1-0,
  section 1 = ^1-1-0, sub-section 1.1 = ^1-1-1-0.
- Text blocks count on from the chapter: ^1-1, ^1-2, … in chapter 1.
- A blank line before and after every heading and every block.
- Keep every word, and keep the numbers at the start of heading lines.
- If you can't tell what a line is, list it for me instead of guessing.

Do chapter 1 first and show it to me before you do the rest.
```

What chapter 1 should come back as (this passes the linter):

```markdown
# སྒྲོལ་མ་ཉེར་གཅིག་ལ་བསྟོད་པའི་འགྲེལ་པ། ^0

## ལེའུ་དང་པོ། བསྟོད་པ་དངོས། ^1-0

༡ མདོར་བསྟན་པ། ༢ རྒྱས་པར་བཤད་པ། ༣ མཇུག་བསྡུ་བ། ^1-1

### ༡ མདོར་བསྟན་པ། ^1-1-0

#### ༡.༡ ཕྱག་འཚལ་བའི་དོན། ^1-1-1-0

ཕྱག་འཚལ་ཞེས་པ་ནི་གུས་པས་འདུད་པའོ། ། ^1-2

ཕྱག་འཚལ་སྒྲོལ་མ་མྱུར་མ་དཔའ་མོ། །
སྤྱན་ནི་སྐད་ཅིག་གློག་དང་འདྲ་མ། །
འཇིག་རྟེན་གསུམ་མགོན་ཆུ་སྐྱེས་ཞལ་གྱི། །
གེ་སར་ཕྱེ་བ་ལས་ནི་བྱུང་མ། ། ^1-3
```

**Ways to describe a line** — pick whatever is true of your file:

| Your file marks it with | Say it like this |
|---|---|
| A word at the start | "A line starting with `ལེའུ་` is a chapter." |
| Numbering | "`1.` is a section, `1.1` a sub-section, `1.1.1` one level deeper." / "`(ཀ)`, `(ཁ)` … are sub-sections." |
| A symbol | "A line starting with `*` is a section heading; remove the `*`." |
| Bold, capitals, indentation | "Lines in bold are headings." / "A line indented by two spaces is a quoted verse." |
| Its place | "The first line after an empty line is a section heading." |
| Its ending | "A short line ending in `ནི།` on its own is a heading." |
| A pattern of lines | "Four lines that each end in `། །` are one verse." |
| Noise to drop | "Lines like `- 12 -` are page numbers: remove them." |

**Paste two or three real lines for each kind**, as in the example: the AI learns your file from them much better than from a description alone. If your file has no visible structure at all, say so: for a Tibetan text, the `root-text-pipeline` and `commentary-pipeline` skills work out the structure themselves, and you check it after.

### 2.3 How the linter and parser read a file

Both tools read a file the same way:

1. The **YAML frontmatter** between the two `---` lines.
2. The **body**, cut into **blocks** at blank lines. A block is one or more lines with no blank line between them.
3. Footnote definitions (`[^d1]: …`) are taken out first, wherever they are.

Then each block is one of three things:

| Block | Starts with | Becomes |
|---|---|---|
| **Heading** | `#` | a node of the table of contents (TOC) — never text |
| **Transclusion** | `![[…#^…]]` only | an alignment link to the root text — never text |
| **Content** | anything else | one segment of the edition text |

Every heading and every content block **ends with a block ID**: a space, then `^` and the ID, at the end of its last line (`… ^1-1`).

> ⚠️ **A heading is a block of its own: a blank line before and after it.** Text on the line under a heading would drop out of the edition, and a heading glued under text, or above a transclusion or another heading, would drop out of the TOC. The linter rejects all of these: `a heading must be a block of its own`.

### 2.4 Frontmatter

What the linter requires before a file can be uploaded. Leave a field empty rather than guess it.

| Field | Root text | Commentary | Translation | Notes |
|---|:-:|:-:|:-:|---|
| `file_type` | `root-text` | `commentary` | `translation` | |
| `title` | ✔ | ✔ | ✔ | in the file's own language and script (Pali: Roman script) |
| `language` / `lang_tag` | ✔ | ✔ | ✔ | at least one; e.g. `Tibetan` / `bo` |
| `category_id` | ✔ | copied from root | copied from root | the API category |
| `license` | ✔ | ✔ | ✔ | `public`, `cc0`, `cc-by`, …, `copyrighted`, `unknown` |
| `source` | ✔ | ✔ | ✔ | an `http(s)://` URL |
| `root_text` | — | ✔ | ✔ | full path, e.g. `1-SOURCES/Text/<file>.md` |
| `author` / `translator` | | | | optional (warning if missing). `Name [bdrc:P1234]` or `Name [op:ID]`; a name without an ID is skipped |
| `edition_type` | | | | `critical` (default), `diplomatic` or `collated` |
| `alt_titles` | | | | optional; a list of `lang: "title"` items, any language — see below |

**Alternative titles** — one item per title, each keyed by its language code, so the language is never guessed:

```yaml
alt_titles:
  - bo: "ཕྱག་འཚལ་ཉེར་གཅིག"
  - en: "Praise to the Twenty-One Tārās"
```

Every key must be a language code the API knows (`bo`, `en`, `sa`, `zh`, …; not `bod` or `english`), and a Pali (`pi`) title must be in Roman script. A bare string (`- ཕྱག་འཚལ་ཉེར་གཅིག`) is still accepted and keyed with the file's own `lang_tag`, but write the keyed form.

> ⚠️ **An alt title in another language becomes a title of this text in that language.** The library keeps titles unique per language, so `en: "Praise to the Twenty-One Tārās"` on the Tibetan root claims that English title: an English translation uploaded later with the same title is refused (HTTP 422 "title … already exists"), and an uploaded alt title cannot be removed. Give another-language alt titles only when no translation will carry that title. `commentary-upload` refuses them on a commentary.

Never fill these by hand: `commentary_of` / `translation_of` (the linter takes them from the root's `text_id`), and `text_id` / `edition_id` / `toc_id` (the upload writes them). Upload the root text first, so its `text_id` exists. The full schema is in [`4-SYSTEM/Templates/FILE_YAML_PROPERTIES.md`](../Templates/FILE_YAML_PROPERTIES.md).

### 2.5 The heading hierarchy (TOC)

The number of `#` is the heading's depth in the table of contents, and it equals **the number of parts in its block ID**:

| Level | Markdown | Block ID | Example |
|---|---|---|---|
| 1 | `#` | `^0` | `# སྒྲོལ་མ་ཉེར་གཅིག་ལ་བསྟོད་པ། ^0` |
| 2 | `##` | `^1-0` | `## ལེའུ་དང་པོ། ^1-0` |
| 3 | `###` | `^1-2-0` | `### རྒྱས་པར་བཤད་པ། ^1-2-0` |
| 4 | `####` | `^1-2-1-0` | `#### སྐུའི་ཡོན་ཏན། ^1-2-1-0` |
| 5 | `#####` | `^1-2-1-1-0` | `##### ཞལ་གྱི་ཡོན་ཏན། ^1-2-1-1-0` |
| 6 | `######` | `^1-2-1-1-1-0` | `###### སྤྱན་གྱི་ཡོན་ཏན། ^1-2-1-1-1-0` |
| 7 | `#######` + `**bold**` | `^1-2-1-1-1-1-0` | `####### **གློག་གི་དཔེ།** ^1-2-1-1-1-1-0` |
| 8+ | one more `#` per level, `**bold**` | full path + `-0` | `######## **དཔེ་དོན་སྦྱར་བ།** ^1-2-1-1-1-1-1-0` |

**The linter rejects the file when:**

- the first heading is not `#`;
- a heading has no block ID (the `#` title too: give it `^0`);
- a level is skipped going down (`###` straight after `#`). Going back up by any number of levels is fine;
- two headings share an ID.

**Convention** (not checked, but every skill writes it and the vault relies on it):

- One `#` per file: the title, first.
- A heading ID is the node's full path in the tree plus a final `-0`: `1.2.1` → `^1-2-1-0`. There is no depth limit; never shorten a deep tree.
- From level 7 on, wrap the title in `**…**`. Obsidian displays only six heading levels, so a seven-`#` line shows as plain text and the bold keeps it visible; the **Deep headings** plugin adds fold arrows. The parser drops the `**` from the TOC title.
- Front matter (homage, title in Sanskrit, translator's preface) goes under `## … ^I-0` with blocks `^I-1`, `^I-2`, …; back matter (colophon) under `^a-0` with `^a-1`, … — only when the vault annex registers these zones.
- In a commentary, the `##` IDs are chosen **by a person**, to key each section to the root text's structure; everything under them is derived ([`annotation-conventions.md`](../Guidelines/annotation-conventions.md) §3).

**What the parser does with headings:** they are left out of the text. Each one becomes a TOC node, nested by its `#` count. Its span runs from the text after it to the next heading of the same or a higher level. A heading with no text under it (straight followed by a sub-heading) gets an empty span.

### 2.6 Content blocks

**IDs.** At most **three parts**: `^1-1`, `^I-3`, `^a-1`, `^1-2-3`. `^1-2-1-1` is an error. IDs must be unique.

- **Root text:** `^chapter-verse`, the verse number restarting in each chapter (`^1-1 … ^1-58`, then `^2-1 …`); before chapter 1, `^0-N` (or `^I-N` front matter). Sanskrit uses the four-zone scheme ([`annotation-conventions.md`](../Guidelines/annotation-conventions.md) §1b).
- **Commentary:** a counter off its `##` label that does **not** restart at `###` and deeper: under `## … ^1-0`, the blocks are `^1-1, ^1-2, ^1-3, …` whatever sub-headings come between.

**Verse or paragraph — decided by the block's shape first, then its ID:**

| The block is | The parser makes it |
|---|---|
| two or more lines with no blank line between them | `verse` (one line per pāda) |
| one line | the file's default: `verse` in a root text, `paragraph` in a commentary |
| an ID starting with `T` / `t` | `top_segment` |
| an ID with an uppercase Roman part (`^I-1`) | `front_matter` (unless it is verse) |
| an ID with a lowercase part (`^a-1`) | `back_matter` (unless it is verse) |

So:

- **A stanza** keeps its lines together, the ID on its last line.
- **A prose paragraph stays on one line.** Hard-wrapped prose is read as verse.
- **A blank line inside a stanza** splits it into two blocks, and the first then has no ID: an error.

**Transclusions** (commentaries and translations) link a block to the root text:

```markdown
![[1-SOURCES/Text/sgrol-ma-bstod-pa-bo.md#^1-1]]

དང་པོ་ལ་གཉིས། མདོར་བསྟན་པ་དང་། རྒྱས་པར་བཤད་པའོ། ། ^1-1
```

- Full vault-relative path with `.md`, on its own line, one blank line before and after. Several verses: consecutive lines, no blank between them.
- Before a whole block, never inside one; after a heading, never before one.
- **Every heading ends the link.** A transclusion covers the blocks after it up to the next transclusion or the next heading, so repeat it after each heading whose text explains that verse (the `transclusion` skill, Mode 5, does this).
- A translation has the shape: transclusion of the root block, blank line, the translated block ending in the **same** ID.

**Inline marks:**

- **Yigchung** (small-script gloss): `<small>…</small>`, opened and closed inside the same block.
- **Durchen** (variant reading): a marker right after the word, `…བསྟན་པའོ།[^d1] །`, and at the end of the file `[^d1]: པའོ། ༼སྣར།༽ པ་ཡིན་ནོ།` — lemma, witness sigla in `༼…༽`, variant.
- **Footnote** (editorial note): `[^f1]` and `[^f1]: …`. At the end of the file the `d` definitions come first, then the `f` ones.
- No markers in headings. Every marker needs exactly one definition.

**Characters.** Plain spaces and plain line breaks only: no non-breaking or zero-width spaces (the linter warns about them).

### 2.7 A complete example

**Root text** — `1-SOURCES/Text/sgrol-ma-bstod-pa-bo.md`:

```markdown
---
title: སྒྲོལ་མ་ཉེར་གཅིག་ལ་བསྟོད་པ།
alt_titles:
  - bo: "ཕྱག་འཚལ་ཉེར་གཅིག"
  - en: "Praise to the Twenty-One Tārās"
author:
language: Tibetan
lang_tag: bo
file_type: root-text
verse_id_format: chapter-verse
category_id: REBGnT4qFooPfPEkR5pe5
license: public
source: https://webuddhist.com/
edition_type: critical
source_description: "Example file for the format guide"
---

# སྒྲོལ་མ་ཉེར་གཅིག་ལ་བསྟོད་པ། ^0

## ཀླད་ཀྱི་དོན། ^I-0

༄༅། །རྒྱ་གར་སྐད་དུ། ཨཱརྱ་ཏཱ་རཱ་སྟོ་ཏྲ། ^I-1

## ལེའུ་དང་པོ། ^1-0

ཕྱག་འཚལ་སྒྲོལ་མ་མྱུར་མ་དཔའ་མོ། །
སྤྱན་ནི་སྐད་ཅིག་གློག་དང་འདྲ་མ། །
འཇིག་རྟེན་གསུམ་མགོན་ཆུ་སྐྱེས་ཞལ་གྱི། །
གེ་སར་ཕྱེ་བ་ལས་ནི་བྱུང་མ། ། ^1-1

ཕྱག་འཚལ་སྟོན་ཀའི་ཟླ་བ་ཀུན་ཏུ། །
གང་བ་བརྒྱ་ནི་བརྩེགས་པའི་ཞལ་མ། །
སྐར་མ་སྟོང་ཕྲག་ཚོགས་པ་རྣམས་ཀྱིས། །
རབ་ཏུ་ཕྱེ་བའི་འོད་རབ་འབར་མ། ། ^1-2
```

**Commentary** — `1-SOURCES/Commentaries/sgrol-ma-bstod-pa-grel-pa-bo.md`, with headings eight levels deep:

```markdown
---
title: སྒྲོལ་མ་ཉེར་གཅིག་ལ་བསྟོད་པའི་འགྲེལ་པ།
author:
language: Tibetan
lang_tag: bo
file_type: commentary
root_text: 1-SOURCES/Text/sgrol-ma-bstod-pa-bo.md
category_id: REBGnT4qFooPfPEkR5pe5
license: public
source: https://webuddhist.com/
edition_type: critical
---

# སྒྲོལ་མ་ཉེར་གཅིག་ལ་བསྟོད་པའི་འགྲེལ་པ། ^0

## དང་པོ་བསྟོད་པ་དངོས། ^1-0

![[1-SOURCES/Text/sgrol-ma-bstod-pa-bo.md#^1-1]]

དང་པོ་ལ་གཉིས། མདོར་བསྟན་པ་དང་། རྒྱས་པར་བཤད་པའོ། ། ^1-1

### མདོར་བསྟན་པ། ^1-1-0

![[1-SOURCES/Text/sgrol-ma-bstod-pa-bo.md#^1-1]]

ཕྱག་འཚལ་ཞེས་པ་ནི་གུས་པས་འདུད་པའོ། ། ^1-2

### རྒྱས་པར་བཤད་པ། ^1-2-0

#### སྐུའི་ཡོན་ཏན། ^1-2-1-0

##### ཞལ་གྱི་ཡོན་ཏན། ^1-2-1-1-0

###### སྤྱན་གྱི་ཡོན་ཏན། ^1-2-1-1-1-0

![[1-SOURCES/Text/sgrol-ma-bstod-pa-bo.md#^1-1]]

སྤྱན་ནི་སྐད་ཅིག་གློག་དང་འདྲ་མ་ཞེས་པ་ནི་མྱུར་བའི་དཔེའོ། ། ^1-3

####### **གློག་གི་དཔེ།** ^1-2-1-1-1-1-0

![[1-SOURCES/Text/sgrol-ma-bstod-pa-bo.md#^1-1]]

གློག་ནི་སྐད་ཅིག་ཙམ་གྱིས་འབྱུང་བའོ། ། ^1-4

######## **དཔེ་དོན་སྦྱར་བ།** ^1-2-1-1-1-1-1-0

![[1-SOURCES/Text/sgrol-ma-bstod-pa-bo.md#^1-1]]

དེ་བཞིན་དུ་སྒྲོལ་མས་སེམས་ཅན་མྱུར་དུ་སྐྱོབ་པའོ། ། ^1-5

## གཉིས་པ་ཟླ་བའི་ཞལ། ^2-0

![[1-SOURCES/Text/sgrol-ma-bstod-pa-bo.md#^1-2]]

ཕྱག་འཚལ་སྟོན་ཀའི་ཟླ་བ་ཀུན་ཏུ། །
གང་བ་བརྒྱ་ནི་བརྩེགས་པའི་ཞལ་མ། ། ^2-1

ཞེས་པ་ནི་ཞལ་གྱི་མཛེས་པ་བསྟན་པའོ།[^d1] ། ^2-2

[^d1]: པའོ། ༼སྣར།༽ པ་ཡིན་ནོ།
```

What the parser makes of the commentary:

- **TOC:** 10 nodes, nested 8 levels deep under the title. The `**` is gone from the level-7 and level-8 titles.
- **Edition:** 7 segments. `^2-1` is `verse` (two lines with no blank between them); the rest are `paragraph`. No heading text is in the content.
- **Alignment:** `^1-1 … ^1-5` → root `^1-1`, and `^2-1`, `^2-2` → root `^1-2`. Each of the blocks under the deeper headings is aligned because its heading is followed by its own transclusion.
- **Durchen:** one, spanning `པའོ།` just before the marker.

### 2.8 Check it: lint, then parse

Run from the vault root (the folder holding `1-SOURCES/` and `4-SYSTEM/`). **Commit first:** the linter edits the file's frontmatter in place (it normalises `language` and `lang_tag`, and fills `commentary_of` / `category_id` in a commentary).

Root text (and translations):

```bash
python 4-SYSTEM/scripts/linter-root-text/lint_text_input.py "1-SOURCES/Text/<file>.md"
```

```bash
python 4-SYSTEM/scripts/parser-root-text/parser.py "1-SOURCES/Text/<file>.md" "4-SYSTEM/scripts/linter-root-text/output/<file>.lint.json"
```

Commentary:

```bash
python 4-SYSTEM/scripts/linter-commentary/lint_text_input.py "1-SOURCES/Commentaries/<file>.md"
```

```bash
python 4-SYSTEM/scripts/parser-commentary/parser.py "1-SOURCES/Commentaries/<file>.md" "4-SYSTEM/scripts/linter-commentary/output/<file>.lint.json"
```

`OK` means the file passed; `FAIL` writes `output/<file>.lint.errors.json` and lists each error. `WARN` lines do not stop the upload but say what is missing. The parser writes the payloads to `4-SYSTEM/scripts/parser-*/output/<file>/`: `text`, `edition`, `toc`, `durchens`, and for a commentary or translation `alignment`.

**Reading the errors:**

| Linter message | What is wrong | Fix |
|---|---|---|
| `header 1: missing reference (^n-n-n-…)` and `toc: header missing reference marker: '…'` | a heading has no ID — usually the `#` title | `# Title ^0` |
| `header ^1-0: a heading must be a block of its own — '…' is on the line after it with no blank line between …` | text, a transclusion or another heading glued to a heading | add the blank line the message names |
| `toc: first header must be level 1 (#)` | the file does not start with the `#` title | add it before the first `##` |
| `toc: heading level skip at ^1-0: h3 after h1 (max allowed: h2)` | a level is skipped | one `#` more than the parent heading |
| `segment 3: missing reference (^n-n-n (max 3 parts))` | a block has no ID — often a stanza cut in two by a blank line | add the ID, or remove the blank line |
| `segment 4: reference '^1-2-1-1' has 4 parts; verses allow at most ^n-n-n (3 parts)` | a heading-style ID on a text block | content IDs have at most 3 parts |
| `segment 6: duplicate reference '^1-3'` | two blocks share an ID | renumber |
| `source: required` / `value must be a URL` | no `source`, or not a link | `source: https://…` |
| `root_text …: no text_id found to set commentary_of` (WARN) | the root is not uploaded yet | upload the root text first |

### 2.9 Upload

Upload with the skills, which lint, parse, show a dry run, and upload only after you confirm:

| File | Skill |
|---|---|
| Root text — **always first** | `root-text-upload` |
| Commentary | `commentary-upload` |
| Translation | `translation-upload` |
| Yigchung marks of an uploaded text | `yigchung-upload` |

They need the API key in the environment (`WEBUDDHIST_API_KEY`, kept in a git-ignored `4-SYSTEM/scripts/.env`, never committed). After the upload, the file's frontmatter carries its `text_id`, `edition_id` and `toc_id`: commit them.

---

## See also

- [`annotation-conventions.md`](../Guidelines/annotation-conventions.md) — the full block-ID specification; it wins over every other document.
- [`About Sources.md`](../../1-SOURCES/About%20Sources.md) — what may and may not be done to a file in `1-SOURCES/`.
- The tools' own READMEs: [`linter-root-text`](../scripts/linter-root-text/README.md), [`linter-commentary`](../scripts/linter-commentary/README.md), [`parser-root-text`](../scripts/parser-root-text/README.md), [`parser-commentary`](../scripts/parser-commentary/README.md).
- [`SKILLS-CATALOG.md`](../Skills/SKILLS-CATALOG.md) — every skill, in pipeline order.
