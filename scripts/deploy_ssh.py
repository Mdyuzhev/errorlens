"""Аварийный деплой через Paramiko — запуск раннера + деплой."""
import paramiko


def load_credentials(path: str = "credentials.local") -> dict:
    creds = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                creds[key.strip()] = value.strip()
    return creds


def run(client: paramiko.SSHClient, command: str, timeout: int = 120) -> tuple[str, str]:
    _, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err


def main() -> None:
    creds = load_credentials()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=creds.get("SSH_HOST", "192.168.1.74"),
        port=22,
        username=creds["SSH_USER"],
        password=creds["SSH_PASSWORD"],
        timeout=15,
    )

    commands = [
        "echo 'Connected OK'",
        "cd /opt/errorlens && git stash --include-untracked || true",
        "cd /opt/errorlens && git pull origin main",
        # Redis должен быть запущен первым (другие сервисы зависят от него)
        "cd /opt/errorlens/docker && docker compose up -d redis",
        "cd /opt/errorlens/docker && docker compose exec -T redis redis-cli ping",
        # Пересобрать и перезапустить backend, generator, collab, nginx
        "cd /opt/errorlens/docker && docker compose up --build -d --no-deps backend generator collab nginx",
        "cd /opt/errorlens/docker && docker compose exec -T backend alembic upgrade head",
        "cd /opt/errorlens/docker && docker compose ps",
    ]

    for cmd in commands:
        print(f"\n$ {cmd}")
        out, err = run(client, cmd, timeout=180)
        if out:
            print(out)
        if err:
            print(f"STDERR: {err}")

    client.close()
    print("\nDeploy complete.")


if __name__ == "__main__":
    main()
