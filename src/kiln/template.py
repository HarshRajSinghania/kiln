"""Accès au modèle Copier : source par défaut et révision suivie."""

import os

DEFAULT_TEMPLATE_SOURCE = "https://github.com/antoine-tena/kiln.git"
TEMPLATE_SOURCE_VARIABLE = "KILN_TEMPLATE"
# Révision d'un modèle local ou explicite (développement de kiln) : son dernier commit.
LOCAL_TEMPLATE_REVISION = "HEAD"


def template_source(explicit_source: str | None) -> str:
    """Source du modèle : option, puis variable d'environnement, puis dépôt GitHub."""
    if explicit_source:
        return explicit_source
    return os.environ.get(TEMPLATE_SOURCE_VARIABLE, DEFAULT_TEMPLATE_SOURCE)


def template_revision(source: str) -> str | None:
    """Le modèle publié se prend à sa dernière version (None : Copier choisit le tag le plus
    récent) ; un modèle local ou explicite, à son dernier commit."""
    return None if source == DEFAULT_TEMPLATE_SOURCE else LOCAL_TEMPLATE_REVISION
