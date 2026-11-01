# Review of the generated beats (VD4)

The storyboard is `video/storyboard.md`; this note covers the six scenes in `compositions/`.

- **Creative calls.** One visual grammar for the whole film: Bylaw's indigo ground with faint ruled lines (the "policy as a record" identity), Fira Sans and Fira Code as in the web app. Muse acts in violet, rounded and dashed (proposals with "?", "Drafted by Muse Spark"). The application acts in white or verdict colours, square, with stamps that land hard (`power4.in`, scale 1.5–1.8 to 1). The receipt is paper, the only light object, so the $280 reads first. B4 is one diagram that grows: five nodes drawn faint, each lit when the voice names it. No icons, no glow, no counters.
- **Not built.** No 3D, no camera moves, no transitions between beats: the beats are cut together in the edit with the app captures between them.
- **Measured.** `npx hyperframes check`: 0 errors. Every figure on screen is checked by `video/figures.py`. Snapshots of every scene at its reveals were looked at, and so were the rendered beats and the rough cut.
- **Kept warnings.** `film_silent` (the beats are silent by request; music is in the rough cut). `text_below_floor` on footnotes and source paths (20–22 px Fira Code): they are citations, not reading text, and 1080p on a desktop screen reads them. `dead_stretch` where a line holds under the voice (`data-hold` on the deliberate ones).
- **Fixed on review.** RATIFIED stamp overlapped "blocked 0 / 8": moved left. "no tools of its own" collided with the connector: moved right. The Agents SDK card was drawn feeding the MCP proxy, which is wrong (the SDK demo is guarded in process): that line was removed and the card says "guarded in process by the same ratified rules".
- **Weakest shot.** B2's two panels are clean but static once landed; with more time, the violet proposals would travel into the Application panel and get stamped there. B7's first 4 s show only two cards.
- **Timing.** Reveals are placed for about 2.4 words a second. The final cut stretches or compresses each generated beat (0.8–1.25x) to the real voice (`video/ASSEMBLY.md`).
