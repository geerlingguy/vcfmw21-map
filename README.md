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

As stated previously, this page was generated with Claude Opus. Here is the full prompt / chat history: [https://claude.ai/share/fad5ac2a-4f86-4068-88cf-b095a97d3f20](https://claude.ai/share/fad5ac2a-4f86-4068-88cf-b095a97d3f20).
