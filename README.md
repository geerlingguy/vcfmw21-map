# VCF Midwest 21 Interactive Map

View the map: [https://geerlingguy.github.io/vcfmw21-map/](https://geerlingguy.github.io/vcfmw21-map/)

The VCF Midwest website has a wealth of information. But the table map is a bit hard to navigate, since it only has names and IDs, not any other information.

I ran the table plan and Exhibitor CSV file through Claude Opus with the instruction:

```
VCF Midwest put out the attached 'table plan' with a map layout from above of all the tables at VCF Midwest 2026.

They also have this page that lists all the exhibitors, matching up to the table locations in the graphical map.

It's annoying having to switch tabs to find out more, so I'd like to have an interactive version of the map. Can you code that up in a static HTML page that I could open up in a browser standalone, which has the map shown. When you hover over each table (or set of tables if they're all one vendor?) it highlights that with a translucent cover, then when you click, it has an info popover that persists with the name, exhibit title, and description, then on a line below the ID and Location. The name should link to the same URL the name links to on the Exhibitor's page.

And the top of the page should have a link to the VCF Midwest website (https://vcfmw.org/).

I have attached a CSV with all the exhibitor information (21tables.csv), and the high resolution image of the table layout (21tableplan.png).
```

And it spat out the index.html file referencing the original table plan PNG (as well as the self-contained larger page vcfmw21-map.html).

This is more useful for me as I can search by name, description, ID, etc. and also zoom around on the map to find out what is where.

## Hover for details

Resting the mouse on a table for a second opens that exhibitor's details without
pinning them. Moving to another table closes the popover and starts the second over
for the new one, and moving off the tables closes it entirely. The popover stays up
while the pointer is on it, so the exhibitor link and **copy link** are still reachable.
If an exhibitor was already pinned by clicking, their details come back once the
preview closes. Touch devices have no hover, so they are unaffected.

## Maintain exhibitor selections

Clicking a table opens its details and marks it on the map, and the next click
normally replaces that selection. Click **Maintain exhibitor selections** in the header
to keep, so you can build up a list of every table you want to visit.

With the box ticked:

- Clicking a table adds it to the selection, and clicking the same table again removes it.
- Clicking the background, pressing Escape, closing the popover, or hitting **fit**
  only puts the details away. The marks stay.
- Unticking the box collapses back to whichever exhibitor's details are open and
  drops the rest, so the map cannot be left stuck full of marks.

**export** writes the current exhibitor selections to a JSON file and **import** reads it
back, which is how a list survives closing the tab or moves to your phone.

## Talks schedule

**Talks**, next to **Exhibitors** in the header, opens the presentation schedule over the
map. It is the same grid VCF Midwest publishes at
[vcfmw.org/talkschedule](https://vcfmw.org/talkschedule) — time down the side, the three
rooms across — drawn in the same light palette as the rest of the guide, so the schedule
and the map read as one page rather than two. Talks you have kept are marked in the same
cyan the map uses for a selected table, and a search hit in the same amber.

- **Hover a talk for a second** and its abstract, speaker bio and room open in the same
  popover the map uses. Moving off closes it; the popover stays up while the pointer is on
  it, so the speaker's link is reachable.
- **Click or tap a talk** to keep it. It stays marked, and clicking it again drops it.
  Unlike the map, talks are always multi-select — there is no checkbox to tick first.
- **Tapping the background or pressing Escape** puts the details away and leaves your
  picks alone.
- **Searching** works on the schedule while it is open: titles, speakers, rooms, times and
  the full abstracts. The grid dims what does not match so you can still see when things
  are; on a phone it filters the list instead. The count on the other toggle tells you how
  many exhibitors also match, so a search is never a dead end.
- **On a phone** the grid becomes a linear day-by-day list, which is what vcfmw.org sends
  mobile visitors to anyway.

During the show, a red rule is drawn across the grid at the current time, labelled with the
local hour, and the **now** button scrolls to it. It appears only while the schedule is
actually running — Saturday 10:00 AM to the end of the evening concert, and Sunday morning
to show close — and stays hidden the rest of the year. Append `?now=2026-09-12T16:20:00Z`
to the URL to preview it.

### Adding talks to your calendar

**calendar**, in the schedule's header, writes the talks you have kept to a `.ics` file
that Google Calendar, Apple Calendar and Outlook all import. Each event carries the
abstract, the speaker bio and the room.

Two things worth knowing: the grid publishes start times only, so **end times are worked
out from the next talk in the same room** and every event says so in its description. And
each event's UID is stable, so re-importing after adding a few more talks updates what is
already in your calendar instead of duplicating it.

### Where the schedule comes from

`talks.json` is generated from the published page by `tools/parse_talks.py`, and committed.
The schedule is also written **into `index.html` itself**, so the page works when you open
it straight off the filesystem — a browser will not `fetch()` from a `file://` page.

To refresh both after VCF Midwest changes the schedule:

```sh
python tools/parse_talks.py --fetch --inline index.html   # the one to run
python tools/parse_talks.py --fetch --check               # parse and report, write nothing
```

Run the first one whenever the schedule changes: it writes `talks.json` **and** updates the
copy inside `index.html` in the same pass, so the two cannot drift apart. If you only run
`--fetch`, the served site picks up the new `talks.json` but a page opened from disk still
shows the old inlined copy.

`--fetch` parses the downloaded page from memory and does not leave the scrape behind; add
`--save-source` if you want it kept.

The script needs only the Python standard library. It refuses to write a file it cannot
make sense of — a missing table, an unknown day, an unparseable time, a row whose cells
overrun the rooms — so a change at vcfmw.org shows up as a failed run rather than a
half-empty schedule.

The event dates and timezone are constants at the top of that script, since the published
grid names only "Saturday" and "Sunday". For VCF Midwest 21 they are 12–13 September 2026,
US Central.

The page reads the inlined schedule when it is there and falls back to fetching
`talks.json` when it is not, so both a static file and a served copy work. If neither is
available the **Talks** button is hidden, the console explains why, and the map behaves
exactly as it did before.

## Linking to a specific exhibitor

The URL fragment opens one exhibitor directly:

| Link | Opens |
| --- | --- |
| `...vcfmw21-map/#026` | the exhibitor with ID 026, the ID shown on the popover |
| `...vcfmw21-map/#26` | the same exhibitor; the leading zeros are optional |
| `...vcfmw21-map/#B120` | table B120, for the few tables with no exhibitor ID |

The **copy link** button on the exhibitor details creates the link and copies it 
to the clipboard.

## AI Disclosure

As stated previously, this page was generated with Claude Opus. Here is the original full prompt / chat history: [https://claude.ai/share/fad5ac2a-4f86-4068-88cf-b095a97d3f20](https://claude.ai/share/fad5ac2a-4f86-4068-88cf-b095a97d3f20).
