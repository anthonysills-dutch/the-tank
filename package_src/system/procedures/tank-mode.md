# Procedure: Tank Mode

Use this procedure when the user says "Tank mode". In Tank mode, the Sharks compete for the deal, and the founder negotiates.

Tank mode starts after a full session. The independent verdicts are always the first round. Tank mode does not replace them.

## 1. Rules for Tank mode

1. Each Shark move comes from that Shark file, that Shark verdict, and the offer board only.
2. A Shark does not see the reasoning or the objections of a different Shark. It sees only the offers on the board.
3. Use method A or method B from `procedures/run-a-pitch.md` for each move. One Shark moves at a time.
4. The Host does not make a move for a Shark. The Host does not change a move.
5. Do not change an OUT to IN to make a deal happen. Only step 3.3 lets a Shark enter late.
6. Use the "Negotiation record" section of each Shark file to set the terms. Do not go far from it without a clear reason.
7. Write each move in the log. A move that is not in the log did not occur.

## 2. Make the opening board

1. If the user did not run a full session for this pitch, do `procedures/run-a-pitch.md` first.
2. Copy `templates/tank-log.md`.
3. Write each IN verdict as an offer on the board: Shark, amount, equity, royalty, loan, and conditions.
4. If no Shark is IN, write "No offers" on the board. Go to step 6.

## 3. Shark rounds

Do two rounds. In each round, the Sharks move in order of probability, from the highest to the lowest.

1. Give each Shark on the board these items: its Shark file, its own verdict, and the current board.
2. The Shark selects one move:
   - HOLD: keep the offer.
   - IMPROVE: make the offer better for the founder. Give the new terms.
   - PARTNER: make a joint offer with one other Shark on the board. Give the joint terms.
   - DROP: remove the offer. Give one reason.
3. In round 1 only, a Shark that is OUT with the signal ABOVE can enter. It makes an offer at its usual terms from the deal record. All other OUT Sharks stay out.
4. A PARTNER move is a proposal. The other Shark accepts or refuses it in its next move. If it refuses, the first Shark keeps its old offer.
5. A Shark can PARTNER only with a Shark that is in its "Partners in shared deals" list.
6. After each move, update the board. Write the move and one sentence of reason in the log.

## 4. Founder turn

1. Show the board to the user.
2. Tell the user the three choices:
   - ACCEPT: take one offer as it is.
   - COUNTER: give new terms to one Shark (amount, equity, or royalty).
   - WALK AWAY: take no offer.
3. Record the choice of the user in the log.

## 5. Counters

1. Give the counter to that Shark only, with its Shark file, its verdict, and the board.
2. The Shark selects one response:
   - ACCEPT: the deal is done at the counter terms.
   - REJECT: the offer stays as it was.
   - FINAL: the Shark gives its last terms. The founder accepts these terms or loses this offer.
3. A Shark rejects a counter at a higher valuation than the founder asked for at the start.
4. The founder can make three counters in total. After the third counter, the founder must accept an offer or walk away.
5. After each response, do step 4 again.

## 6. Close the session

1. Write the result in the log: DEAL or NO DEAL.
2. For a DEAL, write the final terms and each Shark in the deal.
3. Write the "Lessons" section. List what made Sharks drop, and what made Sharks compete.
4. Write the notice at the end. Copy it exactly from the template.
5. Save the log as `tank-log.md` in the session folder (step 6 of `procedures/run-a-pitch.md`).
