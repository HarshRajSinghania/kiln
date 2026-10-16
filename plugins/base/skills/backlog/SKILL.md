---
name: backlog
description: Pick the next ticket from docs/backlog/backlog.md, add a ticket (bug, improvement, idea, task), or record a ticket as started or done, in a repo that tracks its work this way. Use when the user asks what to do next, wants to note something to do or an idea, or after starting or finishing a ticket.
argument-hint: "[T-NN | new <what> | start T-NN | done T-NN]"
---

In a repo without `docs/backlog/backlog.md`, say so and offer to set it up: a kiln repo has it
by default (`kiln update` brings it to an older repo, and moves an old `docs/a-faire/` there);
elsewhere, copy the structure of kiln's template (`template/docs/backlog/`).

`docs/backlog/backlog.md` is the **only** up-to-date source: everything is there, ordered by
priority (🔴 critical, 🟠 important, 🟡 normal, ⚪ background), with the "✅ Done" log at the
bottom. `docs/backlog/rejected.md` lists what was turned down. **Read the "How to use" section
at the top of the file first**: it wins if it differs from what follows.

A ticket: a `### T-NN · Title` heading, then the lines `- **Type**:`, `- **Status**:`,
`- **Opened**: YYYY-MM-DD`, `- **Effort**: … · **Owner**: … · **Due**: …`, `- **Origin**: …`,
then the details (`- [ ]` boxes). Types: `bug`, `improvement`, `idea`, `task`. Statuses:
`todo`, `in progress — branch <name>, since YYYY-MM-DD`, `blocked — waiting for <who or what>`,
`to verify — <where>`. Overview:
`grep -E '^(## |### T-|- \*\*Status)' docs/backlog/backlog.md`.

`docs/_archive/` is **read** when a ticket points to lines of an archived report, but
everything in it is old: check it against the current code before acting. Never edit an
archived report.

**No argument**: propose the next 3 tickets in section order (critical first), following the
north star in the header and skipping `blocked` tickets and those reserved for outside
contributors (**Owner**: `contributor — #NN`, skill `base:good-first-issues`); for each, the ID, one sentence, the
effort, and the owner. List separately the blocked tickets waiting for the user themselves.
Quickly check in the code that the ticket is not already done (the locations quoted are hints,
often stale).

**With an ID**: show the full ticket (and the archive lines it quotes), find the files involved
in the current code, propose a short plan, then create the branch (in a worktree, skill
`base:worktree`) and set the status to `in progress — branch …`.

**`new <what>`**: add a ticket with the "next free" ID from the "How to use" section (then
increment it), the type that fits (`idea` when nothing is decided yet), `todo`, today's date as
`Opened`, in the section matching its priority (⚪ background for an idea still to explore).

**`start T-NN`**: set the **Status** line to `in progress — branch <name>, since YYYY-MM-DD`.

**`done T-NN`**: remove the ticket from its section and add at the **top** of the "✅ Done" log a
line `- **YYYY-MM-DD** · T-NN · Title — what was done (branch) · opened YYYY-MM-DD`. A
half-done ticket stays in place: tick the steps done, write what is left. Keep the style and
tone of the file.

An ID is never reused. Changes are committed on the work branch, never on the integration
branch. Never copy a ticket into `rejected.md` without an explicit decision from the user.
