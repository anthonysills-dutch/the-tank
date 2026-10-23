# Self-Test Checks

Do each check on the verdict from the self-test. Each check must be true.

| No. | Check |
|---|---|
| 1 | The verdict has a decision: IN or OUT. |
| 2 | The verdict has a probability of an offer between 0 and 1. |
| 3 | If the decision is IN, the verdict has an amount and an equity percent. If OUT, the verdict has advice. |
| 4 | The verdict has three objections. |
| 5 | The verdict has one hardest question. |
| 6 | The evidence has at least one belief ID from `sharks/cuban.md`. |
| 7 | The evidence has at least one past pitch ID from `precedents/cuban.md` (Type C: "No past pitches available"). |
| 8 | Each quote in the verdict is in `checks/quote-bank.md`, word for word. |
| 9 | The verdict does not say that Mark Cuban (the real person) said or thinks a thing. |
| 10 | The report ends with the notice from `templates/session-report.md`. |

The result is PASS if all ten checks are true. The result is FAIL if one or more checks are false.
