"""`kiln ci` : la CI du `ci.yml` rejouée sur le poste, verdict en note git sur le commit."""

from kiln.ci.runner import require_known_jobs, run_local_ci, show_verdict

__all__ = ["require_known_jobs", "run_local_ci", "show_verdict"]
