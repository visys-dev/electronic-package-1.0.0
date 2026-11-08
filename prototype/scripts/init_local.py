"""Create local secrets and a development CA without installing system trust."""

from pathlib import Path
import os
import secrets
import subprocess

root = Path(__file__).resolve().parents[1]
env = root / ".env"
if not env.exists():
    values = {
        "COMPOSE_PROJECT_NAME": "coursework-support-" + secrets.token_hex(4),
        "DB_NAME": "coursework",
        "DB_USER": "coursework_app",
        "APP_ORIGIN": "https://localhost:8443",
    }
    for name in [
        "DB_PASSWORD",
        "DB_OWNER_PASSWORD",
        "DEMO_REQUESTER_PASSWORD",
        "DEMO_SPECIALIST_PASSWORD",
        "DEMO_COORDINATOR_PASSWORD",
        "DEMO_ADMIN_PASSWORD",
        "DEMO_OTHER_PASSWORD",
    ]:
        values[name] = secrets.token_urlsafe(24)
    fd = os.open(env, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("".join(f"{k}={v}\n" for k, v in values.items()))
tls = root / ".local" / "tls"
tls.mkdir(parents=True, exist_ok=True)
private = root / ".local" / "ca"
private.mkdir(exist_ok=True, mode=0o700)


def openssl(*args):
    subprocess.run(
        ["openssl", *map(str, args)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


if not (tls / "server.crt").exists():
    if not (tls / "ca.crt").exists():
        openssl(
            "req",
            "-x509",
            "-newkey",
            "rsa:3072",
            "-nodes",
            "-keyout",
            private / "ca.key",
            "-out",
            tls / "ca.crt",
            "-days",
            "365",
            "-subj",
            "/CN=Coursework Local CA",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
            "-addext",
            "keyUsage=critical,keyCertSign,cRLSign",
        )
        (private / "ca.key").chmod(0o600)
    openssl(
        "req",
        "-new",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        tls / "server.key",
        "-out",
        private / "server.csr",
        "-subj",
        "/CN=localhost",
    )
    ext = private / "server.ext"
    ext.write_text(
        "subjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n"
    )
    openssl(
        "x509",
        "-req",
        "-in",
        private / "server.csr",
        "-CA",
        tls / "ca.crt",
        "-CAkey",
        private / "ca.key",
        "-CAcreateserial",
        "-CAserial",
        private / "serial",
        "-out",
        tls / "server.crt",
        "-days",
        "90",
        "-extfile",
        ext,
    )
    # The non-root container needs read access; the parent .local directory is private.
    (tls / "server.key").chmod(0o644)
(root / ".local").chmod(0o700)
print(
    "Local .env and localhost TLS files ready. System trust was not modified. Secrets were not printed."
)
