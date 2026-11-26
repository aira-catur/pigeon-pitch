#!/usr/bin/env python3
"""Pigeon Pitch, One Line -- entry builder (competition #190).

Writes ONE one-line elevator pitch to ``entry.txt`` inside
``MAKEFUN_OUTPUT_DIR`` (default ``/output``), UTF-8, 1-200 characters,
with NO trailing newline.

The pitch: a city pigeon gives investors an elevator pitch for its
startup.  The house judge compares entries pairwise, in this order:
  1. on subject (pigeon -> investors -> its startup),
  2. funnier, with a real joke that lands (not a mild pun / description),
  3. original and surprising,
  4. the pigeon's own voice and city life,
  5. tight writing, every word earning its place, <= 200 chars.

This program holds a pool of candidate pitches, scores every candidate
with a transparent heuristic model of those five criteria (in the
judge's own priority order), and writes only the winner.

JURI KEJAM (harsh-judge) REVIEW LOG
-----------------------------------
Round 1 (draft pool, before first run):
  * Cut candidates that were pure dead puns ("Coo-ber", "coo-pon"):
    the brief says a good pun counts when it lands and a dead one does
    not, so pun-only lines score low on the joke axis by design.
  * Cut straight descriptions with no twist (a delivery service that
    is just a delivery service): no final-clause reversal, no points.
  * Penalised any line without an explicit investor address or funding
    ask: criterion 1 is checked first and loses to any on-subject
    pitch, so the ask must be unmistakable.
  * Penalised lines whose joke could be told by any animal: the pitch
    must be impossible for anyone but a city pigeon (statues, crumbs,
    rooftops, guano, homing instinct).
Round 2 (after the first local run; winner was the security-camera
  line at 171 chars -- good twist, three real flaws):
  * Its opener, "Coo is my pitch deck", never names the investors.
    Criterion 1 is checked first, so the final pool's leaders address
    investors in the first clause, out loud.
  * The scorer rewarded any short closing clause; it now rewards a
    closing clause that carries a CONSEQUENCE (an "or ..." threat or
    a "before ..." deadline), because that is where the joke lands.
  * Three new candidates were written for this round (statue-covering
    "proof of distribution", hawk-proof parcel post, baguette-fuelled
    freight) and the security-camera line was rewritten tighter with
    the investor address moved to the front. Dead-pun and
    description-only lines stay penalised exactly as in round 1.
"""

import os
import re
import sys

MAX_CHARS = 200

# ---------------------------------------------------------------- pool
# Each candidate is a single line of English, <= 200 characters.
CANDIDATES = [
    "Forget drones: my startup delivers parcels by pigeon - no batteries, no traffic, paid in crumbs, and we already know where everyone lives. Seed round? Literally. Bring seeds.",
    "Investors, I poop on statues for free. Imagine what I will do to your competitors' billboards on subscription. GuanoAds: precision targeting, never missed a monument yet.",
    "Investors, meet my startup: we rent out pigeons as living security cameras. We already film every statue, sandwich and affair in this city. Fund us, or the footage leaks.",
    "Every statue in this city is covered in our work, and critics call it vandalism. We call it proof of distribution. Fund GuanoAds: ten million impressions, all organic.",
    "I deliver a parcel in four minutes, work for crumbs, and have never leaked one to a hawk. Fund PigeonPost: the cloud, but with feathers and far better uptime.",
    "Your drone startup needs batteries, licences and luck. Mine needs a baguette. Fund FlockFreight: rooftop to park bench in nine minutes, tips accepted in seeds.",
    "I run the city's oldest aerial network: ten thousand pigeons, zero charging cables, salaries in breadcrumbs. Fund Homing, the only GPS that also judges your outfit.",
    "Google Maps loses signal in tunnels. I never do. My startup sells homing instinct as a service - invest now, before the drones learn to coo and unionise.",
    "Every day I drop free samples on your city's statues. That is not vandalism, that is marketing reach. Fund Guano Gold, premium fertiliser with a billion loyal depositors.",
    "You pay for billboards nobody reads. My flock reads every park bench in town. CrumbBoard: hyperlocal ads, delivered at beak height, pecked fresh daily. Seed funding, please.",
    "Investors, I have sat on the mayor's statue for six years. I know where this city sleeps, eats and cheats. Fund Roost Intelligence before a seagull does.",
    "My startup turns breadcrumbs into a currency: one crumb, one vote, one tiny revolution. The park bench is our stock exchange. Buy in early, the pigeons are already rich.",
    "Drones need charging, permits and apologies. I need a crust. Fund FlockFreight: same-day delivery anywhere a statue can see, which in this city is everywhere.",
    "I am not a rat with wings. I am a drone with ancestors. My startup licenses 5,000 years of flight data to delivery firms - invest, and own the sky retroactively.",
    "Your office window? I have pooped on it twice, so I know your security is weak. Fund Perch Patrol, rooftop surveillance by the only staff who never blink on camera.",
    "Investors, my startup matches lonely statues with pigeons who will sit on them forever. Eternal companionship, zero maintenance, one tasteful deposit per visit.",
    "Traffic jams are a ground problem. My flock moves 40,000 lunches a day above them, paid in fries. Fund SkyCrumb before the crows copy us and charge more.",
    "I know every rooftop, shortcut and dropped sandwich in this city, and I work for crumbs. Fund PigeonPost: the last courier who never asks for a raise or a charger.",
    "Forget focus groups: my flock has watched humans queue, cry and propose in this park for decades. Fund Bench Insights, consumer data with feathers and zero cookies.",
    "My startup sells silence: one trained pigeon sits outside your rival's office and coos at 5 a.m. daily. No refunds. Fund CooOps, corporate warfare, softly.",
    "Investors, the city feeds my team for free and calls it littering. Zero payroll, infinite crumbs, total sky coverage. Fund Flock - your only competitor is gravity.",
]

# ------------------------------------------------------------- scoring
INVESTOR_WORDS = ("investor", "fund", "seed", "invest", "buy in", "back us")
STARTUP_WORDS = ("startup", "we sell", "we rent", "we deliver", "we turn",
                 "we put", "we match", "licenses", "service", "currency",
                 "ads", "patrol", "insights", "network", "freight")
PIGEON_WORDS = ("pigeon", "coo", "crumb", "statue", "flock", "rooftop",
                "guano", "poop", "beak", "feather", "homing", "perch",
                "park bench", "wings", "seagull", "crow")
# Concrete, visual, slightly absurd specifics tend to land as jokes.
JOKE_TEXTURE = ("statue", "crumb", "guano", "sandwich", "mayor", "affair",
                "footage", "fries", "littering", "gravity", "ancestors",
                "cookies", "ex", "wife", "deposit", "unionise", "5 a.m.")
DEAD_PUNS = ("coo-ber", "coo-pon", "coo-peration", "cooops")
FILLER = ("very", "really", "just", "actually", "basically", "amazing",
          "incredible", "revolutionary")


def score_pitch(text):
    """Score one candidate on the judge's five criteria, in order.

    Returns a tuple ordered exactly like the brief, so plain tuple
    comparison mirrors the judge's 'first differing criterion decides'
    rule: (on_subject, funny, original, pigeon_voice, tight).
    """
    low = text.lower()
    words = re.findall(r"[a-z0-9']+", low)

    # 1. On subject: pigeon speaker + investor ask + a startup offer.
    on_subject = 0
    on_subject += 2 if any(w in low for w in INVESTOR_WORDS) else 0
    on_subject += 2 if any(w in low for w in STARTUP_WORDS) else 0
    on_subject += 1 if ("my " in low or "our " in low or "i " in low) else 0
    on_subject += 1 if "pigeon" in low or "flock" in low or "coo" in low else 0

    # 2. Funny: a setup that turns. A colon/dash pivot or a short final
    # reversal clause, plus concrete comic texture; dead puns cost.
    funny = 0
    funny += sum(1 for w in JOKE_TEXTURE if w in low)
    if ":" in text or " - " in text or ". " in text:
        funny += 2
    tail = text.rsplit(". ", 1)[-1]
    if 0 < len(tail) <= 60 and tail != text:
        funny += 2  # a short closing twist, not a trailing summary
    tail_low = tail.lower()
    if tail_low.startswith(("or ", "before ", "fund us, or")):
        funny += 3  # closing consequence: the joke actually lands
    if "investor" in low[:40]:
        funny += 1  # the room is addressed before the joke starts
    funny -= 3 * sum(1 for p in DEAD_PUNS if p in low)

    # 3. Original: rare-in-pool vocabulary and an unusual premise word.
    original = len({w for w in words if len(w) >= 7})

    # 4. Pigeon voice and city life.
    voice = sum(1 for w in PIGEON_WORDS if w in low)

    # 5. Tight: shorter is tighter, filler and repetition cost.
    tight = 200 - len(text)
    tight -= 8 * sum(1 for f in FILLER if f" {f} " in f" {low} ")
    tight -= 4 * (len(words) - len(set(words)))

    return (on_subject, funny, original, voice, tight)


def pick_winner(candidates):
    valid = [c for c in candidates
             if 1 <= len(c) <= MAX_CHARS and "\n" not in c and c.strip()]
    if not valid:
        raise SystemExit("no valid candidate in pool")
    return max(valid, key=score_pitch)


def main():
    winner = pick_winner(CANDIDATES)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.txt")
    # newline="" plus no trailing "\n": the file is exactly the pitch.
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(winner)
    print(f"winner ({len(winner)} chars): {winner}")
    print(f"wrote: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
