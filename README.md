# Boletines · página Recursos de ICOMadera

This repository keeps the **Boletín Costa Rica Forestal** cards on ICOMadera's
Recursos page up to date automatically. Nobody has to edit the website.

**Owner:** ICOMadera. This is organisation infrastructure, not any one
person's — it lives in the ICOMadera GitHub account and stays there as web
administrators change.

### PENDING — convert to a GitHub organisation

Not done yet. `ICOMadera` is currently a single personal account, so access
to it means sharing one password. That is the piece that does not age well
across a change of web administrator.

When the board is ready:

1. From the ICOMadera account: **Settings → Organizations → New organization**
   (the free plan is enough).
2. Add at least one other board member as an **owner**, so access never rests
   on one person.
3. Transfer this repository into the organisation:
   **Settings → General → Transfer ownership**.
4. In the Squarespace Recursos code block, change `var ORG = "ICOMadera"` to
   the organisation's name, and paste the block once more.
5. Update the same name in the weekly watchdog task, which reads
   `raw.githubusercontent.com/<ORG>/boletines/main/boletines.json`.

Step 4 is the only one that touches the website, and nothing breaks in the
meantime — the current setup keeps working until the transfer happens.

---

## How it works

1. Every Monday a GitHub Action reads the CFMI bulletin index at
   <https://www.camaraforestal.org/boletín-informativo>.
2. It takes the **newest four** boletines, opens each PDF and lifts the title
   off the cover page.
3. It writes `boletines.json` and commits it — but only when something
   actually changed.
4. The Recursos page on the website reads `boletines.json` when a visitor
   loads it, and draws the four cards from it.

Nothing in this repository is secret, and no passwords or tokens are stored
anywhere. The Action uses the token GitHub provides automatically.

```
boletines.json                        what the website reads
overrides.json                        hand-picked titles (see below)
scripts/build_boletines.py            fetches, parses, writes boletines.json
scripts/test_parser.py                offline checks, run by the Action
.github/workflows/refresh-boletines.yml   the weekly schedule
```

---

## Fixing a title

The script takes whatever the PDF prints on its cover. That is usually right,
but CFMI change their layout from time to time, and some covers split words
oddly. When a card looks wrong:

1. Open `overrides.json` here on github.com and click the pencil icon.
2. Add a line under `"titles"`, keyed by the boletín label exactly as the CFMI
   site writes it:

   ```json
   "35-2026": "El título correcto, con acentos"
   ```

3. Commit the change.
4. Go to the **Actions** tab → *Refresh boletines* → **Run workflow**.

The website shows the corrected title within a few minutes. Overrides for old
boletines do no harm — they are ignored once that boletín is no longer among
the newest four.

## Running it by hand

Actions tab → *Refresh boletines* → **Run workflow**. Useful if CFMI publish
mid-week and you don't want to wait for Monday.

## Checking it is still working

`boletines.json` shows an `updated` timestamp and the four boletines currently
on the site. If the Action fails, GitHub emails the organisation owners. A
failure is safe: the previous `boletines.json` stays in place and the website
keeps showing the last good set.

---

## The website side

The Recursos page holds one Squarespace **code block** containing the whole
section. The master copy lives with the web administrator as
`Squarespace_Recursos_CodeBlock.html`.

That block should not need editing again. It contains a small script that
loads `boletines.json` from this repository, plus four hardcoded cards that
stay visible if the file cannot be reached, so the page is never empty.

The one line that might ever need changing is near the bottom of the block:

```js
var ORG  = "ICOMadera";   // ICOMadera's GitHub account
var REPO = "boletines";   // this repository's name
```

If you do edit the block: open the .html file, select all, copy, then in the
Squarespace code block select all and paste. Scripts don't run in Squarespace's
editor preview, so the cards will look empty there — check the published page
instead.

## Handing this over

The next web administrator needs: owner access to this GitHub organisation,
and the Squarespace login. Nothing else. There are no credentials to transfer
and no personal accounts involved.
