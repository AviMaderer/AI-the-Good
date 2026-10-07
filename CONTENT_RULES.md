# AI the Good: run instructions

The scheduled task follows this file. Edit it to change how stories are chosen or written.

**Brand:** AI the Good, byline "Real deployments, positive impact!", published under Future of Purpose. The series shows, with verified evidence, that AI is already doing good for people.

## How an edition works

- One **edition per cycle**, named by the date of its release weekday in Israel time (`release_weekday` in `data/config.json`, default Thursday): `data/weeks/<RELEASE_DATE>.json`, published at `<site_url><RELEASE_DATE>/`.
- Stories are **gathered every day, including Saturday**, into the **upcoming edition**. Until it is released, its page is an unlinked preview (only Avi has the link).
- **Which edition to add to:** on the release weekday, today's edition. On any other day, the next release weekday's edition. Create the week file if it does not exist.
- **Normal runs:** add **up to 3 new stories** and rebuild. Email Avi a short note.
- **Release-day run:** add final stories (aim for 5 or more in the edition where they clear the bar; at least 3 to be worth releasing, and if there are fewer, say so in the email), choose the card stories, write the intro options, rebuild and push. This run does **not** release the edition.
- **An edition is released only when Avi commits his intro** (section 4). Never release it yourself, and never publish it without his committed intro. If he has not committed, it stays an unreleased preview and every later email starts with a reminder line.
- After the release-day run an edition is frozen: new stories go into the next edition, even while the frozen one waits for Avi. Never add to an edition once it is frozen or released.
- Fewer stories is fine. Never pad with a weak story. If a run finds nothing new, still rebuild and say so in one line.

## 1. Before researching

- Today's date is the date in Israel (Asia/Jerusalem).
- Read `data/config.json`, `data/sources.md`, `data/stories-log.csv`, `data/rejects.csv`, the target edition's week file if it exists, and the most recent committed edition (to see which intro angle it used).
- Never repeat a story whose source, institution-and-program, or underlying event is already in the log or in any week file. A new article about a story already logged is a repeat.
- Do not re-check stories listed in `data/rejects.csv` unless there is new evidence.

## 2. Choosing stories

- Search across **all** source groups in `data/sources.md`. Use WebSearch, site-restricted searches, and the sources' own news pages. Look back several days, not only the last 24 hours.
- **Monday runs (Israel time) also do a weekly deep check:** the newest online-first articles of Nature Medicine, NEJM AI, The Lancet Digital Health, JAMA Network Open and npj Digital Medicine, and the newsrooms of major hospitals and universities, looking for deployed or measured AI outcomes. If a page is blocked, use the institution's own page for the same finding. Anything found goes through the same tests below.
- **Roundups and aggregator articles are leads, not sources** (listicles, "top AI stories" round-ups, newsletters, aggregator sites). For each item named in one, find the primary source (the journal, institution or organization) and judge the story there. The primary source is the one you verify and cite in `source`.
- Every story must:
  - show **AI having a positive, real-world effect on people or the planet**, as something **already deployed or already measured**. No funding announcements, pledges, "could one day" claims, competitions, prototypes, or pilots with no outcome data;
  - name a **specific application and a named institution or organization**, and include **at least one concrete number** (people reached, accuracy, time or cost saved, lives affected) where one exists;
  - rest on **peer-reviewed results or a named institution's own verified reporting**. Skip PR without outcomes and anything that is only a vendor's claim;
  - be **recent**: prefer the newest, but accept stories published within the last 3 months. Always show the publication date in `source_name`, and flag anything published more than 4 weeks ago in the double-check list;
  - be **verified at the source**: open the article itself and check every number, name, date and quote against it. Never rely on a search snippet. If the page is blocked (PubMed, PMC, reCAPTCHA walls, paywalls), find the same finding on the institution's or journal's own page. If you cannot verify it, drop the story;
  - be positive on its own evidence: skip studies whose main result was null or negative, and flag in the double-check list if the study authors work for the company that makes the AI tool.
- Aim for a **mix of domains** across the edition: medicine and diagnostics, public health, safety and emergency response, accessibility, agriculture and food, education, science, environment and conservation, poverty and financial inclusion, homelessness services, elder care, mental health. The quality bar beats the mix: never include a weaker story just to cover a domain.
- **Theme limit:** at most 2 stories per theme within one edition (a theme is the `theme` slug, for example `diabetic-eye-screening`, `brain-computer-interface`, `sepsis-alerts`, or a specific model such as `weathernext`). A theme already in the log is allowed again if the institution, application or country is clearly different; say why in the double-check list.
- No more than 2 stories from the same outlet per edition. Prefer free-to-read sources.
- Skip political and partisan topics, and skip stories about the AI industry itself (data centers, funding, tax revenue, energy costs). This series is about AI applications that help people.

## 3. Writing each story (fields in the week file)

Voice: plain-spoken and direct, full sentences, no clichés or hype, light use of long dashes. Claim only what the source shows.

| Field | Rule |
|---|---|
| `key` | short lowercase slug, unique within the edition (e.g. `mayo-redmod`) |
| `added` | today's date, YYYY-MM-DD |
| `tag` | domain, 1-2 words (e.g. `Cancer care`, `Wildlife`) |
| `theme` | short lowercase slug for the log and the theme limit (e.g. `stroke-detection`) |
| `institution` | the named institution(s) and program, e.g. `Mayo Clinic REDMOD` |
| `teaser` | max ~70 characters, for the headline list |
| `headline` | max ~80 characters, plain and specific, naming the result |
| `why` | one line: the key number and how solid it is, e.g. `Randomized trial of 300 patients, JAMA Internal Medicine` |
| `bullet` | for the card. Max 78 characters including spaces, plain text, verb-led, opening with the finding or number. The card makes the text before the first comma bold, so put the lede before the first comma. No markdown, no asterisks. |
| `card` | `true` on the 3-4 stories chosen for the card (set on the release-day run); otherwise omit |
| `texts` | **three versions** of the post, each 40-70 words, short paragraphs: (1) number-led and factual, (2) human: who benefits and how, (3) opens with a question or a hook. Do NOT add an opening line (the page adds a rotating one). Do not use the words "week" or "weekly". Quotes only if copied exactly from the source. Each ends with the hashtag line `#AIforGood`. |
| `source` | article URL (the page you actually fetched, never a google.com/url redirect) |
| `source_name` | publisher and publication date, always both, e.g. `Nature Medicine, Sep 22, 2026` |
| `site` | publisher domain, e.g. `nature.com` |
| `source_lang` | only for non-English sources: the language code, e.g. `"he"` |
| `og_title` | the article's own title (its og:title) |
| `og_image` | the article's preview image URL (its og:image). Leave empty if there is none. Never download or re-host it. |

Add new stories to the end of the `stories` list. Never remove or rewrite stories already in the file, except to fix an error.

## 4. The edition intro (Avi's insight at the top)

On the release-day run, write `intro.options` in the week file: **five options**. Each has:

- `angle`: one of `pattern`, `doom-vs-evidence`, `purpose`, `question`, `one-liner`
- `headline`: a short all-capital line (a handful of words, not a full sentence) that invites the reader in
- `text`: the intro, 40-90 words (the `one-liner` is a single sentence)

The angles:

- `pattern`: what this edition's stories have in common. One real observation, not a summary list.
- `doom-vs-evidence`: the contrast between doom-heavy AI headlines and the deployed results below.
- `purpose`: how these results connect to human purpose and flourishing, in the Future of Purpose voice. AI as something that serves people's purpose, not something that replaces it.
- `question`: ends with a question the reader can answer for themselves.
- `one-liner`: one plain sentence.

Rules for all options: same voice as section 3, evergreen wording (no "week" or "weekly"), and nothing that claims more than the stories below show. List first an angle different from the one used by the most recent committed intro.

`intro.final` stays `null` until Avi commits. The Commit button on the preview page writes `intro.final` as `{ "headline", "text", "angle", "committed_at" }` to the week file. Never write `intro.final` yourself.

## 5. The roundup card

The build renders `<RELEASE_DATE>/card.png` (1080 x 1350) from the stories with `"card": true`. Choose 3 or 4 stories with the most striking numbers across different domains, and use 4 whenever 4 qualify.

**The design is fixed.** `tools/build.py` (`card_html`) draws it exactly as below. Never change the layout, colors, fonts or sizes; a run only supplies the content.

- Content: header "FUTURE OF PURPOSE" and the release date; title "AI the Good" with the highlight on "Good"; byline "Real deployments, positive impact!"; one bullet per card story from its `bullet` field, with the text before the first comma in bold; footer `futureofpurpose.substack.com`.
- If a bullet is longer than 78 characters, fix the bullet text. Do not shrink the font.

Colors:

| Element | Color |
|---|---|
| Background (flat, no pattern) | deep teal `#16302F` |
| Title "AI the", bullet text | pale teal `#D4E4E0` |
| Highlight behind "Good" | amber `#E3A75E`, with "Good" in deep teal `#16302F` |
| Bold lede in each bullet | white `#FFFFFF` |
| Bullet dots, short accent bar | amber `#E3A75E` |
| Header, byline, footer text | sage `#A9C4BF` |
| Divider lines under the header and above the footer | sage `#A9C4BF` at 35% opacity |

Fonts: Rubik (500 and 700) for the header, title, byline and footer; Assistant (400 and 700) for the bullets. Both are in `assets/fonts/`.

Layout, top to bottom (padding 84 px top, 88 px sides, 76 px bottom):

1. **Header row:** "FUTURE OF PURPOSE" on the left and the release date on the right in the form `OCTOBER 8, 2026`; Rubik 500, 26 px, all capitals, letter-spacing 0.16 em. Then a 2 px divider line 30 px below.
2. **Title:** "AI the Good", 64 px below the divider; Rubik 700, 132 px, letter-spacing -0.025 em. "Good" sits on an amber block with rounded corners (12 px radius, 0.14 em padding on each side).
3. **Byline:** "Real deployments, positive impact!", 30 px below the title; Rubik 500, 40 px.
4. **Accent bar:** amber, 140 x 8 px with rounded ends, 48 px below the byline.
5. **Bullets:** start 56 px below the bar, 36 px apart; Assistant 400, 42 px, line height 1.28. Each has an 18 px amber dot on the left with the text indented 44 px. The text before the first comma is Assistant 700 in white; the rest is regular in pale teal. With no comma, the whole bullet is bold.
6. **Footer:** pinned to the bottom, with a 2 px divider above it and 30 px of space between; `futureofpurpose.substack.com` in Rubik 500, 30 px, letter-spacing 0.03 em.

## 6. Logs, build and publish

1. Save the edition file.
2. Append one row per new story to `data/stories-log.csv` (date, edition, key, institution, theme, source URL). Append stories you checked and rejected to `data/rejects.csv` (date, title or URL, one-line reason), and delete rows older than 14 days.
3. Run `python tools/build.py data/weeks/<RELEASE_DATE>.json`.
4. Commit with the message `Edition <RELEASE_DATE>: +N stories` (release-day run: `Ready <RELEASE_DATE>: awaiting intro`) and push to `main`.

When Avi presses Commit on the preview page, a GitHub Actions workflow rebuilds the site. That releases the edition: the main link and the archive switch to it, and the build writes `data/social/<RELEASE_DATE>.txt`, the roundup post ready for Facebook and LinkedIn: the committed all-capital headline, a blank line, the committed intro, a blank line, and the edition page link. The card (`card.png`) goes with it.

## 7. Email Avi (avi.maderer@gmail.com)

Always put the preview page link at the top. If an earlier edition is still waiting for Avi's intro, the second line says so, with its link. Write all URLs as plain text. Subjects are in all capitals.

**Normal run** subject: `AI THE GOOD <DATE>: N STORIES ADDED TO <RELEASE_DATE> EDITION` (when N is 0: `AI THE GOOD <DATE>: NOTHING NEW`). Body: the preview link, the running story count, each new story's headline, source link and one line on how it was verified, and anything to double-check (a story published more than 4 weeks ago, a vendor-authored study, a theme already in the log and why it is allowed, a thin source, a missing preview image).

**Release-day run** subject: `AI THE GOOD EDITION <RELEASE_DATE>: READY FOR YOUR INTRO`. Body: the preview link ("choose or edit your intro, then press Commit"), the number of stories, the 3-4 card bullets, each new story as above, and anything to double-check.

If anything fails (build or push error), email Avi what happened instead, and do not publish a partial page.
