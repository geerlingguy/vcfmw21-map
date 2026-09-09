#!/usr/bin/env python3
"""Parse the VCF Midwest talk schedule grid into talks.json.

Source: https://vcfmw.org/talkschedule  (saved locally as talks_grid.htm)
Output: talks.json, consumed by index.html

The page is a GravCMS dump whose only interesting part is a single
<table class="table table-bordered table-dark"> holding a time-by-room grid.
Only the standard library is used: the shape is known and regular, and the
validation pass below is what actually guards against the page changing.

    python tools/parse_talks.py                    # talks_grid.htm -> talks.json
    python tools/parse_talks.py --fetch            # refresh the local copy first
    python tools/parse_talks.py --check            # parse and report, write nothing
    python tools/parse_talks.py --inline index.html
"""

import argparse
import datetime as dt
import html
import json
import re
import sys
import urllib.request

# ---------------------------------------------------------------- constants

SOURCE_URL = "https://vcfmw.org/talkschedule"
EVENT_NAME = "VCF Midwest 21"
TIMEZONE = "America/Chicago"

# The grid names only "Saturday" and "Sunday"; the calendar dates live here.
# CDT is UTC-5, asserted against the real DST window in check_dst() below.
UTC_OFFSET_HOURS = -5
DAYS = {
    "Saturday": {"date": "2026-09-12", "hours": "9:00 AM – 8:00 PM"},
    "Sunday": {"date": "2026-09-13", "hours": "9:00 AM – 3:00 PM"},
}

TABLE_ANCHOR = '<table class="table table-bordered table-dark'
INLINE_BEGIN = "<!-- talks:begin -->"
INLINE_END = "<!-- talks:end -->"

# A talk in the last slot of a room has no following start to measure against.
DEFAULT_LAST_MIN = 45
MAX_DERIVED_MIN = 60

TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*([AP]M)$", re.I)
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday")


class ParseError(Exception):
    """A structural problem that means the output would be wrong."""


# ------------------------------------------------------------------ helpers

def text(fragment):
    """Visible text of an HTML fragment, whitespace collapsed."""
    fragment = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def attr(attrs, name):
    """One attribute value from a raw attribute string, or None.

    Handles both quote styles: two of the abstracts use single quotes because
    they contain a double quote.  Anchored so a name appearing inside another
    attribute's value cannot match.
    """
    m = re.search(
        r"(?:^|\s)" + name + r"\s*=\s*(\"([^\"]*)\"|'([^']*)')", attrs, re.I
    )
    if not m:
        return None
    return html.unescape(m.group(2) if m.group(2) is not None else m.group(3))


def prose(value):
    """Tidy a title= attribute without touching its wording.

    No tag stripping: these attributes are plain prose (verified - not one
    contains a '<'), so a tag stripper could only eat real text.  Paragraph
    breaks are preserved because the popover renders them.
    """
    if not value:
        return ""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = "\n".join(line.rstrip() for line in value.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", value).strip()


BARE_DOMAIN_RE = re.compile(
    r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+([/?#].*)?$",
    re.I,
)


def clean_url(href):
    """Normalise an href, or return '' if it is not a usable URL.

    Several hrefs in the source are not links at all - a sentence, a bare
    hostname, a parenthetical.  A bad URL in the .ics can make a client reject
    the whole event, so anything doubtful is dropped rather than guessed at.
    """
    if not href:
        return ""
    href = href.strip()
    if not href or re.search(r"\s|%20", href):
        return ""
    if href.startswith(("http://", "https://")):
        return href
    if href.startswith("//"):
        return "https:" + href
    if BARE_DOMAIN_RE.match(href):
        return "https://" + href
    return ""


def to_minutes(stamp):
    m = TIME_RE.match(stamp)
    if not m:
        raise ParseError("unparseable time %r" % stamp)
    hour, minute, half = int(m.group(1)), int(m.group(2)), m.group(3).upper()
    if not 1 <= hour <= 12 or minute >= 60:
        raise ParseError("out-of-range time %r" % stamp)
    return (hour % 12 + (12 if half == "PM" else 0)) * 60 + minute


def check_dst():
    """CDT is only UTC-5 inside the DST window; make a wrong year fail loudly."""
    for name, info in DAYS.items():
        date = dt.date.fromisoformat(info["date"])
        march = dt.date(date.year, 3, 8)
        start = march + dt.timedelta(days=(6 - march.weekday()) % 7)   # 2nd Sun
        nov = dt.date(date.year, 11, 1)
        end = nov + dt.timedelta(days=(6 - nov.weekday()) % 7)         # 1st Sun
        if not start <= date < end:
            raise ParseError(
                "%s (%s) is outside US DST; UTC_OFFSET_HOURS=%d is wrong"
                % (name, info["date"], UTC_OFFSET_HOURS)
            )
        if date.strftime("%A") != name:
            raise ParseError(
                "%s is a %s, not a %s" % (info["date"], date.strftime("%A"), name)
            )


# ------------------------------------------------------------------- parsing

def slice_table(raw):
    start = raw.find(TABLE_ANCHOR)
    if start < 0:
        raise ParseError("schedule table not found (anchor %r)" % TABLE_ANCHOR)
    end = raw.find("</table>", start)
    if end < 0:
        raise ParseError("schedule table is not closed")
    return raw[start:end]


def parse(raw):
    """Return (rooms, cells) from the saved page."""
    table = slice_table(raw)

    head_start, head_end = table.find("<thead>"), table.find("</thead>")
    if head_start < 0 or head_end < 0:
        raise ParseError("<thead> not found")
    columns = [text(c) for c in
               re.findall(r"<th[^>]*>(.*?)</th>", table[head_start:head_end], re.S)]
    if len(columns) < 2:
        raise ParseError("expected a Time column plus room columns, got %r" % columns)
    if columns[0].lower() != "time":
        raise ParseError("first column is %r, expected 'Time'" % columns[0])
    rooms = columns[1:]

    body_start = table.find("<tbody>")
    if body_start < 0:
        raise ParseError("<tbody> not found")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table[body_start + 7:], re.S)

    day = None
    cells = []
    for index, row in enumerate(rows):
        found = re.findall(r"<td\b([^>]*)>(.*?)</td>", row, re.S)
        if not found:
            continue

        # A day banner is one cell spanning the whole table.
        if len(found) == 1 and int(attr(found[0][0], "colspan") or 1) > len(rooms):
            day = text(found[0][1])
            if day not in DAYS:
                raise ParseError(
                    "row %d: unknown day %r (known: %s)"
                    % (index, day, ", ".join(DAYS))
                )
            continue

        stamp = text(found[0][1])
        if not stamp:
            continue
        if day is None:
            raise ParseError("row %d: time %r appears before any day banner"
                             % (index, stamp))

        column = 0
        for attrs, body in found[1:]:
            span = max(1, int(attr(attrs, "colspan") or 1))
            if column >= len(rooms):
                raise ParseError("row %d: cells overflow the %d room columns"
                                 % (index, len(rooms)))
            label = text(body)
            if label:
                cells.append(build(day, stamp, column, span, rooms, body, attrs, label))
            column += span

    return rooms, cells


def build(day, stamp, column, span, rooms, body, attrs, label):
    strong = re.search(r"<strong[^>]*>(.*?)</strong>", body, re.S)
    title = text(strong.group(1)) if strong else label

    # The speaker is whatever follows the <br>: an <a>, a <span>, or bare text.
    parts = re.split(r"<br\s*/?>", body, maxsplit=1, flags=re.I)
    speaker = text(parts[1]) if len(parts) > 1 else ""

    anchor = re.search(r"<a\b([^>]*)>", body)
    url = clean_url(attr(anchor.group(1), "href")) if anchor else ""

    details = prose(attr(attrs, "title"))
    abstract, bio = split_details(details)

    if abstract:
        kind = "talk"
    elif url:
        kind = "event"          # the fundraiser auction: scheduled, but not a talk
    else:
        kind = "note"           # SUNDAY OPEN / PACK UP TALK HALLS / SHOW CLOSE

    across = span >= len(rooms)
    return {
        "kind": kind,
        "day": day,
        "time": stamp,
        "minutes": to_minutes(stamp),
        "roomIdx": column,
        "span": span,
        "room": ", ".join(rooms) if across else rooms[column],
        "across": across,
        "title": title,
        "speaker": speaker,
        "url": url,
        "abstract": abstract,
        "bio": bio,
        "details": details,
    }


def split_details(details):
    """Split "Abstract: ... / Bio: ..." into its two halves.

    Every abstract in the source opens with "Abstract:"; most, but not all,
    carry a "Bio:" paragraph.  Both markers are optional here so an edit
    upstream degrades to a single blob instead of losing the text.
    """
    if not details:
        return "", ""
    body = re.sub(r"^\s*Abstract:\s*", "", details, count=1)
    m = re.search(r"^\s*Bio:\s*", body, re.M)
    if not m:
        return body.strip(), ""
    return body[:m.start()].strip(), body[m.end():].strip()


# ----------------------------------------------------------------- enrichment

def derive_durations(cells, rooms):
    """Infer each entry's length from the next start in the same room.

    The grid publishes start times only.  Entries spanning every room bound the
    talk before them in all of them, so they take part in each room's sequence.
    """
    for day in DAYS:
        for room in range(len(rooms)):
            sequence = sorted(
                (c for c in cells
                 if c["day"] == day and (c["across"] or c["roomIdx"] == room)),
                key=lambda c: c["minutes"],
            )
            for i, cell in enumerate(sequence):
                if cell["across"] or cell["roomIdx"] != room:
                    continue
                cell["durationMin"] = span_to_next(sequence, i)

        # Entries across every room measure against that day as a whole.
        whole = sorted((c for c in cells if c["day"] == day),
                       key=lambda c: c["minutes"])
        for i, cell in enumerate(whole):
            if cell["across"]:
                cell["durationMin"] = span_to_next(whole, i)


def span_to_next(sequence, i):
    start = sequence[i]["minutes"]
    for later in sequence[i + 1:]:
        if later["minutes"] > start:
            return min(later["minutes"] - start, MAX_DERIVED_MIN)
    return DEFAULT_LAST_MIN


def assign(cells):
    """Stable ids plus absolute local and UTC times."""
    offset = dt.timedelta(hours=UTC_OFFSET_HOURS)
    for cell in cells:
        date = dt.date.fromisoformat(DAYS[cell["day"]]["date"])
        start = (dt.datetime.combine(date, dt.time())
                 + dt.timedelta(minutes=cell["minutes"]))
        end = start + dt.timedelta(minutes=cell["durationMin"])

        where = "all" if cell["across"] else "r%d" % (cell["roomIdx"] + 1)
        cell["id"] = "%s-%02d%02d-%s" % (
            cell["day"][:3].lower(), cell["minutes"] // 60, cell["minutes"] % 60, where
        )
        cell["date"] = DAYS[cell["day"]]["date"]
        cell["start"] = start.isoformat()
        cell["end"] = end.isoformat()
        cell["startUtc"] = (start - offset).strftime("%Y%m%dT%H%M%SZ")
        cell["endUtc"] = (end - offset).strftime("%Y%m%dT%H%M%SZ")
        cell["durationEstimated"] = True
        del cell["minutes"]


FIELD_ORDER = ("id", "kind", "day", "date", "time", "start", "end",
               "startUtc", "endUtc", "durationMin", "durationEstimated",
               "roomIdx", "span", "across", "room",
               "title", "speaker", "url", "abstract", "bio", "details")


def document(rooms, cells):
    cells.sort(key=lambda c: (c["start"], c["roomIdx"]))
    return {
        "format": "vcfmw-talks",
        "version": 1,
        "event": EVENT_NAME,
        "source": SOURCE_URL,
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timezone": TIMEZONE,
        "utcOffset": "%+03d:00" % UTC_OFFSET_HOURS,
        "rooms": rooms,
        "days": [dict(name=name, **info) for name, info in DAYS.items()],
        "talks": [{k: c[k] for k in FIELD_ORDER} for c in cells],
    }


# ----------------------------------------------------------------- validation

MIN_EXPECTED = 20


def validate(doc):
    """Return a list of problems. Non-empty means do not write the file."""
    problems = []
    talks = doc["talks"]

    if len(talks) < MIN_EXPECTED:
        problems.append("only %d entries parsed, expected at least %d - the source "
                        "page has probably changed" % (len(talks), MIN_EXPECTED))

    seen = {}
    for t in talks:
        if t["id"] in seen:
            problems.append("duplicate id %s: %r and %r"
                            % (t["id"], seen[t["id"]], t["title"]))
        seen[t["id"]] = t["title"]

        if not t["title"]:
            problems.append("%s: empty title" % t["id"])
        if t["kind"] == "talk" and not t["abstract"]:
            problems.append("%s: talk with no abstract (%r)" % (t["id"], t["title"]))
        if t["roomIdx"] >= len(doc["rooms"]):
            problems.append("%s: room index %d past %d rooms"
                            % (t["id"], t["roomIdx"], len(doc["rooms"])))

    days = {t["day"] for t in talks}
    for day in sorted(set(DAYS) - days):
        problems.append("no entries for %s" % day)
    for day in sorted(days):
        if day not in WEEKDAYS:
            problems.append("%r is not a weekday" % day)

    return problems


def report(doc):
    talks = doc["talks"]
    kinds = {}
    lengths = {}
    for t in talks:
        kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
        lengths[t["durationMin"]] = lengths.get(t["durationMin"], 0) + 1

    print("%d entries: %s" % (
        len(talks), ", ".join("%d %s" % (n, k) for k, n in sorted(kinds.items()))))
    print("%d days, %d rooms: %s" % (
        len(doc["days"]), len(doc["rooms"]), " | ".join(doc["rooms"])))
    print("durations: %s" % ", ".join(
        "%d at %dmin" % (n, m) for m, n in sorted(lengths.items())))
    print("%d entries without a usable link" % sum(1 for t in talks if not t["url"]))

    # Talks legitimately run past the published show-floor hours (evening
    # programming), so this is a note, never a failure.
    for t in talks:
        hour = int(t["start"][11:13])
        if hour < 9 or hour >= 20:
            print("  note: %s %s outside show-floor hours - %s"
                  % (t["day"], t["time"], t["title"][:52]))


# --------------------------------------------------------------------- inline

def inline(path, payload):
    with open(path, encoding="utf-8") as fh:
        page = fh.read()
    start, end = page.find(INLINE_BEGIN), page.find(INLINE_END)
    if start < 0 or end < 0:
        raise ParseError("%s has no %s / %s markers" % (path, INLINE_BEGIN, INLINE_END))
    if end < start:
        raise ParseError("%s has the inline markers in the wrong order" % path)
    block = '%s\n<script id="talksData" type="application/json">\n%s\n</script>\n' % (
        INLINE_BEGIN, payload.replace("</", "<\\/"))
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(page[:start] + block + page[end:])
    print("inlined %d bytes into %s" % (len(payload), path))


# ----------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Parse the VCF Midwest talk schedule grid into talks.json.")
    ap.add_argument("--in", dest="src", default="talks_grid.htm",
                    help="saved schedule page (default: talks_grid.htm)")
    ap.add_argument("--out", default="talks.json",
                    help="JSON to write (default: talks.json)")
    ap.add_argument("--fetch", action="store_true",
                    help="parse %s directly instead of a local file" % SOURCE_URL)
    ap.add_argument("--save-source", action="store_true",
                    help="with --fetch, also keep the downloaded page at --in")
    ap.add_argument("--check", action="store_true",
                    help="parse and report without writing anything")
    ap.add_argument("--inline", metavar="HTML",
                    help="also splice the JSON into HTML between the talks markers")
    args = ap.parse_args(argv)

    try:
        check_dst()

        if args.fetch:
            print("fetching %s" % SOURCE_URL)
            with urllib.request.urlopen(SOURCE_URL, timeout=30) as response:
                body = response.read().decode("utf-8", "replace")
            # The scrape is an intermediate; talks.json is the artefact worth
            # keeping, so the page is parsed from memory unless asked otherwise.
            if args.save_source and not args.check:
                with open(args.src, "w", encoding="utf-8", newline="") as fh:
                    fh.write(body)
                print("saved %d bytes to %s" % (len(body), args.src))
        else:
            try:
                with open(args.src, encoding="utf-8") as fh:
                    body = fh.read()
            except FileNotFoundError:
                # The scraped page is not committed; --fetch is the usual route.
                raise ParseError(
                    "%s is not here. Run with --fetch to pull it from %s, "
                    "or pass --in with a saved copy." % (args.src, SOURCE_URL)
                )

        rooms, cells = parse(body)
        derive_durations(cells, rooms)
        assign(cells)
        doc = document(rooms, cells)

        problems = validate(doc)
        report(doc)
        if problems:
            print("\n%d problem(s):" % len(problems), file=sys.stderr)
            for p in problems:
                print("  - %s" % p, file=sys.stderr)
            return 1

        if args.check:
            print("\nok (--check: nothing written)")
            return 0

        payload = json.dumps(doc, indent=2, ensure_ascii=False)
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload + "\n")
        print("\nwrote %s (%d bytes)" % (args.out, len(payload) + 1))

        if args.inline:
            inline(args.inline, payload)
        return 0

    except ParseError as err:
        print("parse_talks: %s" % err, file=sys.stderr)
        return 1
    except OSError as err:
        print("parse_talks: %s" % err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
