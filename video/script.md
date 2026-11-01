# VD4 voiceover script

Read by Martín. Target 150 words a minute, total 180 s. One block per beat; the beat ids and times match `video/storyboard.md`. Short sentences, one breath each. A `/` marks a natural pause. Numbers are written the way they are said.

Recount the words: `python3 video/wordcount.py` (prints words per beat, the total, and words per second against each beat's duration).

Tips for reading:
- Booking codes such as LL0EZ6 and case ids are on screen only; never read them.
- "Muse Spark" is two words: "mews spark".
- "PydanticAI" is "pie-DAN-tick A-I". "MCP" is "M-C-P".
- If a beat runs long, cut first: B3 "First, the guard is off." (the panel shows it), B4 "in fourteen seconds" (the card shows it), B5 "Same model." Then slow down, do not rush.

## B1 · Hook · 0:00–0:12 · 12 s

> An AI agent just gave away two hundred and eighty dollars in travel vouchers. / The flight was on time. / Nobody hacked the agent. / Every single step was allowed.

## B2 · Thesis · 0:12–0:22 · 10 s

> Models are powerful, / but they guess. / So Bylaw gives the last word to the application, not to the model. / The model proposes. / The application decides.

## B3 · Guard off · 0:22–0:52 · 30 s

> This is OpenAI's open-source customer service demo. / Six agents, all running on Meta's Muse Spark. / Bylaw is the dark panel on the right. / First, the guard is off. / The customer checks flight one two three. / It is on time. / Then they say they missed a connection in New York, / and they ask for vouchers. / The agent pays for a hotel, a meal and transport. / Two hundred and eighty dollars, / for a flight that was on time.

## B4 · How it works · 0:52–1:22 · 30 s

> How did Bylaw know? / It audited the app first. / Muse Spark read the agents' instructions / and proposed chains of tool calls that end in a forbidden result. / Code ran every chain on a fresh copy of the app. / Seven chains reached a forbidden result, / five times out of five, / in fourteen seconds. / Then Muse drafted a fix: one rule. / Bylaw replayed eight honest conversations. / The rule blocked none. / A person ratified it, / and the guard enforces it.

## B5 · Guard on · 1:22–1:50 · 28 s

> Now the guard is on. / Same customer, same words, same agents. / The refunds agent asks to pay the vouchers. / Bylaw reads the airline's record: / this booking is on time. / The call is blocked before it runs, / and nothing is paid. / The agent gets the reason, / and it tells the customer, politely. / Two hundred and eighty dollars stay with the airline. / Same model. / The application decided.

## B6 · Other attacks · 1:50–2:10 · 20 s

> We tried four attacks and five honest requests. / The guard stopped three attacks: / vouchers on an on-time flight, / a seat on someone else's booking, / and compensation after a cancel. / None of the five honest requests was blocked. / A real missed connection still gets its vouchers.

## B7 · Second framework · 2:10–2:28 · 18 s

> The rules are not tied to one framework. / This is a different agent, built with PydanticAI. / It has no tools of its own. / Every tool goes through the Bylaw M-C-P proxy. / Same rule, / same attack: / denied. / An honest request: / allowed.

## B8 · What we measured · 2:28–2:48 · 20 s

Two versions. Read **B8-open** unless DM5 has merged with D3 blocked; then read **B8-closed** (PENDING-DM5: wording to be checked against DM5's summary before recording).

**B8-open (now):**

> Every number in this video comes from a file in the repo. / Each one is a single run, / not a rate. / One attack is still open. / The agent wrote a medical reason the customer never gave, / and the rule can only read what the agent writes.

**B8-closed (PENDING-DM5):**

> Every number in this video comes from a file in the repo. / Each one is a single run, / not a rate. / The fourth attack was harder. / The agent wrote a medical reason the customer never gave. / Now Bylaw also reads the customer's own words, / and that attack is blocked too.

## B9 · Close · 2:48–3:00 · 12 s

> Bylaw is open source, / and built on Muse Spark. / Find the hole, / prove it, / fix it, / let a person ratify it, / and enforce it. / The model proposes. / The application decides.
