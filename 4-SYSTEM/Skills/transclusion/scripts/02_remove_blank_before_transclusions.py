#!/usr/bin/env python3
"""STAGE 2 - Move each verse transclusion to the START OF A SEGMENT: right
before the verse's OWN sa-bcad (ས་བཅད) segment(s) when the verse has them,
otherwise right before the segment that holds the verse's quotation.

A transclusion never sits inside a segment. A segment is a run of
consecutive non-blank lines ended by a blank line or a heading (block IDs sit
at its end). Stage 1 puts each transclusion on the line right before the
quoted stanza, which can be inside a segment (e.g. a segment that opens with
"དང་པོ་ནི།" and then quotes the verse); this stage lifts it to the first line
of that segment, and further up when sa-bcad segments sit directly above.

NOTE ON THE FILENAME: this script used to just delete the blank line above a
transclusion. It has been rewritten to reposition the transclusion itself.
The filename is kept for now so existing pipeline notes/commands still work;
rename it to 02_reposition_before_sachad.py next time you have shell access
to the vault if you want the name to match the new behaviour.

THE WALK, SEGMENT BY SEGMENT
----------------------------
Starting from the segment that holds the transclusion, look at the segment
directly above it (blank lines skipped). It is STRUCTURAL when every one of
its lines is structural (below); keep walking up through structural
segments. Stop at the first segment that is not, or at a heading, a
transclusion, or the start of the file. The transclusion then goes to the
start of the TOPMOST walked segment that holds an opener (ordinal, heading
ending ནི།, enumeration opener): leading member-only segments are trimmed,
exactly as member-only lines used to be. If no walked segment holds an
opener, the transclusion goes to the start of its own segment.

A line is classified with its trailing block ID removed (every segment of a
segmented commentary ends in one; without stripping it, no ending test
matched and most sa-bcad were missed):
  - an ordinal-led line (དང་པོ, གཉིས་པ, གསུམ་པ, ... བཅུ་པ) - 'open', but ONLY
    when it is heading-anchored or does not itself read as a conclusion (see
    the "ordinal-priority" note below);
  - a heading ending ནི། / ནི། །  (short, <= 60 collapsed syllables) - 'open';
  - an enumeration opener ending ལ། / ལ་ཡང་། / ལས། / ཏེ། / སྟེ།  (short) - 'open';
  - an enumeration member/closer ending དང་། / a closing member
    (…པའོ།/…བའོ།/…ནོ།/…ལོ།) / a count word  (short) - 'mem'.

Ordinary commentary prose, connectors (དེའི་རྗེས་སུ།, དེའི་འཐད་པར།,
དེའི་འཐད་པ་ནི།), quotation/commentary conclusions (containing ཞེས/ཅེས),
root-verse-line fragments (ending དང་། །  or  དང་ནི། །) and markdown headings
are NOT structural and stop the walk.

ORDINAL-PRIORITY, AND WHY IT REQUIRES A HEADING ANCHOR
------------------------------------------------------
An ordinal-led block is usually a sa-bcad announcement even when it folds its
own extended explanation into the same paragraph (e.g. "བཞི་པ་...ནི། <several
sentences> ཞེས་པའི་དོན་ནོ།"), so trailing ཞེས/ཅེས text should not by itself
mask an ordinal opener at the front of a block. BUT a real placement bug
(caught by a human reviewer against the ^5-49 / ^5-50 pair, then confirmed
against several more instances in the same file - ^9-79, ^9-110, ^9-154)
showed that an ordinal word at the front of a paragraph is NOT always a fresh
sa-bcad for the verse that follows. Two recurring false-positive shapes:

  1. A commentary announces a flat numbered list once in prose ("there are
     27 gateways for faults... first: X, second: Y...") and then walks
     through the list's items one by one across several verses' worth of
     exposition, sometimes packing several list items into ONE verse's
     gloss. Every item still starts a fresh paragraph with its ordinal word,
     but most of them are explaining a WORD OR CLAUSE of the verse that was
     JUST quoted, not introducing the verse that comes next.
  2. An opponent's objection is elaborated with its own internal step
     numbering ("...so they say: second, ... third, and so on") - again
     ordinal-led, again not a sa-bcad for what follows. (^9-110.)

The one structural feature that reliably distinguishes a GENUINE sa-bcad
resumption from these false positives is a true markdown heading (any #...#
line ending in a block ID like ^1-2-3-...-0) sitting a short distance above
the ordinal line. So: an ordinal-led line is trusted unconditionally only
when such a heading is found within the last few blocks above it. Without a
heading anchor, an ordinal-led line that itself contains a ཞེས/ཅེས
conclusion falls back to the plain conclusion test and is treated as 'none'
- the walk stops, which is always the safe default. A missed sa-bcad
placement (verse quoted a few lines later than ideal) is a much smaller
error than a WRONG one (root verse displaced across another verse's own
commentary material). Skim the --report output for chapters with heavy
enumeration/debate prose and hand-place any genuine sa-bcad the heuristic
was too conservative about.

LONG SEGMENTS
-------------
A file that is not segmented (few or no blank lines) is one enormous
"segment", and lifting a transclusion to its start would move it hundreds of
lines. When the start of the transclusion's own segment is more than
--max-segment-lines above it, the transclusion is LEFT WHERE IT IS and
reported as LONG-SEGMENT: segment the commentary first, or place it by hand.
Stage 3 leaves such a mid-segment transclusion alone too.

Only ![[...]] lines are ever moved. No commentary text is added, removed,
reordered, or rephrased, and no blank lines are touched here - spacing is
Stage 3's job (03_blank_before_sachad.py).

Idempotent: a transclusion already at the start of a segment is walked from
that segment, and the walk ends where it ended the first time (the segment
above it is either not structural, or holds no opener).

Usage:
  python3 02_remove_blank_before_transclusions.py --commentary <path> [--chapter N|all] --report   # dry run
  python3 02_remove_blank_before_transclusions.py --commentary <path> [--chapter N|all] --apply
"""
import re, sys, argparse
sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # Tibetan in the report on any console

ORD =['དང་པོ','གཉིས་པ','གསུམ་པ','བཞི་པ','ལྔ་པ','དྲུག་པ','བདུན་པ','བརྒྱད་པ','དགུ་པ','བཅུ་པ']
CONNECTORS = ['དེའི་རྗེས་སུ།','དེའི་འཐད་པར།','དེའི་འཐད་པ་ནི།']

HEAD_END = ('ནི།','ནི། །','ནི།།')
OPEN_END = ('ལ།','ལ་ཡང་།','ལ་ཡང༌།','ལས།','ཏེ།','སྟེ།')
MEM_END  = ('དང་།','དང༌།','དང་། །',
            'པའོ། །','པའོ།།','བའོ། །','བའོ།།',
            'ནོ། །','ནོ།།','ལོ། །','ལོ།།',
            'གཅིག།','གཉིས།','གསུམ།','བཞི།','ལྔ།','དྲུག།','བདུན།','བརྒྱད།','དགུ།','བཅུ།',
            'གསུམ་ལས།','གཉིས་ལས།','ཡོན།')

TRAILING_ID_RE = re.compile(r'\s*\^[\w-]+\s*$')
TRANS_RE = re.compile(r'#\^([IVXLCDM]+|\d+)-(\d+)\]\]')

def clen(s):
    return len(s.replace('་','').replace('།','').replace(' ','').replace('༎','').strip())
def starts_ord(s): return any(s.startswith(o) for o in ORD)
def ends_any(s, group): return any(s.endswith(x) for x in group)
def has_zhes(s): return 'ཞེས' in s or 'ཅེས' in s

def is_blank(line): return line.strip() == ''
def is_trans_line(line): return line.strip().startswith('![[')
def is_md_heading(line): return bool(re.match(r'^\s*#{1,}\s', line))
def is_breaker(line): return is_blank(line) or is_md_heading(line)

def is_heading(line):
    """True markdown heading line (#... **text** ^...-0). A heading never
    counts as sa-bcad prose itself, but one sitting a short distance above an
    ordinal-led line is the strongest available signal that the line is a
    genuine sa-bcad resuming that heading's topic. See ORDINAL-PRIORITY."""
    s = line.strip()
    return bool(re.match(r'^#{1,12}\s', s)) and bool(re.search(r'-0\s*$', s))

def prev_nonblank(ls, idx):
    """Index of the nearest non-blank line before idx, or -1 if none."""
    p = idx - 1
    while p >= 0 and ls[p].strip() == '':
        p -= 1
    return p

def heading_anchor_nearby(ls, idx, steps=3):
    """True if a true markdown heading sits within the last `steps` non-blank
    lines above idx. A transclusion line breaks the search (a heading is
    meaningful context only while nothing else has been transcluded since)."""
    q = prev_nonblank(ls, idx)
    for _ in range(steps):
        if q < 0:
            return False
        if is_heading(ls[q]):
            return True
        if ls[q].strip().startswith('!['):
            return False
        q = prev_nonblank(ls, q)
    return False

def kind(ls, idx):
    """'open' (opener: heading-phrase/opener/ordinal), 'mem' (member), or
    'none', for the line at ls[idx], read without its trailing block ID."""
    raw = ls[idx]
    if not raw.strip() or is_trans_line(raw) or is_md_heading(raw):
        return 'none'
    s = TRAILING_ID_RE.sub('', raw.strip()).strip()
    if not s or s in CONNECTORS: return 'none'
    if starts_ord(s):
        # Ordinal-priority, gated by a heading anchor - see the docstring.
        if heading_anchor_nearby(ls, idx) or not has_zhes(s):
            return 'open'
    if has_zhes(s): return 'none'        # quotation / conclusion
    if s.endswith('དང་། །') or s.endswith('དང་ནི། །'): return 'none'  # verse fragment
    L = clen(s)
    if ends_any(s, HEAD_END) and L <= 60: return 'open'
    if ends_any(s, OPEN_END) and L <= 60: return 'open'
    if ends_any(s, MEM_END)  and L <= 60: return 'mem'
    return 'none'

def segment_top(ls, i):
    """First line of the segment holding line i. Transclusion lines inside a
    segment (Stage 1 leaves them there) do not end it."""
    j = i
    while j - 1 >= 0 and not is_breaker(ls[j - 1]):
        j -= 1
    return j

def segment_above(ls, top):
    """(start, end) of the segment directly above the one starting at `top`,
    blank lines skipped; None at a heading or the start of the file."""
    p = top - 1
    while p >= 0 and is_blank(ls[p]):
        p -= 1
    if p < 0 or is_md_heading(ls[p]):
        return None
    end = p
    while p - 1 >= 0 and not is_breaker(ls[p - 1]):
        p -= 1
    return p, end

def find_target(ls, i):
    """Where the transclusion at line i belongs: (index, why). The index is
    always the first line of a segment."""
    top = segment_top(ls, i)
    run = []          # walked structural segments, nearest first: (start, has_open)
    cur = top
    while True:
        seg = segment_above(ls, cur)
        if seg is None:
            break
        s, e = seg
        if any(is_trans_line(ls[k]) for k in range(s, e + 1)):
            break     # another verse's transclusion: never walk past it
        kinds = [kind(ls, k) for k in range(s, e + 1)]
        if 'none' in kinds:
            break
        run.append((s, 'open' in kinds))
        cur = s
    for s, has_open in reversed(run):   # topmost first: trim leading members
        if has_open:
            return s, 'sa-bcad'
    return top, 'segment'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--commentary', required=True)
    ap.add_argument('--chapter', default='all')
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--max-segment-lines', type=int, default=12,
                    help='leave a transclusion in place (and report it) when the start of '
                         'its own segment is more than this many lines above it (default 12)')
    a = ap.parse_args()

    raw = open(a.commentary, 'rb').read().decode('utf-8', 'replace')
    eol = '\r\n' if '\r\n' in raw else '\n'   # written back with the same ending
    ls = raw.split(eol)

    trans = []  # (original index, vid)
    for i, l in enumerate(ls):
        m = TRANS_RE.search(l)
        if is_trans_line(l) and m:
            if a.chapter != 'all' and m.group(1) != str(a.chapter): continue
            trans.append((i, "%s-%s" % (m.group(1), m.group(2))))

    targets = {}   # original transclusion index -> (index to insert before, why)
    pending = {}   # target index -> [transclusion line text, ...], in original order
    for i, vid in trans:
        if i - segment_top(ls, i) > a.max_segment_lines:
            t, why = i, 'long-segment'
        else:
            t, why = find_target(ls, i)
        # a transclusion already directly above its target segment, or one in a
        # run of transclusions directly above it, stays put
        if why != 'long-segment' and all(is_trans_line(ls[k]) for k in range(t, i)):
            t, why = i, 'in-place'
        targets[i] = (t, why)
        pending.setdefault(t, []).append(ls[i])

    counts = {}
    for t, why in targets.values():
        counts[why] = counts.get(why, 0) + 1
    print("transclusions=%d  before-sachad=%d  to-segment-start=%d  already-placed=%d  long-segment=%d" %
          (len(trans), counts.get('sa-bcad', 0), counts.get('segment', 0),
           counts.get('in-place', 0), counts.get('long-segment', 0)))
    if a.report:
        for i, vid in trans:
            t, why = targets[i]
            if why == 'in-place':
                print("  ^%-7s already at a segment start (line %d)" % (vid, i + 1))
            elif why == 'long-segment':
                print("  ^%-7s LONG-SEGMENT: left at line %d, %d lines below its segment start "
                      "(segment the file, or place by hand)" % (vid, i + 1, i - segment_top(ls, i)))
            elif why == 'sa-bcad':
                print("  ^%-7s moves before sa-bcad '%s...' (line %d -> %d)" %
                      (vid, ls[t].strip()[:30], i + 1, t + 1))
            else:
                print("  ^%-7s moves to its segment start '%s...' (line %d -> %d)" %
                      (vid, ls[t].strip()[:30], i + 1, t + 1))

    if a.apply and trans:
        trans_idx = {i for i, _ in trans}
        out = []
        for idx in range(len(ls)):
            if idx in pending:
                out.extend(pending[idx])
            if idx not in trans_idx:
                out.append(ls[idx])
        open(a.commentary, 'w', encoding='utf-8', newline='').write(eol.join(out))
        open(a.commentary, encoding='utf-8').read()  # validate decode
        print("APPLIED")

if __name__ == '__main__':
    main()
