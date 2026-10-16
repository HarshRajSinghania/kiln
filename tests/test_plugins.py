import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
PLUGINS = [plugin["name"] for plugin in MARKETPLACE["plugins"]]
# Ce qui renvoie à un skill (`base:fusion`) : la charte et les fichiers générés, les plugins
# eux-mêmes, les messages de la commande, la documentation.
CITING = ("template", "plugins", "src", "README.md", "README.fr.md", "CONTRIBUTING.md", "CLAUDE.md")
TEXT_SUFFIXES = {".md", ".py", ".jinja", ".json", ".yml", ".yaml", ".toml", ".sh", ".txt"}


def citing_files() -> list[Path]:
    files = []
    for name in CITING:
        path = ROOT / name
        if path.is_file():
            files.append(path)
        else:
            files += [f for f in path.rglob("*") if f.is_file() and f.suffix in TEXT_SUFFIXES]
    return files


def test_every_cited_skill_exists() -> None:
    cited = re.compile(rf"\b({'|'.join(map(re.escape, PLUGINS))}):([a-z][a-z0-9-]*)")
    missing = {
        f"{match[1]}:{match[2]} ({path.relative_to(ROOT)})"
        for path in citing_files()
        for match in cited.finditer(path.read_text(errors="ignore"))
        if not (ROOT / "plugins" / match[1] / "skills" / match[2] / "SKILL.md").is_file()
    }
    assert sorted(missing) == []


def test_each_skill_is_named_after_its_folder() -> None:
    # Ligne à ligne et non en YAML : Claude Code accepte « Sans CI : elle… » sans guillemets.
    for skill in (ROOT / "plugins").glob("*/skills/*/SKILL.md"):
        front_matter = skill.read_text().split("---")[1]
        assert re.search(rf"^name: {re.escape(skill.parent.name)}$", front_matter, re.M), skill
        assert re.search(r"^description: \S", front_matter, re.M), skill
