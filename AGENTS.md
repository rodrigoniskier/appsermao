# AGENTS.md

## Interface rule

Before creating or modifying any visible interface, read `DESIGN.md`.

`DESIGN.md` is the source of truth for visual language, typography, color, spacing,
component geometry, responsive behavior, and accessibility.

Do not introduce a second visual system locally in templates. Prefer shared CSS tokens and
shared component classes. Preserve existing behavior unless the task explicitly requests a
functional change.

## Project-specific guardrails

- Keep the sermon-preparation experience text-first.
- Preserve the three-column research workspace on desktop and its responsive stacking.
- Do not reintroduce the former dark blue/gold dashboard aesthetic.
- Do not use purple/blue gradients to label AI features.
- Avoid decorative religious imagery; the visual identity is editorial/scholarly.
- Maintain keyboard focus visibility and readable contrast.
