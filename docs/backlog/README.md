# Backlog

What is left to do on kiln, what is done, and what was turned down. **This folder is the
only up-to-date source.**

| File | Content |
|---|---|
| [backlog.md](backlog.md) | **Everything**: the single list ordered by priority, one `T-NN` ticket per thing to do with its type, status and details; at the bottom, the "Done" log |
| [rejected.md](rejected.md) | What was turned down, dropped, or ruled out for good |
| [urgent.md](urgent.md) | What only a human on the team can do (access, payment, decision), one checkbox per action |

An audit writes its dated report next to these files (`audit-<topic>-YYYY-MM-DD.md`) while it
runs, copies its open findings into [backlog.md](backlog.md) (with a pointer to their lines),
then moves to `docs/_archive/YYYY-MM-DD-topic/`. Archives **can be read, but everything in them
is old and must be checked** against the current code; they are never edited.
