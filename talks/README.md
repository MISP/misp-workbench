# Talks

Slide decks about misp-workbench, written in Markdown and rendered with
[Marp](https://marp.app/).

| Deck | Length | Source |
|---|---|---|
| MISP Workbench in 5 minutes | 10 slides, a lightning talk | [`lightning/slides.md`](lightning/slides.md) |

## Rendering

Install the Marp CLI once (it needs Node.js; the PDF, PPTX and image outputs
also need Chrome, Chromium or Edge):

```bash
npm install -g @marp-team/marp-cli
# or run it without installing: npx @marp-team/marp-cli ...
```

From the deck's folder:

```bash
cd talks/lightning

# HTML: one self-contained page, presented in the browser (F for full screen)
marp slides.md -o slides.html

# PDF, to present or hand out
marp slides.md --pdf --allow-local-files -o slides.pdf

# PowerPoint
marp slides.md --pptx --allow-local-files -o slides.pptx

# One PNG per slide
marp slides.md --images png --allow-local-files -o slides.png
```

`--allow-local-files` is needed for every format but HTML: the slides embed
the logo and screenshots from `docs/` by relative path, and the browser Marp
drives refuses to load local files without it.

While editing, preview with live reload:

```bash
PORT=8090 marp -s .  # serves the folder at http://localhost:8090 (its default, 8080, is the API's)
marp -w slides.md    # rebuilds slides.html on every save
```

The VS Code extension *Marp for VS Code* previews a deck in the editor as well.

## Writing a deck

- The theme is in the deck's front matter (`style:`), so a deck renders the
  same anywhere, without a separate theme file. It loads IBM Plex Sans and
  JetBrains Mono from Google Fonts; offline, a fallback font is used.
- Speaker notes are HTML comments (`<!-- ... -->`) at the end of a slide:
  the HTML output's presenter view (press P) shows them, and
  `--pdf-notes` adds them to a PDF.
- HTML elements may carry a `class` but not a `style` attribute (Marp drops
  it): add a class to the theme instead.
- Images come from `docs/screenshots/` and `docs/images/`. Regenerate them
  with the docs screenshot suite (`frontend/scripts/docs-screenshots`) rather
  than taking new ones by hand.
- QR codes: `qrencode -t SVG -m 2 -o qr.svg "<url>"`.
