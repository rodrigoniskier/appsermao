# DESIGN.md — Exposibot / Reformation Folio

## 1. Design intent

Exposibot is a study and sermon-preparation workspace, not a generic SaaS dashboard.
The visual language should evoke a contemporary theological study desk: printed folios,
annotated margins, restrained ecclesiastical color, and editorial typography.

The interface must feel:
- scholarly rather than corporate;
- warm rather than technological;
- textual rather than dashboard-heavy;
- calm, serious, and durable;
- contemporary without looking like a startup template.

This design intentionally contrasts with the previous dark blue/gold interface.

## 2. Core visual metaphor

**A modern Reformation folio.**

Think of a high-quality critical edition placed on a study desk:
- warm paper surfaces;
- ink-black typography;
- oxblood red for primary action and navigation;
- muted mineral/stone colors for secondary surfaces;
- thin rules instead of floating shadows;
- serif typography for reading and major headings;
- sans-serif typography for controls, metadata, labels, and navigation.

Do not imitate antique parchment, medieval ornament, gothic type, crosses, religious icons,
or decorative ecclesiastical imagery. The reference is editorial and scholarly, not costume-like.

## 3. Color tokens

```css
--folio-canvas: #eee7dc;
--folio-paper: #fbf8f2;
--folio-paper-strong: #ffffff;
--folio-paper-muted: #e5ddd1;
--folio-ink: #211c19;
--folio-ink-soft: #443b36;
--folio-muted: #746961;
--folio-rule: #cfc3b5;
--folio-rule-strong: #a99a8a;
--folio-oxblood: #7a2f2a;
--folio-oxblood-dark: #56201d;
--folio-oxblood-soft: #ead8d5;
--folio-sage: #566358;
--folio-sage-soft: #e1e6df;
--folio-warning: #9a681d;
--folio-danger: #9b302d;
--folio-success: #47604b;
```

### Color rules
- Oxblood is the primary action color and navigation accent.
- Never use bright startup blue as a primary action color.
- Green/sage is semantic and supportive, not decorative.
- Large backgrounds remain paper, cream, charcoal, or oxblood.
- Avoid neon colors and saturated gradients.

## 4. Typography

### Editorial family
Use `Georgia, 'Times New Roman', serif` for:
- page titles;
- sermon titles;
- major section headings;
- analysis reading pane;
- long-form sermon content.

### Interface family
Use `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif` for:
- navigation;
- buttons;
- labels;
- metadata;
- form controls;
- tabs;
- status text.

### Hierarchy
- Hero/page title: 34–44px serif, 600/700.
- Section title: 22–28px serif.
- Card title: 19–22px serif.
- Reading body: 17–18px serif, line-height 1.7–1.85.
- Interface body: 14–16px sans-serif.
- Labels/meta: 11–13px sans-serif with modest tracking.

Do not make every label bold. Hierarchy should come from family, size, whitespace, and rules.

## 5. Geometry

- Main cards/panels: 0–3px radius.
- Buttons: 2px radius.
- Inputs: 2px radius.
- Pills only for true statuses/tags.
- Avoid large 12–24px SaaS-style rounded cards.
- Use 1px rules extensively.
- Use shadows only as subtle paper lift; never luminous/glowing shadows.

## 6. Spacing

Base unit: 4px.

Preferred scale:
`4, 8, 12, 16, 24, 32, 48, 64, 96`.

Editorial pages should have generous outer margins and relatively dense internal information.

## 7. Header and navigation

The application header should feel like the binding/edge of a volume:
- oxblood background;
- warm off-white text;
- thin darker lower rule;
- restrained height;
- no floating/translucent glass effect.

Brand name may use serif typography. Utility navigation remains sans-serif.

Tabs are not pills. They resemble index tabs:
- transparent background;
- thin bottom border;
- active tab uses paper surface plus oxblood indicator.

## 8. Dashboard

The sermon list should read like an archive/catalog rather than an app marketplace.

Cards:
- paper background;
- thin border;
- small oxblood top rule or left rule;
- title in serif;
- metadata in tracked sans-serif;
- no large drop shadows.

Primary action: oxblood solid.
Secondary/destructive actions: outlined or textual.

## 9. Workspace — research mode

The three columns intentionally have distinct paper roles.

### Left — Text and tools
- warm cream background;
- compact controls;
- tool buttons like catalog/index entries;
- tool hover uses oxblood tint, not bright fill.

### Center — Analysis
- brightest paper surface;
- reading typography in serif;
- generous line-height;
- headings in oxblood/ink;
- visual priority over surrounding chrome.

### Right — Collected material
- very light sage/stone tint;
- note tags in oxblood or sage;
- dashed/solid editorial separators.

Panel headers are compact, uppercase sans-serif labels with tracking.

## 10. Workspace — outline mode

The sermon outline is a writing surface.

- Central column width: approximately 920px.
- Main background: warm canvas.
- Form groups are separated by whitespace, not floating cards.
- Major sections use serif headings and horizontal rules.
- Sermon points use a paper block with a narrow oxblood rule.
- AI suggestion button may be distinctive but must remain within the palette; no purple/blue gradient.

## 11. Forms

Inputs:
- paper-white background;
- dark ink text;
- 1px stone rule;
- 2px oxblood focus border/ring;
- no heavy shadows.

Labels:
- sans-serif;
- small;
- dark muted tone;
- sentence case.

Placeholders must have sufficient contrast without looking like entered text.

## 12. Buttons

### Primary
Oxblood fill + warm white text.

### Secondary
Paper background + dark ink + border.

### Success
Muted sage/green.

### Danger
Prefer outline/text until destructive confirmation is needed.

Buttons should use modest letter spacing and medium weight. Avoid oversized pill buttons.

## 13. Reading / sermon preview

The preview should look printable even on screen:
- warm outer canvas;
- white paper sheet;
- serif text;
- oxblood headings/rules;
- metadata rendered as a quiet editorial block;
- toolbar visually separated from the document.

Print output must remain high-contrast and clean.

## 14. Accessibility

- Body text contrast target: WCAG AA or better.
- Focus indicators must remain visible.
- Never encode status by color alone.
- Touch targets should remain at least ~40px on narrow screens where practical.
- Preserve responsive single-column fallback for the research workspace.

## 15. Responsive behavior

Desktop: retain three-column research workspace.
Tablet: stack columns vertically when horizontal density becomes harmful.
Mobile: single-column reading order, full-width controls, tabs remain easily tappable.

Typography may reduce one scale step on mobile but must never become cramped.

## 16. Do

- Make text feel central.
- Prefer rules and whitespace to shadows.
- Use serif/sans contrast intentionally.
- Keep oxblood as the visual signature.
- Preserve clear information density.
- Treat analysis output as a document, not a chat bubble.

## 17. Do not

- Do not reintroduce the previous blue/gold dark-dashboard language.
- Do not use glassmorphism.
- Do not use neon/glow effects.
- Do not use purple AI gradients.
- Do not use large rounded SaaS cards.
- Do not add decorative crosses, stained glass, manuscript illustrations, or denominational imagery.
- Do not sacrifice usability for an antique aesthetic.

## 18. Agent instruction

Before changing any visible interface in this repository, read this file.
New UI must reuse these tokens and principles. When a local template style conflicts with
this document, migrate the local style toward this system rather than creating another visual dialect.
