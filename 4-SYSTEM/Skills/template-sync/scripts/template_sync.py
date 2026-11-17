#!/usr/bin/env python3
"""template-sync — bring rails-template updates into a vault made from it,
without losing the vault's own changes.

A vault made with "Use this template" shares no git history with the
template, so it never receives the template's later fixes. Copying the
template's files over would wipe out what the vault changed in its own copies
of the skills and scripts. This script does a THREE-WAY MERGE per file:

    base      the template file as it was when the vault was made / last synced
    template  the template file now
    vault     the vault's file now

    template unchanged since base       -> nothing to do
    vault unchanged since base          -> take the template version   (UPDATE)
    both changed, in different places   -> merge both                 (MERGE)
    both changed the same lines         -> conflict markers in the file (CONFLICT),
                                           resolved by the agent with the human
    template added a file               -> add it                      (ADD)
    template deleted an unchanged file  -> delete it                   (DELETE)
    anything else                       -> left alone and listed       (REVIEW)

Only paths that exist in the template are ever touched: a file that exists
only in the vault is never read or written. Vault-specific paths (the annex,
sources, rails, outputs, plugin data, `profile: vault-local` skills, …) are
excluded even when the template has them; a template change to an excluded
file is listed (EXCLUDED) so a person can adopt it by hand.

The base is the template commit recorded in `.rails-template-sync.json` at the
vault root after each sync. Before the first sync there is none: a vault made
with "Use this template" starts with a commit whose tree is identical to one
template commit, and that commit is the base. Otherwise pass --base.

Commands (run from anywhere inside the vault):

    python template_sync.py plan     fetch the template, classify every file,
                                     write a report; changes nothing in the vault
    python template_sync.py apply    carry out the plan: write ADD / UPDATE /
                                     MERGE / CONFLICT (with markers) / DELETE
    python template_sync.py finish   check that no conflict marker is left and
                                     that touched .py / .json files still parse,
                                     then record the new base

Options: --template URL-or-path (default: the URL in the marker file, else
WeBuddhist-Data/rails-template), --branch (default main), --base SHA (first
sync only, when the base cannot be found), --git PATH (git executable).
"""
import argparse
import datetime
import difflib
import fnmatch
import glob
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_TEMPLATE = "https://github.com/WeBuddhist-Data/rails-template.git"
MARKER = ".rails-template-sync.json"
WORKDIR = "0-INBOX/temp/template-sync"

# Vault-specific even though the template carries a copy (see
# 4-SYSTEM/How-to guides/Sync with rails-template.md, "What to always exclude").
EXCLUDE = [
    MARKER,
    "4-SYSTEM/Guidelines/vault-annex.md",
    "gemini-scribe/*",
    "4-SYSTEM/gemini-scribe/*",
    "4-SYSTEM/Pipelines/*",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".obsidian/workspace*.json",
    ".obsidian/plugins/*/data.json",
    "4-SYSTEM/scripts/*/output/*",
    "*/__pycache__/*",
    "*.pyc",
    ".env",
    "*/.env",
]
CONTENT_DIRS = ("0-INBOX/", "1-SOURCES/", "2-RAILS/", "3-TRANSFORMATIONS/")
# Only the labelled markers this script writes: a bare "=======" line is also a
# Markdown heading underline.
LABELS = ("vault (yours)", "template (before)", "template (now)")
CONFLICT_RE = re.compile(r"^(<<<<<<< vault \(yours\)|\|\|\|\|\|\|\| template \(before\)|>>>>>>> template \(now\))", re.M)


# --------------------------------------------------------------------------- git

def find_git(explicit):
    if explicit:
        return explicit
    found = shutil.which("git")
    if found:
        return found
    # GitHub Desktop ships its own git; many contributors have only that.
    local = os.environ.get("LOCALAPPDATA", "")
    hits = sorted(glob.glob(os.path.join(local, "GitHubDesktop", "app-*", "resources", "app", "git", "cmd", "git.exe")))
    if hits:
        return hits[-1]
    sys.exit("git not found: install Git, or pass --git <path to git>")


class Git:
    def __init__(self, exe, cwd):
        self.exe, self.cwd = exe, cwd

    def run(self, *args, check=True, input=None):
        r = subprocess.run([self.exe, *args], cwd=self.cwd, input=input,
                           capture_output=True)
        if check and r.returncode != 0:
            sys.exit(f"git {' '.join(args[:3])} … failed:\n{r.stderr.decode('utf-8', 'replace')}")
        return r

    def out(self, *args):
        return self.run(*args).stdout.decode("utf-8", "replace").strip()

    def blob(self, sha):
        return self.run("cat-file", "blob", sha).stdout

    def tree(self, commit):
        """{path: blob sha} for every file in a commit."""
        raw = self.run("ls-tree", "-r", "-z", commit).stdout.decode("utf-8", "replace")
        files = {}
        for entry in raw.split("\0"):
            if not entry:
                continue
            meta, path = entry.split("\t", 1)
            mode, kind, sha = meta.split()
            if kind == "blob":
                files[path] = sha
        return files


# --------------------------------------------------------------------------- helpers

def norm(data):
    """Content compared and merged with LF line endings, whatever the checkout uses."""
    return None if data is None else data.replace(b"\r\n", b"\n")


def is_binary(*datas):
    return any(d is not None and b"\0" in d[:8000] for d in datas)


def vault_local_skills(root):
    names = set()
    for skill_md in (root / "4-SYSTEM" / "Skills").glob("*/SKILL.md"):
        head = skill_md.read_text(encoding="utf-8", errors="replace").split("---")
        if len(head) > 2 and re.search(r"^profile:\s*vault-local\s*$", head[1], re.M):
            names.add(skill_md.parent.name)
    return names


def excluded(path, extra, local_skills):
    if path.startswith(CONTENT_DIRS):
        name = path.rsplit("/", 1)[-1]
        if not (name.startswith("About ") or name in ("_TEMPLATE.md", ".gitkeep")):
            return "vault content"
    if re.match(r"^([5-9]|\d{2,})-", path):
        return "numbered folder ≥ 5"
    m = re.match(r"^4-SYSTEM/Skills/([^/]+)/", path) or re.match(r"^\.claude/commands/([^/]+)\.md$", path)
    if m and m.group(1) in local_skills:
        return f"vault-local skill '{m.group(1)}'"
    for pat in EXCLUDE + list(extra):
        if fnmatch.fnmatch(path, pat) or path.startswith(pat.rstrip("*")) and pat.endswith("/*"):
            return f"excluded ({pat})"
    return None


def read_marker(root):
    p = root / MARKER
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def same_repo(a, b):
    clean = lambda u: re.sub(r"(\.git)?/?$", "", u.strip().lower().replace("\\", "/"))
    return clean(a) == clean(b)


# --------------------------------------------------------------------------- plan

def find_base(git, target, marker, explicit):
    if explicit:
        return git.out("rev-parse", explicit + "^{commit}"), "given with --base"
    if marker.get("synced_commit"):
        sha = marker["synced_commit"]
        if git.run("cat-file", "-e", sha + "^{commit}", check=False).returncode == 0:
            return sha, "recorded in " + MARKER
        sys.exit(f"the base {sha[:10]} recorded in {MARKER} is not in the fetched template history")
    roots = git.out("rev-list", "--max-parents=0", "HEAD").split()
    root_trees = {git.out("rev-parse", r + "^{tree}") for r in roots}
    history = [line.split() for line in git.out("log", "--format=%H %T", target).splitlines()]
    for commit, tree in history:
        if tree in root_trees:
            return commit, "the vault's first commit is identical to this template commit"
    # Not made with "Use this template": rank template commits by how many of
    # their files the vault's first commit had, byte for byte.
    first = git.tree(roots[-1])
    scored = []
    for commit, _ in history[:200]:
        files = git.tree(commit)
        same = sum(1 for p, s in files.items() if first.get(p) == s)
        scored.append((same / max(1, len(files)), commit))
    scored.sort(reverse=True)
    lines = "\n".join(f"  {c[:10]}  {s:.0%} of its files identical  "
                      f"{git.out('log', '-1', '--format=%cs %s', c)}" for s, c in scored[:3])
    sys.exit("No base found: this vault's first commit is not an exact copy of a template commit.\n"
             "Closest template commits:\n" + lines +
             "\nRe-run with --base <commit> once a person has confirmed which one the vault was copied from.")


def classify(git, root, base, target, extra):
    base_files, target_files = git.tree(base), git.tree(target)
    local_skills = vault_local_skills(root)
    rows = []
    for path in sorted(set(base_files) | set(target_files)):
        b_sha, t_sha = base_files.get(path), target_files.get(path)
        if b_sha == t_sha:
            continue                                   # template did not touch it
        why = excluded(path, extra, local_skills)
        if why:
            rows.append({"path": path, "action": "EXCLUDED", "why": why, "base": b_sha, "target": t_sha})
            continue
        f = root / path
        v = f.read_bytes() if f.is_file() else None
        b = git.blob(b_sha) if b_sha else None
        t = git.blob(t_sha) if t_sha else None
        nv, nb, nt = norm(v), norm(b), norm(t)
        row = {"path": path, "base": b_sha, "target": t_sha}
        if t is None:                                  # template deleted it
            if v is None:
                continue
            row.update(action="DELETE") if nv == nb else row.update(
                action="REVIEW", why="the template deleted this file, and your copy differs from the template's: kept")
        elif v is None:
            row.update(action="ADD") if b is None else row.update(
                action="REVIEW", why="you deleted this file, and the template changed it: left deleted")
        elif nv == nt:
            continue                                   # vault already has it
        elif b is not None and nv == nb:
            row.update(action="UPDATE")
        elif is_binary(v, b, t):
            row.update(action="REVIEW", why="binary file changed in the template and in the vault: kept yours")
        else:
            row["conflicts"] = merge(git, root, path, nv, nb or b"", nt)[1]
            row["action"] = "CONFLICT" if row["conflicts"] else "MERGE"
            if row["conflicts"]:
                refine(git, root, path, row, nv, nt, target)
        rows.append(row)
    return rows, local_skills


def history_blobs(git, rev, path):
    """Blob shas the path has had in the history of `rev`, newest first."""
    raw = git.run("log", "--format=", "--raw", "--no-abbrev", rev, "--", path).stdout.decode("utf-8", "replace")
    shas = []
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) >= 4 and line.startswith(":") and set(parts[3]) != {"0"} and parts[3] not in shas:
            shas.append(parts[3])
    return shas


def refine(git, root, path, row, nv, nt, target):
    """A conflict often means the global base is the wrong ancestor for this
    file: the template copied the file from this vault after the vault was made
    (so the global base has no copy, or an older one), or the vault copied a
    later template version by hand. Decide again from the file's own history,
    using only versions a side really had — never "the closest-looking" one,
    which would be the vault's or the template's current text itself:

      the template's current text is a PAST version of the vault's file
          -> AHEAD: the vault already has it and has moved on
      the vault's current text is a PAST version of the template's file
          -> UPDATE: the vault is only behind
      otherwise the newest text both histories contain is the base
          -> merge from it (kept only if it conflicts less)
    """
    t_hist = [s for s in history_blobs(git, target, path)]
    v_hist = [s for s in history_blobs(git, "HEAD", path)]
    content = {}
    for sha in t_hist + v_hist:
        content.setdefault(sha, norm(git.blob(sha)))
    t_past = [s for s in t_hist if content[s] != nt]       # template's earlier versions
    v_past = [s for s in v_hist if content[s] != nv]       # vault's earlier versions
    v_past_text = {content[s] for s in v_past}
    if nt in v_past_text:
        row.update(action="AHEAD", conflicts=0, why="the template's version is an earlier version of yours")
        return
    old = next((s for s in t_past if content[s] == nv), None)
    if old:
        row.update(action="UPDATE", base=old, conflicts=0, why="your copy is an earlier template version")
        return
    v_all_text = v_past_text | {nv}
    shared = next((s for s in t_hist if content[s] in v_all_text), None)   # newest first
    why = "merged from the last version both sides had"
    if not shared and v_past:
        # The template may have copied an earlier version of the vault's file
        # and edited it in the same commit, so no version is in both histories.
        # Take the vault's earlier version the template text matches best — but
        # only when it clearly matches, never for an unrelated file.
        lines = lambda b: b.decode("utf-8", "replace").splitlines()
        lt = lines(nt)
        score = {s: difflib.SequenceMatcher(None, lines(content[s]), lt, autojunk=False).ratio() for s in v_past}
        best = max(v_past, key=lambda s: score[s])
        if score[best] >= 0.6:
            shared = best
            why = (f"merged from your earlier version the template's copy matches ({score[best]:.0%} of lines): "
                   "check this file")
    if shared and shared != row["base"]:
        n = merge(git, root, path, nv, content[shared], nt)[1]
        if n < row["conflicts"]:
            row.update(base=shared, conflicts=n, action="CONFLICT" if n else "MERGE", why=why)


def merge(git, root, path, v, b, t):
    """Three-way merge with git merge-file. Returns (merged bytes, conflict count)."""
    tmp = root / WORKDIR / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    fv, fb, ft = tmp / "vault", tmp / "base", tmp / "template"
    fv.write_bytes(v), fb.write_bytes(b), ft.write_bytes(t)
    r = git.run("merge-file", "-p", "--diff3", "-L", LABELS[0], "-L", LABELS[1],
                "-L", LABELS[2], str(fv), str(fb), str(ft), check=False)
    if r.returncode >= 128:
        sys.exit(f"git merge-file failed on {path}: {r.stderr.decode('utf-8', 'replace')}")
    return r.stdout, r.returncode


def cmd_plan(git, root, args, marker):
    template = args.template or marker.get("template") or DEFAULT_TEMPLATE
    branch = args.branch or marker.get("branch") or "main"
    origin = git.run("remote", "get-url", "origin", check=False).stdout.decode().strip()
    if origin and same_repo(origin, template):
        sys.exit("This is the template repository itself: run template-sync in a vault made from it.")
    if git.out("status", "--porcelain", "--untracked-files=no"):
        print("WARNING: the vault has uncommitted changes. Commit them before `apply`.")
    print(f"Fetching {template} ({branch}) …")
    git.run("fetch", "--no-tags", "--quiet", template, branch)
    target = git.out("rev-parse", "FETCH_HEAD")
    base, how = find_base(git, target, marker, args.base)
    git.run("update-ref", "refs/template-sync/base", base)       # keep both reachable
    git.run("update-ref", "refs/template-sync/target", target)
    describe = lambda c: git.out("log", "-1", "--format=%h %cs %s", c)
    print(f"base    {describe(base)}   ({how})")
    print(f"target  {describe(target)}")
    if base == target:
        print("The vault is up to date with the template.")
        return
    rows, local_skills = classify(git, root, base, target, marker.get("exclude", []))
    plan = {"template": template, "branch": branch, "base": base, "target": target,
            "vault_head": git.out("rev-parse", "HEAD"), "rows": rows,
            "created": datetime.datetime.now().isoformat(timespec="seconds")}
    out = root / WORKDIR
    out.mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    report = render_report(git, plan, local_skills)
    (out / "report.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"\nPlan saved: {WORKDIR}/plan.json  ·  report: {WORKDIR}/report.md")


def render_report(git, plan, local_skills):
    groups = {}
    for r in plan["rows"]:
        groups.setdefault(r["action"], []).append(r)
    log = git.out("log", "--format=  %h %cs %s", f"{plan['base']}..{plan['target']}")
    lines = [f"# Template sync plan", "",
             f"Template commits since the last sync:", "", log or "  (none)", ""]
    meaning = {
        "ADD": "new in the template — will be added",
        "UPDATE": "you never changed these — will take the template version",
        "MERGE": "changed by both, in different places — both changes will be kept",
        "CONFLICT": "changed by both on the same lines — will need a decision",
        "DELETE": "removed from the template, never changed by you — will be deleted",
        "AHEAD": "the template's version came from this vault, which has moved on — nothing to bring in",
        "REVIEW": "left alone — a person should look",
        "EXCLUDED": "vault-specific, not synced — the template changed them; adopt by hand if useful",
    }
    for action in ("ADD", "UPDATE", "MERGE", "CONFLICT", "DELETE", "AHEAD", "REVIEW", "EXCLUDED"):
        rows = groups.get(action, [])
        if not rows:
            continue
        lines += [f"## {action} ({len(rows)}) — {meaning[action]}", ""]
        for r in rows:
            extra = f" — {r['conflicts']} conflict(s)" if action == "CONFLICT" else ""
            extra += f" — {r['why']}" if r.get("why") and action != "AHEAD" else ""
            lines.append(f"- `{r['path']}`{extra}")
        lines.append("")
    if local_skills:
        lines += ["Vault-local skills, never synced: " + ", ".join(sorted(local_skills)), ""]
    if not plan["rows"]:
        lines += ["The template's changes since the base touch no file this vault syncs.", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- apply / finish

def write_like(path, data, like):
    """Write with the line endings of the vault's existing copy (`like`)."""
    if like is not None and b"\r\n" in like:
        data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def load_plan(root):
    p = root / WORKDIR / "plan.json"
    if not p.exists():
        sys.exit("No plan: run `template_sync.py plan` first.")
    return json.loads(p.read_text(encoding="utf-8"))


def cmd_apply(git, root, args, marker):
    plan = load_plan(root)
    if git.out("rev-parse", "HEAD") != plan["vault_head"]:
        sys.exit("The vault has new commits since the plan was made: run `plan` again.")
    if git.out("status", "--porcelain", "--untracked-files=no"):
        sys.exit("The vault has uncommitted changes: commit or stash them, then run `apply`.")
    done = {}
    for r in plan["rows"]:
        a, f = r["action"], root / r["path"]
        if a in ("EXCLUDED", "REVIEW", "AHEAD"):
            continue
        v = f.read_bytes() if f.is_file() else None
        b = norm(git.blob(r["base"])) if r["base"] else None
        # Re-check the plan's verdict against the file as it is now: never
        # overwrite or delete a file that no longer matches the template's base.
        if a == "DELETE" and norm(v) != b:
            print(f"skipped DELETE, the file changed since the plan: {r['path']}")
            continue
        if v is None and a in ("UPDATE", "MERGE", "CONFLICT"):
            print(f"skipped {a}, the file was deleted since the plan: {r['path']}")
            continue
        if (a == "UPDATE" and norm(v) != b) or (a == "ADD" and v is not None):
            a = "MERGE"
        if a == "DELETE":
            f.unlink()
        elif a in ("ADD", "UPDATE"):
            write_like(f, git.blob(r["target"]), v)
        else:                                          # MERGE / CONFLICT
            b = b or b""
            merged, n = merge(git, root, r["path"], norm(v), b, norm(git.blob(r["target"])))
            write_like(f, merged, v)
            if n:
                keep = root / WORKDIR / "conflicts" / r["path"]
                keep.parent.mkdir(parents=True, exist_ok=True)
                for suffix, data in ((".vault", v), (".base", b), (".template", git.blob(r["target"]))):
                    keep.with_name(keep.name + suffix).write_bytes(data)
            a = "CONFLICT" if n else "MERGE"
        done.setdefault(a, []).append(r["path"])
    shutil.rmtree(root / WORKDIR / "tmp", ignore_errors=True)
    for a in ("ADD", "UPDATE", "MERGE", "DELETE", "CONFLICT"):
        if done.get(a):
            print(f"{a:9} {len(done[a])}")
    for p in done.get("CONFLICT", []):
        print(f"  resolve: {p}   (the three versions: {WORKDIR}/conflicts/{p}.vault|.base|.template)")
    print("\nNext: resolve every CONFLICT, then run `template_sync.py finish`." if done.get("CONFLICT")
          else "\nNext: review `git diff`, then run `template_sync.py finish`.")


def cmd_finish(git, root, args, marker):
    plan = load_plan(root)
    problems = []
    for r in plan["rows"]:
        f = root / r["path"]
        if r["action"] in ("EXCLUDED", "REVIEW", "DELETE", "AHEAD") or not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if r["action"] in ("MERGE", "CONFLICT") and CONFLICT_RE.search(text):
            problems.append(f"conflict markers left in {r['path']}")
        if f.suffix == ".py":
            try:
                compile(text, r["path"], "exec")       # syntax check only, writes nothing
            except SyntaxError as e:
                problems.append(f"{r['path']} no longer compiles: {e.msg} (line {e.lineno})")
        if f.suffix == ".json":
            try:
                json.loads(text)
            except ValueError as e:
                problems.append(f"{r['path']} is not valid JSON: {e}")
    if problems:
        sys.exit("Not finished:\n  " + "\n  ".join(problems))
    new_marker = {"template": plan["template"], "branch": plan["branch"],
                  "synced_commit": plan["target"],
                  "synced_at": datetime.date.today().isoformat(),
                  "exclude": marker.get("exclude", [])}
    (root / MARKER).write_text(json.dumps(new_marker, indent=2) + "\n", encoding="utf-8")
    report = (root / WORKDIR / "report.md").read_text(encoding="utf-8")
    shutil.rmtree(root / WORKDIR, ignore_errors=True)
    git.run("update-ref", "-d", "refs/template-sync/base", check=False)
    git.run("update-ref", "-d", "refs/template-sync/target", check=False)
    print(f"Recorded the new base {plan['target'][:10]} in {MARKER}.")
    print("Review `git diff`, then commit everything, including the marker file.\n")
    print(report)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("command", choices=["plan", "apply", "finish"])
    ap.add_argument("--vault", default=".", help="a folder inside the vault (default: current folder)")
    ap.add_argument("--template", help="template repository URL or local path")
    ap.add_argument("--branch", help="template branch (default main)")
    ap.add_argument("--base", help="first sync only: the template commit the vault was made from")
    ap.add_argument("--git", help="path to the git executable")
    args = ap.parse_args()
    exe = find_git(args.git)
    top = subprocess.run([exe, "rev-parse", "--show-toplevel"], cwd=args.vault,
                         capture_output=True, text=True)
    if top.returncode:
        sys.exit(f"{args.vault} is not inside a git repository")
    root = pathlib.Path(top.stdout.strip())
    git = Git(exe, root)
    marker = read_marker(root)
    {"plan": cmd_plan, "apply": cmd_apply, "finish": cmd_finish}[args.command](git, root, args, marker)


if __name__ == "__main__":
    main()
