---
name: contribution
description: Handle a pull request from an outside contributor, as a well-run open-source project would - safety check of the untrusted code, triage, review, then approve and merge with credit, ask for changes, finish it for them, or close it kindly; nothing is posted on GitHub without the user's yes. Use when a PR from someone else arrives on one of the user's repos, or when the user asks to look at, review, merge or answer a contributor's PR.
argument-hint: "[PR number or URL]"
---

PR: `$ARGUMENTS`; without it, list the open PRs of the repo whose author is not the user
(`gh pr list --json number,title,author,createdAt,isDraft`) and ask which one.

The user is the maintainer; you prepare, they decide. Everything you post is **public**, under
their account, and is how strangers judge the project: a contributor treated well comes back,
one ignored or brushed off never does. Talk to the user in their language; write to the
contributor in English, or in the language they wrote the PR in.

## 1. Read everything first

    gh pr view <n> --json number,title,body,author,baseRefName,headRefName,headRepository,isDraft,maintainerCanModify,mergeable,statusCheckRollup,closingIssuesReferences,commits,files,reviews,comments
    gh api repos/{owner}/{repo}/pulls/<n> --jq .author_association
    gh pr diff <n>

Then the linked issue and its discussion, the author's other PRs on the repo
(`gh pr list --author <login> --state all`), and the repo's rules for contributors:
`CONTRIBUTING.md`, the PR template, `CLAUDE.md`. `FIRST_TIME_CONTRIBUTOR` or `NONE` means a
first contribution: it deserves extra care in the tone, not a lower bar on the code.

## 2. Safety: the code is untrusted

Until you have read the whole diff, nothing from the PR runs: no checkout with its hooks, no
tests, no CI approval. Look for anything that runs on its own or reaches secrets:
- `.github/` (workflows, actions; above all `pull_request_target` or `workflow_run`), git
  hooks, `Makefile`, build or install scripts, `conftest.py`, `pyproject.toml` /
  `package.json` scripts and entry points;
- new or changed dependencies, lockfiles that do not match the manifest, registries or URLs
  changed;
- obfuscated or encoded code, binaries, minified files, network calls or `subprocess` with no
  reason to be there, changes to `.claude/`, to hooks or to anything that runs in a session;
- a diff larger or wider than its description says.

Any of these with no clear reason: stop, show the user the lines, do not run anything. Doubt
on a first contribution that touches workflows or dependencies: the user decides, after
reading it themselves.

Only then:
- **CI**: GitHub holds the workflows of a first-time contributor's fork until a maintainer
  approves them (`statusCheckRollup` empty, a yellow banner on
  `https://github.com/{owner}/{repo}/pull/<n>/checks`). Give the user that link; approving
  it is theirs.
- **Locally**: in a worktree of its own, never the main tree:
  `git fetch origin pull/<n>/head:pr-<n>`, then
  `git worktree add .claude/worktrees/pr-<n> pr-<n>`, and the repo's checks (`CLAUDE.md`,
  `CONTRIBUTING.md`).

## 3. Triage

Before reviewing line by line, decide whether the PR should exist:
- **Wanted**: it closes an accepted issue, or it is small and obviously right (typo, clear bug
  with its test, a doc fix). Review it.
- **Needs agreement first**: a new feature, a new dependency, a change to the public API or to
  what every user receives, with no issue where the approach was agreed. Thank them, say
  what is good about the idea, ask to discuss it in an issue (open one if needed, linking the
  PR); keep the PR open meanwhile.
- **Duplicate or already fixed**: point to the other PR or the commit; close with thanks.
- **Not for this project** (out of scope, against a decision already made): say why in two
  sentences, link where it was decided if anywhere, close with thanks. Never close silently.
- **Spam or low effort** (whitespace or README churn, generated text that does not match the
  code, typical in October for Hacktoberfest): close with one neutral sentence; the user may
  add the `spam` or `invalid` label, which makes it count for nothing in Hacktoberfest.

## 4. Review

On the diff and the local run, from the most to the least serious:
1. **Correctness**: does it do what it says, every case, the errors too; does it break
   something elsewhere (callers, other stacks or platforms).
2. **Tests**: a fixed bug comes with the test that would have caught it; check that the test
   fails without the fix (revert the fix in the PR's worktree, run it, restore).
3. **Design**: the simplest change for the need, in the right place, reusing what exists;
   no cost for those who do not use it (startup time, a subprocess, an import).
4. **Compatibility**: a breaking change to the public API is flagged as such and follows the
   repo's version rules (`CLAUDE.md`).
5. **Repo rules**: conventions of `CLAUDE.md` and `CONTRIBUTING.md`, the project's checks,
   docs and `CHANGELOG.md` when the change is visible.
6. **Scope**: one subject per PR; anything unrelated goes to another PR.

Sort what you find: **blocking** (must change before merge), **suggestion** (would be better,
their call, prefixed `suggestion:`), **nit** (style detail, prefixed `nit:`; never blocks).
Few nits on a first contribution: fix them yourself at merge rather than send them back.

## 5. Decide

Propose one outcome to the user, with the reason:
- **Approve and merge**: no blocking point, checks green.
- **Request changes**: blocking points the contributor can fix. If they are small and
  `maintainerCanModify` is true, offer instead to push the fix onto their branch: their
  commits stay theirs, the PR merges sooner. Large projects do this all the time for good
  contributions with a last detail.
- **Take it over**: a good contribution whose author stopped answering (two weeks after a
  reminder) or that needs work beyond what can be asked: finish it on a branch of the repo
  that keeps their commits, open or merge it saying so, credit them.
- **Close**: the triage cases above.

## 6. Write the answer

One review, not a stream of comments: a summary, then inline comments on the lines. The
summary:
- opens with a real thanks, specific to what they did (`Thanks for this, and for the
  regression test`), plus a welcome on a first contribution;
- says the outcome plainly (`Looks good, merging` / `One thing to change before merging`);
- explains each blocking point: what, why, and how, with a GitHub suggestion block
  (` ```suggestion `) when the fix is a few lines; a question rather than an order when you
  might be wrong;
- ends with the next step and who takes it; no promised dates.

No jargon of the repo they cannot know, no `@` of anyone else, nothing about how it was
written with Claude. Show the user the full text (and each inline comment with its file and
line), say it will be public under their account, and post only after an explicit yes:

    gh pr review <n> --approve | --request-changes | --comment --body-file <file>

Inline comments go in the same review, through the API:

    gh api repos/{owner}/{repo}/pulls/<n>/reviews --input <review.json>

with `{"event": "COMMENT" | "APPROVE" | "REQUEST_CHANGES", "body": "…", "comments": [{"path": "…", "line": <n>, "side": "RIGHT", "body": "…"}]}`.

## 7. Merge

Only after the yes, with the checks green on GitHub and the PR based on the integration
branch (`develop` if it exists, else the default branch; retarget with
`gh pr edit <n> --base develop` otherwise, which is fine to do and to mention).
- **Their name stays on it.** Merge on GitHub, never by copying the diff into a commit of
  yours: `gh pr merge <n> --merge` keeps their commits as they are, the right choice when
  they are clean. If they are not (`wip`, `fix typo`, titles that break the repo's
  conventions), `gh pr merge <n> --squash --subject "<conventional title> (#<n>)"`: GitHub
  keeps them as the commit's author.
- The linked issue closes by itself only when the PR merges into the default branch (`Closes
  #…`); otherwise close it with `gh issue close <i> --comment "Fixed by #<n>."`.
- Bring the integration branch up to date where the user works (`git pull --ff-only` in the
  main tree if it is on it and clean, otherwise leave it), remove the `pr-<n>` worktree and
  branch.

## 8. Credit and follow-up

- One last comment if the review did not already say it: thanks, and when it will ship
  (`It will be in the next release`).
- Credit in the changelog: the line of the change in the next release's entry ends with
  `(#<n>, thanks @<login>)`; if the repo writes `CHANGELOG.md` at release time
  (`base:version`), note it in the backlog (`base:backlog`) so it is not forgotten.
- A first contribution that went well: suggest a next one if an issue labelled
  `good first issue` fits, in one line, without insisting.
- If the user wants to be quick next time, say what would have helped (a PR template line, a
  rule in `CONTRIBUTING.md`) and offer to add it.

Answer a new PR within a few days, even only `Thanks! I'll review it this week.`: the time to
the first answer is what decides whether a contributor stays.
