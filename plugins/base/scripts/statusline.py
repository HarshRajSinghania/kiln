#!/usr/bin/env python3
"""Status line commune à tous les dossiers, sur quatre lignes : dépôt, session, à faire, état.

Dans un repo : branche, état git, CI, Vercel, conteneurs, `docs/a-faire/a-faire.md`, chacun
affiché seulement si le repo s'en sert. Hors repo (~/code) : vue d'ensemble des repos du
dessous. Les sources lentes sont lues en cache et rafraîchies en tâche de fond.
"""
import datetime, fcntl, hashlib, json, struct, termios, unicodedata, os, re, shlex, subprocess, sys, time

CACHE = os.path.expanduser("~/.cache/claude-statusline")
R, G, Y, D, X = "\033[31m", "\033[32m", "\033[33m", "\033[2m", "\033[0m"
B, M, C, BOLD = "\033[34m", "\033[35m", "\033[36m", "\033[1m"
SEP = f" {D}│{X} "
JOURS = ("lun", "mar", "mer", "jeu", "ven", "sam", "dim")
INTEGRATION = ("main", "master", "develop")
U = {"second": "s", "minute": "min", "hour": "h", "day": "j", "week": "sem", "month": "mois", "year": "an"}


def sh(*cmd, cwd=None, timeout=2):
    try:
        if cmd[:1] == ("git",):  # jamais de verrou sur l'index : un git interrompu le laisserait derrière lui
            cmd = ("git", "--no-optional-locks") + cmd[1:]
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def cached(name, ttl, cmd, cwd):
    """Renvoie la dernière valeur connue ; relance `cmd` (dans `cwd`) en fond si elle a plus de `ttl` s.

    Une commande en échec ne remplace pas la dernière valeur connue.
    """
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    try:
        age, val = time.time() - os.path.getmtime(path), open(path).read().strip()
    except OSError:
        age, val = 1e9, ""
    lock = path + ".lock"
    if age > ttl and not (os.path.exists(lock) and time.time() - os.path.getmtime(lock) < 60):
        open(lock, "w").close()
        q = shlex.quote
        script = (f"cd {q(cwd)} && ({cmd}) > {q(path + '.tmp')} 2>/dev/null && mv {q(path + '.tmp')} {q(path)};"
                  f" rm -f {q(path + '.tmp')} {q(lock)}; touch {q(path)}")
        subprocess.Popen(["bash", "-c", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    return val


def git_state(path):
    ab = sh("git", "-C", path, "rev-list", "--left-right", "--count", "HEAD...@{u}").split()
    return {
        "name": os.path.basename(path).lstrip("."),
        "branch": sh("git", "-C", path, "branch", "--show-current"),
        "dirty": len(sh("git", "-C", path, "status", "--porcelain").splitlines()),
        "ahead": int(ab[0]) if len(ab) == 2 else 0,
        "behind": int(ab[1]) if len(ab) == 2 else 0,
        "wt": sh("git", "-C", path, "worktree", "list").count("\n"),
    }


def scan(root):
    """Imprime l'état git de chaque repo sous `root` (hors dossiers `_*` et node_modules)."""
    found = []
    for dirpath, dirs, files in os.walk(root):
        if ".git" in dirs or ".git" in files:
            if dirpath != root:
                found.append(dirpath)
                dirs.clear()
                continue
        depth = dirpath[len(root):].count(os.sep)
        dirs[:] = [x for x in dirs if not x.startswith("_") and x != "node_modules" and depth < 2]
    found.sort(key=lambda p: os.path.basename(p).lstrip(".").lower())
    print(json.dumps([git_state(p) for p in found]))


if sys.argv[1:2] == ["--scan"]:
    scan(sys.argv[2])
    sys.exit()

d = json.load(sys.stdin)
# Antigravity CLI (agy) envoie le même format, sauf ses quotas : fraction restante par fenêtre
# (gemini-5h, gemini-weekly), ramenée ici au rate_limits de Claude Code.
if d.get("quota") and not d.get("rate_limits"):
    d["rate_limits"] = {}
    for src, k in (("gemini-5h", "five_hour"), ("gemini-weekly", "seven_day")):
        q = d["quota"].get(src) or {}
        if q.get("remaining_fraction") is not None:
            d["rate_limits"][k] = {
                "used_percentage": 100 * (1 - float(q["remaining_fraction"])),
                "resets_at": time.time() + float(q.get("reset_in_seconds") or 0),
            }
try:  # dernière entrée reçue, pour voir les champs que fournit Claude Code
    json.dump(d, open(os.path.join(CACHE, "input.json"), "w"), indent=1)
except OSError:
    pass
cwd = d.get("workspace", {}).get("current_dir") or d.get("cwd") or os.getcwd()
if re.match(r"[A-Za-z]:[\\/]", cwd):  # appelé depuis Claude Code Windows via wsl.exe
    cwd = sh("wslpath", "-u", cwd) or cwd
repo, state, todo, sess = [], [], [], []  # lignes, affichées dans l'ordre dépôt, session, à faire, état


def opt(main, key):
    """Réglage du repo, posé par `git config statusline.<key> …` (ex. `ci false`, `prod-url https://…`)."""
    return sh("git", "-C", main, "config", "--get", f"statusline.{key}")


top = sh("git", "-C", cwd, "rev-parse", "--show-toplevel")
main = ""
if top:
    main = sh("git", "-C", cwd, "worktree", "list", "--porcelain").split("\n", 1)[0].removeprefix("worktree ")
    key = hashlib.sha1(main.encode()).hexdigest()[:12]
    name = os.path.basename(main).lstrip(".")
    integ = "develop" if sh("git", "-C", cwd, "rev-parse", "-q", "--verify", "origin/develop") else \
        sh("git", "-C", cwd, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").removeprefix("origin/") or "main"

    # ligne 1 : repo, emplacement, branche (rouge sur l'intégration), écart avec l'intégration, fichiers, stash
    st = sh("git", "-C", cwd, "status", "--porcelain=v2", "--branch").splitlines()
    branch = next((l.split()[2] for l in st if l.startswith("# branch.head ")), "")
    branch = "" if branch == "(detached)" else branch
    place = f"{BOLD}{C}{name}{X}" + ("" if top == main else f" {M}wt:{os.path.basename(top)}{X}")
    git = f"{place} {R if branch == integ else G}{branch or 'détachée'}{X}"
    ab = sh("git", "-C", cwd, "rev-list", "--left-right", "--count", f"HEAD...origin/{integ}").split()
    if len(ab) == 2 and ab != ["0", "0"]:
        git += f" {G}↑{ab[0]}{X}{R}↓{ab[1]}{X}"
    files = [l for l in st if not l.startswith("#")]
    add = sum(1 for l in files if l[:1] in "12" and l[2:3] != ".")
    mod = sum(1 for l in files if l[:1] in "12u" and l[3:4] != ".")
    unt = sum(1 for l in files if l.startswith("?"))
    counts = " ".join(f"{col}{s}{n}{X}" for s, n, col in (("+", add, G), ("~", mod, Y), ("?", unt, M)) if n)
    if counts:
        git += f" {counts}"
    gitdir = sh("git", "-C", cwd, "rev-parse", "--absolute-git-dir")
    for marker, label in (("rebase-merge", "REBASE"), ("rebase-apply", "REBASE"), ("MERGE_HEAD", "MERGE"),
                          ("CHERRY_PICK_HEAD", "CHERRY-PICK"), ("REVERT_HEAD", "REVERT"), ("BISECT_LOG", "BISECT")):
        if os.path.exists(os.path.join(gitdir, marker)):
            git += f" {BOLD}{R}{label}{X}"
            break
    if branch and branch != integ:
        if not any(l.startswith("# branch.upstream ") for l in st):
            git += f" {D}non poussée{X}"
        else:
            up_ab = next((l.split()[2:4] for l in st if l.startswith("# branch.ab ")), ["+0", "-0"])
            if up_ab[0] != "+0":
                git += f" {Y}⇡{up_ab[0][1:]}{X}"
    stash = len(sh("git", "-C", cwd, "stash", "list").splitlines())
    if stash:
        git += f" {B}≡{stash}{X}"
    repo.append(git)
    wt = sh("git", "-C", cwd, "worktree", "list").count("\n")
    if wt:
        repo.append(f"{Y}wt×{wt}{X}")
    unmerged = len(sh("git", "-C", cwd, "branch", "--no-merged", f"origin/{integ}").splitlines())
    if unmerged:
        repo.append(f"{M}br×{unmerged}{X} {D}non fusionnées{X}")
    subject = sh("git", "-C", cwd, "log", "-1", "--format=%s")
    if subject:
        repo.append(f"{D}{subject[:36] + ('…' if len(subject) > 36 else '')}{X}")

    # secrets suivis ou en passe de l'être : .env (hors exemples), jetons, clés privées
    secrets = [f for f in sh("git", "-C", top, "ls-files").splitlines()
               if re.search(r"(^|/)\.env(\.[^/]+)?$", f) and not re.search(r"\.(example|sample|template|dist)$", f)
               or re.search(r"(^|/)\.[\w-]+/token$|\.(pem|key|p12)$|(^|/)id_(rsa|ed25519)$", f)]
    if secrets:
        state.append(f"{BOLD}{R}⚠ secret suivi : {secrets[0]}" + (f" +{len(secrets) - 1}" if len(secrets) > 1 else "") + X)

    # ligne 2, partout : marqueurs TODO/FIXME/XXX en commentaire
    todos = cached(f"{key}-todo2", 300, "git grep -I -c -E '(#|//|/\\*|<!--)\\s*(TODO|FIXME|XXX)\\b' -- . ':!docs/_archive'"
                   " | awk -F: '{s+=$NF} END{print s+0}'", main)
    if todos and todos != "0":
        state.append(f"{Y}TODO {todos}{X}")

    # ligne environnement : back et front en prod, chacun avec les commits qui le touchent et ne
    # sont pas encore déployés (une modif de docs ne compte pas). Back : la sonde de santé
    # (`statusline.prod-url`) donne le commit déployé ; front : le dernier déploiement Vercel.
    def deployed(side, name, sha, paths):
        label = f"{D}{side} :{X} {B}{name}" if name != side else side
        if not sha:
            return f"{B}{label}{X} {Y}?{X}"
        late = sh("git", "-C", main, "rev-list", "--count", f"{sha}..origin/{integ}", "--",
                  *[p for p in paths if os.path.exists(os.path.join(main, p))])
        if not late:
            return f"{B}{label}{X} {Y}?{X}"
        return f"{B}{label}{X} {G}✔{X}" if late == "0" else f"{B}{label}{X} {Y}↓{late}{X}"

    def framework(folder, markers, fallback):
        """Nom du framework d'un dossier, reconnu à un fichier qui lui est propre."""
        return next((name for f, name in markers if os.path.exists(os.path.join(main, folder, f))), fallback)

    back_name = framework("backend", (("manage.py", "django"), ("main.py", "fastapi")), "back")
    front_name = framework("frontend", (("nuxt.config.ts", "nuxt"), ("next.config.js", "next"), ("next.config.ts", "next"),
                                        ("svelte.config.js", "svelte"), ("vite.config.ts", "vue")), "front")
    prod = []
    prod_url = opt(main, "prod-url")
    if prod_url:
        try:
            health = json.loads(cached(f"{key}-health", 120, f"curl -s4 -m 5 {shlex.quote(prod_url)}", main) or "{}")
        except ValueError:
            health = {}
        prod.append(deployed("back", back_name, health.get("version", ""), ("backend", "config")))
        if health and health.get("status") != "ok":
            down = [k for k, ok in (health.get("checks") or {}).items() if not ok]
            prod[-1] += f" {BOLD}{R}{health.get('status', '?')}{X}" + (f" {R}{' '.join(down)}{X}" if down else "")
    try:
        vp = json.load(open(os.path.join(main, ".vercel", "project.json")))
        scope = f"--scope {vp['orgId']}"
        paused = cached(f"{key}-vercel", 300, f"vercel api /v9/projects/{vp['projectId']} {scope}"
                        " | python3 -c 'import json,sys; print(json.load(sys.stdin).get(\"paused\", False))'", main)
        front_sha = cached(f"{key}-front", 300, f"vercel api '/v6/deployments?projectId={vp['projectId']}"
                           f"&target=production&state=READY&limit=1' {scope} | python3 -c 'import json,sys;"
                           " print(json.load(sys.stdin)[\"deployments\"][0][\"meta\"][\"githubCommitSha\"])'", main)
        prod.append(deployed("front", front_name, front_sha, ("frontend",)) + (f" {R}⏸ en pause{X}" if paused == "True" else ""))
    except (OSError, ValueError, KeyError):
        pass
    if prod:
        state.append(f" {D}·{X} ".join(prod))

    # CI de l'intégration (sauf `statusline.ci false`)
    if os.path.isdir(os.path.join(main, ".github", "workflows")) and opt(main, "ci") != "false":
        ci = cached(f"{key}-ci", 60, f"gh run list -b {integ} -L 1 --json status,conclusion"
                                     " -q '.[0] | .conclusion // .status'", main)
        state.append(f"{B}CI{X} {integ} " + {"success": f"{G}✔{X}", "failure": f"{R}✘{X}", "cancelled": "⊘"}
                     .get(ci, f"{Y}⏳{X}" if ci else "?"))

    # dépendances à mettre à jour (uv, pnpm), vérifiées une fois par jour en tâche de fond
    deps = []
    for folder in ("", "backend", "frontend"):
        path = os.path.join(main, folder)
        tag = hashlib.sha1(path.encode()).hexdigest()[:8]
        if os.path.exists(os.path.join(path, "uv.lock")):
            n = cached(f"{key}-{tag}-uv", 86400, "uv tree --outdated --depth 1 --frozen | grep -c 'latest:'", path)
            if n and n != "0":
                deps.append(f"uv {Y}{n}{X}")
        if os.path.exists(os.path.join(path, "pnpm-lock.yaml")):
            n = cached(f"{key}-{tag}-pnpm", 86400, "pnpm outdated --format json"
                       " | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))'", path)
            if n and n != "0":
                deps.append(f"pnpm {Y}{n}{X}")
    if deps:
        state.append(f"{D}à mettre à jour :{X} " + " · ".join(deps))

    # serveurs de dev : ports en écoute ouverts par un processus lancé depuis ce repo
    ports = set()
    for l in sh("ss", "-ltnpH").splitlines():
        m = re.search(r":(\d+)\s.*pid=(\d+)", l)
        if not m:
            continue
        try:
            here = os.readlink(f"/proc/{m.group(2)}/cwd")
        except OSError:
            continue
        if here == main or here.startswith(main + "/"):
            ports.add(int(m.group(1)))
    if ports:
        state.append(f"{D}serveurs :{X} " + " ".join(f"{G}:{p_}{X}" for p_ in sorted(ports)))

    # conteneurs podman nommés <repo>-… : en marche / arrêtés
    pods = cached("podman", 30, "podman ps -a --format '{{.Names}} {{.State}}'", main)
    mine = [l.split() for l in pods.splitlines() if l.startswith(name.lower() + "-") and len(l.split()) == 2]
    if mine:
        up = [n.removeprefix(name.lower() + "-") for n, s in mine if s == "running"]
        stopped_pods = len(mine) - len(up)
        state.append(f"{D}conteneurs :{X} {B}podman{X} " + (" ".join(f"{G}{u}{X}" for u in up) if up else f"{D}aucun allumé{X}")
                     + (f" {D}· {stopped_pods} arrêté{'s' if stopped_pods > 1 else ''}{X}" if stopped_pods else ""))

    # éléments restants dans docs/a-faire/a-faire.md : entrées `### AF-NN ·` avant la section
    # « Fait », dont les critiques (section 🔴) ; à défaut, l'ancien format `N. **Titre**`
    try:
        lines = open(os.path.join(top, "docs/a-faire/a-faire.md")).read().splitlines()
        entries, critical, section, states = 0, 0, "", {}
        for l in lines:
            if l.startswith("## "):
                section = l
                if "Fait" in l:
                    break
            elif re.match(r"### [A-Z]+-\d+ ·", l):
                entries += 1
                critical += "🔴" in section
            elif l.startswith("- **État** : "):
                for prefix in ("en cours", "bloqué", "à vérifier"):
                    if l.removeprefix("- **État** : ").startswith(prefix):
                        states[prefix] = states.get(prefix, 0) + 1
        if entries:
            detail = "".join(f" {D}·{X} {col}{states[w]} {label}{X}" for w, label, col in
                             (("en cours", "en cours", C), ("bloqué", "bloquées", R), ("à vérifier", "à vérifier", Y))
                             if states.get(w))
            todo.append(f"{B}à faire{X} {BOLD}{entries}{X}" + (f" {D}·{X} {R}{critical} critiques{X}" if critical else "") + detail)
        else:
            todo_count = sum(1 for l in lines
                       if re.match(r"\s*\d+\.\s+\*\*", l) and "Fait" not in l and "fait le" not in l.lower())
            todo.append(f"{B}à faire{X} {BOLD}{todo_count}{X}")
    except OSError:
        pass
    try:  # cases à cocher de docs/a-faire/urgent.md : ce que seul l'utilisateur peut faire
        urgent = sum(1 for l in open(os.path.join(top, "docs/a-faire/urgent.md")) if l.lstrip().startswith("- [ ]"))
        if urgent:
            todo.append(f"{BOLD}{M}urgent {urgent}{X}")
    except OSError:
        pass
else:
    # hors repo : un mot par repo du dessous, vert s'il est propre et à jour, jaune sinon ;
    # branche en rouge si l'arbre principal a quitté l'intégration
    key = hashlib.sha1(cwd.encode()).hexdigest()[:12]
    try:
        repos = json.loads(cached(f"{key}-repos", 20, f"python3 {shlex.quote(__file__)} --scan {shlex.quote(cwd)}", cwd) or "[]")
    except ValueError:
        repos = []
    wts = 0
    for r in repos:
        s = f"{BOLD}{Y if r['dirty'] or r['ahead'] or r['behind'] else G}{r['name']}{X}"
        if r["branch"] not in INTEGRATION:
            s += f" {R}{r['branch'] or 'détachée'}{X}"
        if r["dirty"]:
            s += f" {Y}~{r['dirty']}{X}"
        if r["ahead"] or r["behind"]:
            s += f" ↑{r['ahead']}↓{r['behind']}"
        repo.append(s)
        wts += r["wt"]
    if wts:
        state.append(f"{Y}wt×{wts}{X}")

# ligne session : modèle, effort, mode de permissions
model = d.get("model", {}).get("display_name", "?")
effort = d.get("effort") or d.get("effort_level") or (d.get("model", {}) or {}).get("effort")
if isinstance(effort, dict):
    effort = effort.get("level")
sess.append(f"{BOLD}{M}{model}{X}" + (f" {C}{effort}{X}" if effort else ""))
if d.get("session_name"):
    sess.append(f"{D}« {d['session_name'][:20]} »{X}")
if d.get("fast_mode"):
    sess[-1] += f" {Y}⚡{X}"
style = (d.get("output_style") or {}).get("name")
if style and style != "default":
    sess.append(f"{C}style {style}{X}")
mode = d.get("permission_mode") or d.get("permissionMode")
if mode:
    sess.append(f"{R}{mode}{X}" if "bypass" in str(mode).lower() else str(mode))

# autres sessions Claude (consigne : une seule à la fois par projet) : dans un repo, celles qui
# tournent dans ce repo ou ses worktrees ; ailleurs, toutes ; et les sessions suspendues
active, stopped = 0, 0
for pid in sh("pgrep", "-x", "claude").split():
    try:
        here = os.readlink(f"/proc/{pid}/cwd")
        state_letter = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[0]
    except OSError:
        continue
    if main and not (here == main or here.startswith(main + "/")):
        continue
    if state_letter == "T":
        stopped += 1
    else:
        active += 1
others = active - 1
if others > 0:
    sess.append(f"{Y}+{others} session{'s' if others > 1 else ''}{X}")
if stopped:
    sess.append(f"{D}⏸{stopped} suspendue{'s' if stopped > 1 else ''}{X}")

# contexte
cw = d.get("context_window") or {}
pct = cw.get("used_percentage")
if pct is None and cw.get("context_window_size"):
    used = sum((cw.get("current_usage") or {}).get(k, 0) or 0
               for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    pct = 100 * used / cw["context_window_size"]
if pct is not None:
    pct = float(pct)
    bar = "▓" * round(pct / 20) + "░" * (5 - round(pct / 20))
    sess.append(f"{R if pct > 80 else Y if pct > 60 else G}{bar} {pct:.0f}%{X}")

# limites d'abonnement (fenêtre de 5 h, semaine), si Claude Code ou agy les fournit
limits = []
for k, label in (("five_hour", "5h"), ("seven_day", "sem")):
    used = ((d.get("rate_limits") or {}).get(k) or {}).get("used_percentage")
    if used is not None:
        used = float(used)
        reset = ((d.get("rate_limits") or {}).get(k) or {}).get("resets_at")
        when = ""
        if reset and used > 50:
            at = datetime.datetime.fromtimestamp(reset)
            when = f" {D}↻{at:%Hh%M}{X}" if k == "five_hour" else f" {D}↻{JOURS[at.weekday()]}{X}"
        limits.append(f"{B}{label}{X} {R if used > 80 else Y if used > 50 else G}{used:.0f}%{X}{when}")
if limits:
    sess.append(" · ".join(limits))

# cache de prompt : taux de réussite, froid s'il a expiré
pc = d.get("prompt_cache") or {}
if pc.get("hit_ratio") is not None:
    ratio = 100 * float(pc["hit_ratio"])
    sess.append(f"{B}cache{X} " + (f"{R if ratio < 70 else Y if ratio < 90 else G}{ratio:.0f}%{X}"
                                   if pc.get("warm", True) else f"{C}froid{X}"))

# durée et lignes de la session (le coût n'apparaît que sans limites d'abonnement)
c = d.get("cost") or {}
if c:
    mins = int((c.get("total_duration_ms") or 0) / 60000)
    cost = "" if limits else f"{Y}${c.get('total_cost_usd', 0):.2f}{X} · "
    sess.append(f"{cost}{B}{mins // 60}h{mins % 60:02d}{X}"
                f" · {G}+{c.get('total_lines_added', 0)}{X}/{R}-{c.get('total_lines_removed', 0)}{X}")

for line in (state, todo):  # hauteur constante : chaque ligne existe même vide
    if not line:
        line.append(f"{D}—{X}")

def terminal_columns():
    """Largeur du terminal de la session : celui du processus `claude` parent (le script n'en a pas)."""
    pid = os.getppid()
    for _ in range(6):
        try:
            if open(f"/proc/{pid}/comm").read().strip() == "claude":
                with open(f"/proc/{pid}/fd/0", "rb") as tty:
                    return struct.unpack("hhhh", fcntl.ioctl(tty, termios.TIOCGWINSZ, b"\0" * 8))[1]
            pid = int(open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            return 0
    return 0


def visible_width(text):
    plain = re.sub(r"\033\[[0-9;]*m", "", text)
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 0 if unicodedata.combining(ch) else 1 for ch in plain)


# chaque ligne : son nom tout à gauche, puis son contenu centré dans la place qui reste
# (marge de Claude Code déduite quand la largeur du terminal est connue)
LABELS = (("dépôt", repo), ("session", sess), ("tâches", todo), ("environnement", state))
label_width = max(len(name) for name, _ in LABELS) + 2
columns = terminal_columns() - 4 - label_width
out = []
for name, line in LABELS:
    if line:
        body = SEP.join(line)
        out.append(f"{BOLD}{D}{name.upper():<{label_width}}{X}" + " " * max(0, (columns - visible_width(body)) // 2) + body)
# une ligne blanche entre chaque et une à la fin : U+2800 (blanc braille), qu'aucun nettoyage ne
# prend pour un espace, car Claude Code retire les lignes vides ou faites d'espaces
print("\n\u2800\n".join(out) + "\n\u2800", end="")
