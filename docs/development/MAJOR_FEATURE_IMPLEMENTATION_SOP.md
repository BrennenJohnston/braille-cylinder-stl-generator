# Adding a Major Feature

A checklist for implementing significant features in this project. Based on lessons learned from the Card Thickness Preset System (December 2025).

Large, multi-phase work now follows Brennen's AI planning workflow template, which is kept outside this repository; this checklist still applies inside each phase.

## Before you start

1. Read `docs/specifications/SPECIFICATIONS_INDEX.md` to understand what already exists
2. Read any related specification documents
3. Check `settings.schema.json` for existing parameters — they may already cover what you need
4. Plan which files need changes

## Key files

Changes to the UI typically touch these files:

| What | Where |
|------|-------|
| Frontend (the whole UI) | `public/index.html` |
| Data models | `app/models.py` |
| Validation | `app/validation.py` |
| Settings schema | `settings.schema.json` |
| Geometry spec (what the server sends) | `app/geometry_spec.py`, with `app/geometry/gears.py`, `interpoint.py` and `version2.py` |
| 3D model (built in the browser) | `static/workers/csg-worker-manifold.js` (cylinders) |

## Implementation checklist

### Code
- [ ] Add UI controls with proper HTML semantics and ARIA attributes
- [ ] Add event listeners (both `change` and `click` for radio buttons)
- [ ] Add localStorage persistence with try-catch (private browsing breaks without it), for design settings only: no text or braille a person types is ever stored (`tests/test_text_privacy.py`)
- [ ] Restore saved values on page load
- [ ] Update `settings.schema.json` if adding parameters
- [ ] Update `app/models.py` if backend needs new fields

### Documentation
- [ ] Create a specification doc in `docs/specifications/` if the feature is substantial
- [ ] Update `docs/specifications/SPECIFICATIONS_INDEX.md`
- [ ] Update related specs if the feature changes existing behavior

### Testing
- [ ] Feature works in Chrome, Firefox, and Safari
- [ ] Feature works with localStorage disabled (private browsing)
- [ ] Keyboard navigation works
- [ ] Existing features still work
- [ ] Screen reader announces the new controls correctly

## Common mistakes

- **Skipping the specs**: Reading existing specs before coding prevents naming conflicts and duplicate work. This saved hours on the thickness preset feature.
- **No error handling on localStorage**: Wrap all `localStorage.setItem()` calls in try-catch.
- **Missing ARIA attributes**: All form controls need labels. Radio groups need `role="radiogroup"`.
