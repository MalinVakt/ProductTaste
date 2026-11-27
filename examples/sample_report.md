> **Illustration only.** This report was written by hand to show the output
> format on the sample data in `sample_data/`. It was not produced by a live
> run. Run `python -m halkvakt_pm` with an API key to get a real one.

# Halkvakt feedback triage, 2026-11-27

18 items from bug_tracker, email, social; 8 issues, 3 items set aside.

## Overview

The dominant problem is late push alerts on Android since the 3.4 update: it
shows up in every channel, includes the most-engaged public complaint, and two
paying users mention cancelling. A duplicate Premium charge needs a refund and a
root-cause check. Demand for warnings on cycle paths and sidewalks is the
clearest product request. A Business-plan fleet customer wants an API and ties it
to a January renewal.

## Priority list

| # | Priority | Type | Issue | Reports | Channels |
|---|---|---|---|---|---|
| 1 | P0 | Bug | Android push alerts arrive hours late since 3.4 | 5 | bug_tracker, social, email |
| 2 | P1 | Bug | Premium renewal charged twice | 2 | bug_tracker, email |
| 3 | P1 | Bug | iOS crash on Map tab with location permission off | 1 | bug_tracker |
| 4 | P2 | Request | Warnings for cycle paths and sidewalks | 3 | social, email |
| 5 | P2 | Request | Public API for Business / fleet customers | 1 | email |
| 6 | P3 | Bug | Wrong municipality label for Upplands Väsby | 1 | bug_tracker |
| 7 | P3 | Request | Home-screen widget showing current risk level | 1 | social |
| 8 | P3 | UX | Unreadable grey text in dark mode settings | 1 | bug_tracker |

## Rationale

### 1. [P0] Android push alerts arrive hours late since 3.4

**What:** Android users get slippery-road alerts 2 to 4 hours after the warning is issued; iOS is unaffected.

**Why P0:** This breaks Halkvakt's core job, a warning before you travel. Five independent reports across all three channels (bugs-101, bugs-105, social-tw-9002, social-tw-9005, support-email-004) on Pixel, Samsung and OnePlus, all pointing at the 3.4 release. bugs-101 has 14 votes. social-tw-9002 describes sliding into a ditch and has 388 likes and 120 reposts, so this is already a public reputation risk. A Premium user (support-email-004) threatens to cancel before winter peaks. Would drop to P1 only if it turns out to affect a single device family.

**Next step:** Diff notification scheduling and FCM priority between 3.3 and 3.4; ship a hotfix and reply publicly to tw-9002 once out.

**Confidence:** high

### 2. [P1] Premium renewal charged twice

**What:** A customer was charged 49 kr twice on 21 November for the yearly renewal.

**Why P1:** Payment errors cost trust and money directly, and the user threatens to cancel. Only one customer has reported it (bugs-106 and support-email-002 are the same person), so it is not P0, but double charges usually affect more people than report them. Raise to P0 if the billing logs show other duplicates on 21 November.

**Next step:** Refund today, then query billing for other duplicate renewals that day.

**Confidence:** medium

*(...remaining issues follow the same shape...)*

## Set aside

`social-tw-9003` (spam), `support-email-003` (marketing email), `social-tw-9004` (praise, no ask)
