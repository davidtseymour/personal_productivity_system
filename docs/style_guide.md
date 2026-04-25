# Style Guide

## Imports

- Follow PEP 8 import grouping in all Python files:
  1. Standard library
  2. Third-party packages
  3. Local (`src...`) imports
- Keep imports alphabetized within each group.
- Keep imports at the top of the module unless there is a specific, documented reason for local import placement.

## Function Typing

- All top-level functions in `src/` must include type annotations for every parameter and the return value.
- Callback registration functions (for example `register_*_callbacks`) must be fully typed.
- Callback handler functions (nested functions decorated with `@app.callback`) are exempt from mandatory full typing.
- Nested helper functions outside callback handlers should be fully typed.
- Prefer concrete types where stable (for example `dbc.Container`, `str`, `int`, `dict[str, Any]`); use broader types only when necessary.

## Layout Structure (Dash + Bootstrap)

- Use one page-level `dbc.Container` as the root for each page module.
- Build visible page sections using `dbc.Row` + `dbc.Col`.
- Keep non-visual infrastructure components outside layout grid structure:
  - `dcc.Store`
  - toasts
  - modals
- For input-heavy pages, prefer:
  - page root = `dbc.Container`
  - form content nested in `dbc.Form`

## Spacing

- Use row-oriented spacing as the default.
- Apply vertical spacing to section rows (for example `className="mb-3"` on `dbc.Row`), not to child components.
- Keep child components margin-neutral unless a local micro-adjustment is needed for inline alignment.

## Sizing Units

- Prefer `rem` for reusable layout sizing (widths, heights, spacing) so UI scales with typography and browser zoom.
- Keep `px` for precision-critical cases:
  - 1px borders/dividers
  - exact icon/button hit-target dimensions where visual precision is intentional
