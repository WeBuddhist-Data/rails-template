#!/usr/bin/env python3
"""STAGE 3 - Normalize blank-line spacing so exactly ONE blank line sits
immediately before AND immediately after every verse transclusion (or group
of transclusions on consecutive lines), wherever Stage 2 left it:

    <end of the previous segment>

    ![[link-base#^N-V]]

    <first line of the segment it transcludes into>

A group - transclusions on consecutive lines - stays on consecutive lines;
the blank lines go around the group, never inside it.

NEVER SPLITS A SEGMENT. A transclusion with text directly above AND directly
below it sits inside a segment (Stage 1 output not yet run through Stage 2,
or a LONG-SEGMENT that Stage 2 left in place). Adding blank lines there would
cut one segment in two, so it is left untouched and reported as MID-SEGMENT:
run Stage 2, or place it by hand at the start of its segment.

NOTE ON THE FILENAME: this script used to only add a blank line before a
sa-bcad block. It has been rewritten to normalize spacing on both sides of
every transclusion instead (the placement decision lives entirely in
Stage 2). The filename is kept for now so existing pipeline notes/commands
still work; rename it to 03_blank_around_transclusions.py next time you
have shell access to the vault if you want the name to match.

Multiple existing blank lines touching a transclusion are collapsed down to
exactly one; a missing blank is inserted. No text is touched, and no blank
line anywhere else in the file is affected. A transclusion at the very start
or very end of the file gets no leading/trailing blank (there is nothing on
that side to separate it from).

Idempotent: running this twice makes no further changes.

Usage:
  python3 03_blank_before_sachad.py --commentary <path>          # dry run
  python3 03_blank_before_sachad.py --commentary <path> --apply
"""
import re, sys, argparse
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def is_trans(line):
    return bool(line.strip().startswith('![[') and re.search(r'#\^([IVXLCDM]+|\d+)-(\d+)\]\]', line))

def is_text(line):
    """A line that belongs to a segment: not blank, not a heading, not a transclusion."""
    s = line.strip()
    return bool(s) and not re.match(r'#{1,}\s', s) and not s.startswith('![[')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--commentary', required=True)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    raw = open(a.commentary, 'rb').read().decode('utf-8', 'replace')
    eol = '\r\n' if '\r\n' in raw else '\n'   # written back with the same ending
    ls = raw.split(eol)
    n = len(ls)

    out = []
    added_before = added_after = collapsed = 0
    mid_segment = []
    i = 0
    while i < n:
        if not is_trans(ls[i]):
            out.append(ls[i])
            i += 1
            continue
        # the group: this transclusion and any directly following it
        g = i
        while g < n and is_trans(ls[g]):
            g += 1
        group = ls[i:g]
        if out and is_text(out[-1]) and g < n and is_text(ls[g]):
            mid_segment.append(i + 1)
            out.extend(group)
            i = g
            continue
        # --- spacing before ---
        if out:
            if out[-1].strip() != '':
                out.append('')
                added_before += 1
            else:
                while len(out) >= 2 and out[-2].strip() == '':
                    out.pop()
                    collapsed += 1
                if len(out) == 1 and out[0].strip() == '':
                    out.pop()          # leading blank at the very top of the file
                    collapsed += 1
        out.extend(group)
        # --- spacing after ---
        j = g
        blanks_seen = 0
        while j < n and ls[j].strip() == '':
            blanks_seen += 1
            j += 1
        if j < n:
            out.append('')
            if blanks_seen == 0:
                added_after += 1
            elif blanks_seen > 1:
                collapsed += blanks_seen - 1
        else:
            out.extend(ls[g:j])        # keep the file's trailing blank lines as they were
        i = j

    print("blank lines added before: %d   added after: %d   collapsed: %d   mid-segment (left alone): %d" %
          (added_before, added_after, collapsed, len(mid_segment)))
    for ln in mid_segment[:20]:
        print("  MID-SEGMENT transclusion at line %d: run Stage 2, or move it to the start of its segment by hand" % ln)
    if len(mid_segment) > 20:
        print("  ... and %d more" % (len(mid_segment) - 20))
    if a.apply:
        open(a.commentary, 'w', encoding='utf-8', newline='').write(eol.join(out))
        open(a.commentary, encoding='utf-8').read()  # validate decode
        print("APPLIED")

if __name__ == '__main__':
    main()
