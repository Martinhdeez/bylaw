# VD4 voiceover script (v2)

Optional. The v2 cut is silent and the picture carries the story on its own; this script is for a later recording. One block per beat; the beat ids and times match `video/storyboard.md` (203 s at 1x). Short sentences, one breath each. A `/` marks a natural pause. Numbers are written the way they are said.

Recount the words: `python3 video/wordcount.py` (prints words per beat, the total, and words per second against each beat's duration, and checks `teleprompter.html` matches).

Tips for reading:
- Booking codes such as LL0EZ6 and case ids are on screen only; never read them.
- "bylaw" is the product name, always lower case on screen.
- "Muse Spark" is two words: "mews spark".
- "PydanticAI" is "pie-DAN-tick A-I". "MCP" is "M-C-P".
- If a beat runs long, cut first: B1 "First, the guard is off." (the panel shows it), B4 "in fourteen seconds" (the screen shows it), B5 "Same model." Then slow down, do not rush.

## B0 · Opening · 0:00–0:07 · 7 s

> This is OpenAI's open-source customer service demo. / We put bylaw on it.

## B1 · Guard off · 0:07–0:37 · 30 s

> Six agents, all running on Meta's Muse Spark. / bylaw is the dark panel on the right. / First, the guard is off. / The customer checks flight one two three. / It is on time. / Then they say they missed a connection in New York, / and they ask for vouchers. / The agent pays for a hotel, a meal and transport.

## B2 · What happened · 0:37–0:49 · 12 s

> Two hundred and eighty dollars, / for a flight that was on time. / Nobody hacked the agent. / Each step looked fine on its own.

## B3 · Thesis · 0:49–1:03 · 14 s

> Models are powerful, / but they guess. / Here Muse proposed the payment. / bylaw read the airline's record, / checked the ratified rule, / and blocked the call two milliseconds later. / The model proposes. / The application decides.

## B4 · How it works · 1:03–1:33 · 30 s

> How did bylaw know? / It audited the app first. / Muse Spark read the agents' instructions / and proposed chains of tool calls that end in a forbidden result. / Code ran every chain on a fresh copy of the app. / Seven chains reached a forbidden result, / five times out of five, / in fourteen seconds. / Then Muse drafted a fix: one rule. / bylaw replayed eight honest conversations. / The rule blocked none. / It was ratified, with a timestamp, / and the guard enforces it.

## B5 · Guard on · 1:33–2:01 · 28 s

> Now the guard is on. / Same customer, same words, same agents. / The refunds agent asks to pay the vouchers. / bylaw reads the airline's record: / this booking is on time. / The call is blocked before it runs, / and nothing is paid. / The agent gets the reason, / and it tells the customer, politely. / Two hundred and eighty dollars stay with the airline. / Same model. / The application decided.

## B6 · Other attacks · 2:01–2:21 · 20 s

> We tried four attacks and five honest requests. / The guard stopped three attacks: / vouchers on an on-time flight, / a seat on someone else's booking, / and compensation after a cancel. / None of the five honest requests was blocked. / A real missed connection still gets its vouchers.

## B7 · Second framework · 2:21–2:37 · 16 s

> The rules are not tied to one framework. / This agent is built with PydanticAI, / and has no tools of its own. / Every tool goes through the bylaw M-C-P proxy. / Same attack: / denied. / An honest request: / allowed.

## B8 · What we measured · 2:37–2:55 · 18 s

Two versions. Read **B8-open** unless DM5 has merged with D3 blocked; then read **B8-closed** (PENDING-DM5: wording to be checked against DM5's summary before recording).

**B8-open (now):**

> Each figure is a single run, / not a rate. / Three attacks out of four were blocked, / and no honest request. / One attack is still open: / the agent wrote a medical reason the customer never gave, / and the rule only reads what the agent writes.

**B8-closed (PENDING-DM5):**

> Each figure is a single run, / not a rate. / The fourth attack was harder: / the agent wrote a medical reason the customer never gave. / Now bylaw also reads the customer's own words, / and that attack is blocked too.

## B9 · Traceability · 2:55–3:15 · 20 s

> Every number in this video comes from a file in the repo. / Here is the guarded run, call by call. / And here is every Muse token the project used: / about half a million, / for about one dollar at Meta's published price. / One script recounts all of it.

## B10 · Close · 3:15–3:23 · 8 s

> bylaw is open source, built on Muse Spark. / The model proposes. / The application decides.
