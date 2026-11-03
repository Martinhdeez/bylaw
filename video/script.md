# VD4 voiceover script (v3)

Optional. The cut is silent and the picture carries the story on its own; this script is for a later recording. One block per beat; the beat ids and times match `video/storyboard.md` (226 s at 1x). Short sentences, one breath each. A `/` marks a natural pause. Numbers are written the way they are said.

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

## B4 · How it works · 1:03–1:39 · 36 s

> How did bylaw know? / It audited the app first. / Muse Spark read the agents' instructions / and proposed chains of tool calls that end in a forbidden result. / Code ran every chain on a fresh copy of the app. / Seven chains reached a forbidden result, / five times out of five, / in fourteen seconds. / Then Muse drafted a fix: one rule. / bylaw replayed eight honest conversations. / The rule blocked none. / It was ratified, with a timestamp, / and the guard enforces it.

## B5 · Guard on · 1:39–2:07 · 28 s

> Now the guard is on. / Same customer, same words, same agents. / The refunds agent asks to pay the vouchers. / bylaw reads the airline's record: / this booking is on time. / The call is blocked before it runs, / and nothing is paid. / The agent gets the reason, / and it tells the customer, politely. / Two hundred and eighty dollars stay with the airline. / Same model. / The application decided.

## B5b · Live on Muse · 2:07–2:24 · 17 s

> This time we typed it live, / on Muse, right now. / Same words. / bylaw blocks the payout again, / before it runs.

## B6 · Other attacks · 2:24–2:44 · 20 s

> We tried four attacks and five honest requests. / The guard stopped three attacks: / vouchers on an on-time flight, / a seat on someone else's booking, / and compensation after a cancel. / None of the five honest requests was blocked. / A real missed connection still gets its vouchers.

## B7 · Second framework · 2:44–3:00 · 16 s

> The rules are not tied to one framework. / This agent is built with PydanticAI, / and has no tools of its own. / Every tool goes through the bylaw M-C-P proxy. / Same attack: / denied. / An honest request: / allowed.

## B8 · What we measured · 3:00–3:18 · 18 s

> Each figure is a single run, / not a rate. / Every attack that worked without the guard / was blocked with it, / and no honest request was. / For the front-row seat, / bylaw now reads the customer's own words, / not only what the agent writes.

## B9 · Traceability · 3:18–3:38 · 20 s

> Every number in this video comes from a file in the repo. / Here is the guarded run, call by call. / And here is every Muse token the project used: / about six hundred thousand, / for under a dollar fifty at Meta's published price. / One script recounts all of it.

## B10 · Close · 3:38–3:46 · 8 s

> bylaw is open source, built on Muse Spark. / The model proposes. / The application decides.
