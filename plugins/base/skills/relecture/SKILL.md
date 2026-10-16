---
name: relecture
description: Review a branch's commits and diff before they become public for good - messages, authorship, forbidden trailers, stray files, secrets, fixups to fold - and tidy the history while it can still be rewritten; with `--depot`, review the whole repo before a release (published commits since the last tag, leftover remote branches, worktrees). Run by base:fusion before merging and by base:version before tagging; use also when the user asks whether a branch or the repo is clean, presentable, ready to be seen.
argument-hint: "[branch | --depot]"
---

Branch: `$ARGUMENTS`, otherwise the current branch. Integration branch: the one the project's
`CLAUDE.md` names, otherwise `develop` if it exists, otherwise the default branch of `origin`.

Once merged into the integration branch and pushed, a commit is public forever: anyone reading
the history, a release note or a `git blame` judges the project by it. The branch is the last
place where it can still be fixed. Talk to the user in their language.

## 1. Gather

    git fetch -q --prune origin
    git log --reverse --format='%h%x09%an <%ae>%x09%s%n%b' origin/<integration>..<branch>
    git diff --stat origin/<integration>...<branch>
    git diff origin/<integration>...<branch>

And the conventions to measure against: the project's `CLAUDE.md` (commit rules, Carte du
repo), `CONTRIBUTING.md`, and the last 30 subjects of the integration branch
(`git log --no-merges --format=%s -30 origin/<integration>`): language, scopes, tone.

## 2. Commits

Each one, against the repo's habits:
- **Subject**: Conventional Commits `type(scope): summary` (`!` for a breaking change), in the
  language of the history, under 72 characters, saying what changes rather than how; no
  `wip`, `test`, `oops`, `fix typo`, `update`, `.` or a bare file name.
- **Body and trailers**: no `Co-Authored-By: Claude`, no `Claude-Session:`, no
  « Generated with » line; a breaking change says it (`BREAKING CHANGE:`).
- **Author**: the user's usual identity on this repo (`git config user.name/email`, the
  history), never a placeholder or a machine address; an outside contributor keeps their own.
- **Shape**: small and atomic, one purpose each, only the files of the task. To fold in:
  `fixup!` / `squash!` commits, a commit that fixes or reverts an earlier one of the same
  branch, two commits with the same subject, formatting churn alone after the real change.

## 3. Diff

- No secret or real personal data (`gitleaks git --log-opts=origin/<integration>..<branch>`
  if installed, otherwise read the diff for keys, tokens, `.env`, e-mails, phone numbers).
- No stray file: scratch or debug output, `*.orig`, `*.rej`, `.DS_Store`, a local `.<service>/`
  folder, a large binary, a lockfile changed without its manifest.
- No leftover: conflict markers, `print` / `console.log` of debugging, commented-out code, a
  `TODO` with no ticket, a test skipped without a reason.
- No change outside the task (reformatting of untouched code, an unrelated file).
- What goes with it is there: the Carte du repo updated if a folder or entry point moved, the
  backlog ticket, the docs or `CHANGELOG.md` the project asks for, the tests of the change.

## 4. Tidy

Report first, as a short list: what is fine, what is wrong, the fix proposed for each.

Rewriting the history is allowed only on the branch, never on the integration branch, `main`
or a tag, and only if nobody else builds on it: the branch is not on `origin`
(`git ls-remote --heads origin <branch>` empty), or it is, but it is the user's own branch with
no open PR from someone else. A pushed branch is rewritten only with the user's yes, then
`git push --force-with-lease origin <branch>`. Otherwise, report without rewriting.

Note the current tip (`git rev-parse <branch>`) to give it back if needed, then, from the
branch's worktree, without any interactive command (`GIT_EDITOR=true` before each rebase):
- fold a commit into an earlier one: `git commit --fixup=<sha>` (or keep the existing
  `fixup!`), then `git rebase --autosquash origin/<integration>`;
- reword a commit: `git commit --allow-empty -m "amend! <its current subject>" -m "<new
  message>"`, then the same rebase (`--fixup=reword:` refuses `-m` and opens an editor);
- drop a stray file: `git rm --cached <file>` in a fixup of the commit that added it, and
  the pattern in `.gitignore` if it can come back;
- a secret already pushed: stop, tell the user to revoke it first; rewriting does not
  unpublish it.

After the rewrite: `git diff <old tip> <branch>` is empty unless a file was meant to go, and
the history reads as section 2 asks. Rewriting a published commit is not this skill's job:
say what is wrong and what will prevent it next time (a rule, a hook, a kiln fix via
`base:report-to-kiln`).

## 5. With `--depot`: the whole repo, before a release

Run by `base:version` before the tag: the release note and the tag point to all of this.
- **Published commits** of the release, `git log <previous tag>..<candidate>`: section 2 again.
  They can no longer be rewritten: the release note (`CHANGELOG.md`) is where to say clearly
  what a poor subject hides.
- **Remote branches**: `git branch -r --merged origin/<integration>` (merged, left on
  GitHub), and the others with their last commit date (`git for-each-ref
  --sort=-committerdate refs/remotes/origin --format='%(refname:short) %(committerdate:relative) %(subject)'`):
  abandoned, open PR, in progress. Propose to delete the merged ones and to close or finish
  the abandoned ones; delete nothing on GitHub without the user's yes.
- **Local branches and worktrees** already merged: `base:nettoyage`.
- **Tags**: well formed for the project (`vX.Y.Z`, `-rc.N`), none on a commit outside
  `main` or a release branch.

## 6. Summary

Verdict in one line (clean / tidied / to fix by the user), then what was rewritten (old and new
tip), what is left and why.
