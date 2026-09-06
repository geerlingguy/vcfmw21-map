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
