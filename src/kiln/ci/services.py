"""PostgreSQL et Redis jetables pour `kiln ci`, comme l'action `actions/services` de kiln.

Ports libres choisis au lancement et conteneurs nommés d'après le commit : deux `kiln ci` (ou la
base de test du poste) ne se croisent jamais. Les conteneurs sont retirés en sortie, échec compris ;
ceux d'un `kiln ci` tué (SIGKILL, fenêtre fermée) portent son PID et le suivant les retire.
"""

import os
import socket
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager

from kiln.ci.jobs import Services
from kiln.shell import KilnError

READY_ATTEMPTS = 30
READY_PAUSE_SECONDS = 2
LOOPBACK = "127.0.0.1"
OWNER_LABEL = "kiln.ci.pid"


@contextmanager
def running_services(services: Services | None, prefix: str) -> Iterator[dict[str, str]]:
    """Lance les bases du job et renvoie DATABASE_URL / REDIS_URL ; les retire en sortie."""
    containers: list[str] = []
    service_env: dict[str, str] = {}
    try:
        if services is not None and services.postgres:
            service_env["DATABASE_URL"] = _start_postgres(services, f"{prefix}-postgres")
            containers.append(f"{prefix}-postgres")
        if services is not None and services.redis:
            service_env["REDIS_URL"] = _start_redis(services.redis, f"{prefix}-redis")
            containers.append(f"{prefix}-redis")
        yield service_env
    finally:
        for container in containers:
            subprocess.run(["podman", "rm", "-f", container], capture_output=True, check=False)


def remove_orphan_containers() -> int:
    """Retire les conteneurs dont le `kiln ci` lanceur est mort ; renvoie leur nombre."""
    listing = subprocess.run(
        ["podman", "ps", "-a", "--filter", f"label={OWNER_LABEL}",
         "--format", f'{{{{.Names}}}} {{{{index .Labels "{OWNER_LABEL}"}}}}'],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    orphans = [
        name
        for name, _, owner in (line.partition(" ") for line in listing.stdout.splitlines())
        if owner.isdigit() and not _is_alive(int(owner))
    ]
    for container in orphans:
        subprocess.run(["podman", "rm", "-f", container], capture_output=True, check=False)
    return len(orphans)


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _start_postgres(services: Services, container: str) -> str:
    port = free_port()
    base = services.base
    _start(
        container,
        port,
        5432,
        ["-e", f"POSTGRES_USER={base}", "-e", f"POSTGRES_PASSWORD={base}_password"],
        ["-e", f"POSTGRES_DB={base}", services.postgres],
    )
    _wait_until_ready(container, ["pg_isready", "-U", base])
    return f"postgres://{base}:{base}_password@localhost:{port}/{base}"


def _start_redis(image: str, container: str) -> str:
    port = free_port()
    _start(container, port, 6379, [], [image])
    _wait_until_ready(container, ["redis-cli", "ping"])
    return f"redis://localhost:{port}/1"


def _start(
    container: str, host_port: int, container_port: int, env: list[str], tail: list[str]
) -> None:
    subprocess.run(["podman", "rm", "-f", container], capture_output=True, check=False)
    command = [
        "podman", "run", "-d", "--name", container, "--label", f"{OWNER_LABEL}={os.getpid()}",
        "-p", f"{LOOPBACK}:{host_port}:{container_port}", *env, *tail,
    ]  # fmt: skip
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise KilnError(f"podman n'a pas lancé {container} : {completed.stderr.strip()}")


def _wait_until_ready(container: str, probe: list[str]) -> None:
    for _ in range(READY_ATTEMPTS):
        probe_run = subprocess.run(["podman", "exec", container, *probe], capture_output=True)
        if probe_run.returncode == 0:
            return
        time.sleep(READY_PAUSE_SECONDS)
    raise KilnError(f"{container} ne répond pas après {READY_ATTEMPTS * READY_PAUSE_SECONDS} s")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_socket:
        probe_socket.bind((LOOPBACK, 0))
        return int(probe_socket.getsockname()[1])
