# Review of the generated beats (VD4 v2)

The storyboard is `video/storyboard.md` (its "Visual direction (v2)" holds the design plan); this note covers the eight scenes in `compositions/`.

- **Direction.** frontend-design set the plan, and impeccable's craft floor and a critique of every beat checked it. The project has no PRODUCT.md, so the critique ran in this thread, against the user's notes and the craft-floor bans, on rendered frames of every beat. Each frame is an annotated exhibit: a plain headline, the real artifact from a committed file, and its source line. Colour comes from the app's palette; violet appears only where Muse acts. Fira Code is used only for literal data. No glass, glow, chips, stamps, eyebrows or all-caps labels.
- **Data.** No figure is typed into a scene. `index.html` loads `assets/figures.js`, which `video/figures.py` writes after its asserts pass; each scene fills its text from `window.FIG`. B8's state for D3 stays as composition variables (PENDING-DM5).
- **Fixed on review.**
  - The v1 thesis cards (glass panel, dashed "?" chips, an "ALLOWED / BLOCKED" stamp) are replaced by the real call, fact, rule and verdict.
  - "RATIFIED BY A PERSON" was not what the record says. It is replaced by the store entry and the function that ratified it.
  - B0's headline collided with the URL.
  - B9's first per-call timeline had labels that overlapped. It is now a proportional strip plus log rows.
  - B9's source column truncated file paths; it is now wider.
  - Small type was raised to the 28 px floor where it is reading text.
  - Sources now appear with their evidence instead of at the end.
- **Measured.**
  - `npx hyperframes check`: no errors.
  - `impeccable detect --json` on the eight scenes: no findings.
  - Frames of every beat in the rendered rough cut were looked at.
- **Kept warnings.**
  - `film_silent`: silence was requested.
  - `dead_stretch`: deliberate holds of at least 2 s, so the cut still reads when sped up.
  - `text_below_floor`: on the HUD and source lines (16–26 px). These are citations to pause on, not reading text.
  - `line_unread`: on the long price note in B9.
  - `container_overflow`: on B0's push-in, which is clipped by design.
- **Weakest shots.**
  - B7's lower right is empty until the honest run appears at 9 s.
  - B10 is a deliberately plain end card.
  - Fira Code draws `==` as one long rule because of its glyph design, not a ligature; it still reads as `==`.
