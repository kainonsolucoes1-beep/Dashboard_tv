import os
import re
import requests

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _renovar_token_auto() -> str | None:
    env_path = os.path.join(_PROJECT_ROOT, ".env")
    try:
        with open(env_path, "r") as f:
            conteudo = f.read()
        client_id     = re.search(r'CLIENT_ID\s*=\s*["\']([^"\']+)["\']', conteudo).group(1)
        client_secret = re.search(r'CLIENT_SECRET\s*=\s*["\']([^"\']+)["\']', conteudo).group(1)
        refresh_token = re.search(r'REFRESH_TOKEN\s*=\s*["\']([^"\']+)["\']', conteudo).group(1)
        resp = requests.post(
            "https://api.followize.com.br/oauth/token",
            data={
                "grant_type":    "refresh_token",
                "refresh_token": refresh_token,
                "client_id":     client_id,
                "client_secret": client_secret,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        novo_access  = data["access_token"]
        novo_refresh = data["refresh_token"]
        conteudo = re.sub(r'ACCESS_TOKEN\s*=\s*"[^"]*"',  f'ACCESS_TOKEN  = "{novo_access}"',  conteudo)
        conteudo = re.sub(r'REFRESH_TOKEN\s*=\s*"[^"]*"', f'REFRESH_TOKEN = "{novo_refresh}"', conteudo)
        with open(env_path, "w") as f:
            f.write(conteudo)
        return novo_access
    except Exception:
        return None
