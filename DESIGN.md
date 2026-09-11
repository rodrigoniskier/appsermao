# DESIGN.md — Exposibot / Blue Steel

## 1. Design intent

Exposibot is a technical workspace for biblical study and sermon preparation. The visual language should feel precise, engineered, clean, and premium without resembling a generic corporate dashboard.

The interface must feel:
- metallic and technical rather than rustic;
- bright rather than dark;
- disciplined rather than decorative;
- serious and academic without becoming austere;
- contemporary, durable, and clearly differentiated from the previous Reformation Folio theme.

## 2. Core visual metaphor

**Blue Steel study console.**

The interface combines three visual materials:
- deep metallic blue for structural chrome, headers, navigation, and primary actions;
- white for reading, writing, and content surfaces;
- safety yellow for selection, emphasis, active states, and high-value calls to action.

Use subtle metallic gradients only on structural elements. Content surfaces remain mostly flat and white so the text stays central.

Do not imitate BMW or any other commercial brand. The automotive/engineering reference is conceptual: precision, contrast, clean geometry, and controlled metallic sheen.

## 3. Color tokens

```css
--steel-canvas: #e8eef3;
--steel-surface: #ffffff;
--steel-surface-soft: #f4f7fa;
--steel-surface-metal: #d6e0e8;
--steel-surface-metal-dark: #bcc9d4;
--steel-ink: #142536;
--steel-ink-soft: #405467;
--steel-muted: #657789;
--steel-rule: #b7c4cf;
--steel-rule-strong: #8799a8;
--steel-blue: #0b4f86;
--steel-blue-mid: #17679f;
--steel-blue-light: #3e86b8;
--steel-blue-dark: #082f52;
--steel-blue-deep: #061f37;
--steel-yellow: #f2c300;
--steel-yellow-hover: #d9ad00;
--steel-yellow-soft: #fff4b8;
--steel-success: #2f7b5b;
--steel-danger: #b23d46;
--steel-warning: #a96f00;
```

### Color rules
- Blue is the structural color and default primary action color.
- White is the dominant content surface.
- Yellow is an accent, never the dominant page background.
- Yellow may mark active tabs, primary creation actions, important selection, and narrow rules.
- Avoid purple, oxblood, beige/parchment, neon cyan, and multicolor gradients.
- Semantic red/green remain reserved for destructive/success states.

## 4. Metallic treatment

Metallic effect must be subtle and functional.

Recommended blue structural gradient:

```css
linear-gradient(180deg, #17679f 0%, #0b4f86 38%, #083a64 72%, #082f52 100%)
```

Recommended steel surface gradient:

```css
linear-gradient(180deg, #f9fbfc 0%, #e7edf2 48%, #d6e0e8 100%)
```

Rules:
- Use metallic gradients on header chrome, selected structural controls, compact panel headers, and occasional toolbars.
- Do not put gradients behind long-form text.
- Do not use glossy highlights, lens flares, chrome reflections, or fake 3D bevels.
- Shadows should be short, cool, and subtle.

## 5. Typography

Use a modern sans-serif stack throughout:

`Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`

Long-form analysis may use the same family at a more relaxed line-height. The goal is a technical reading environment, not an editorial book aesthetic.

### Hierarchy
- Page title: 30–40px, 700.
- Section title: 20–26px, 700.
- Card title: 17–20px, 700.
- Analysis body: 16–17px, 400, line-height 1.7–1.8.
- Interface body: 14–16px.
- Labels/meta: 11–13px, 600–800 with restrained tracking.

## 6. Geometry

- Main cards/panels: 4–8px radius.
- Buttons: 4–6px radius.
- Inputs: 4px radius.
- Use square-ish engineering geometry; avoid oversized pills.
- Use 1px steel borders and narrow yellow keylines for emphasis.
- Shadows must remain subtle and cool-toned.

## 7. Header and navigation

The application header is metallic blue:
- deep blue gradient;
- white text;
- narrow yellow lower rule;
- compact height;
- no glass transparency.

Tabs:
- live inside the header chrome;
- inactive state uses muted white/steel text;
- active state uses white surface with deep blue text and a yellow indicator;
- never render tabs as rounded pills.

## 8. Dashboard

Dashboard cards are white technical panels on a pale steel canvas.

Cards:
- white surface;
- steel border;
- narrow metallic blue top rail;
- yellow micro-accent for state or interaction;
- clear sans-serif hierarchy;
- subtle cool shadow on hover only.

Primary create action may use yellow fill with deep-blue text to stand apart from ordinary blue actions.

## 9. Workspace — research mode

The three columns remain visually distinct but belong to the same industrial system.

### Left — Text and tools
- pale steel background;
- white inputs;
- tool rows with restrained separators;
- blue hover state with yellow marker.

### Center — Resultado da Análise
- pure white reading surface;
- strongest visual priority;
- compact metallic-blue header with yellow rule;
- deep-blue headings;
- body text in complete paragraphs with generous line-height;
- no table-like presentation.

### Right — Material coletado
- very light cool-blue/steel tint;
- blue note tags;
- yellow left marker on important captured notes;
- compact separators.

## 10. Workspace — outline mode

The outline is a white technical writing surface on a steel canvas.

- Central content width about 960px.
- Major sections use deep-blue headings and a narrow yellow underline/accent.
- Sermon points use white/soft-steel panels with a blue left rail.
- AI suggestion action uses yellow fill with blue text.
- Avoid purple AI gradients.

## 11. Forms

Inputs:
- white background;
- dark blue-gray text;
- 1px steel border;
- blue focus ring plus optional yellow inset marker;
- no heavy shadows.

Labels:
- compact sans-serif;
- medium/bold weight;
- blue-gray tone.

## 12. Buttons

### Primary
Metallic blue gradient + white text.

### High-emphasis / creation
Yellow fill + deep-blue text.

### Secondary
White/steel surface + blue-gray text + steel border.

### Success
Muted green.

### Danger
Red outline/text unless confirmation requires stronger treatment.

## 13. Reading / sermon preview

Preview should look like a clean technical document:
- pale steel outer canvas;
- white page;
- blue headings;
- yellow rules and small accents;
- metadata in a soft steel panel;
- toolbar in metallic blue;
- high-contrast print mode.

## 14. Accessibility

- Body text contrast target: WCAG AA or better.
- Yellow text is never placed directly on white; yellow is primarily fill/rule/marker.
- Yellow buttons use deep-blue text.
- Focus indicators must remain visible.
- Never encode status by color alone.
- Touch targets should remain approximately 40px or larger where practical.

## 15. Responsive behavior

Desktop: retain three-column research workspace.
Tablet: stack columns vertically when horizontal density becomes harmful.
Mobile: single-column reading order and full-width controls.

The protected 54px desktop workspace header geometry must remain intact because automated tests rely on it.

## 16. Do

- Use blue metallic chrome sparingly but visibly.
- Keep content surfaces bright and mostly white.
- Use yellow as a precise accent.
- Make the analysis pane the calmest reading surface.
- Preserve high information density with strong grouping.
- Keep controls visually engineered and consistent.

## 17. Do not

- Do not return to oxblood, parchment, cream, or Reformation Folio styling.
- Do not use dark mode as the default canvas.
- Do not use purple AI gradients.
- Do not use giant rounded SaaS cards.
- Do not use glassmorphism or neon glow.
- Do not imitate automotive logos, stripes, trademarks, or branded fonts.

## 18. Agent instruction

Before changing any visible interface in this repository, read this file. New UI must reuse these tokens and principles. When a local template style conflicts with this document, migrate the local style toward Blue Steel rather than creating another visual dialect.
