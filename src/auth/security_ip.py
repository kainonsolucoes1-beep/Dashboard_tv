import streamlit as st

from config_ips import REDE_INTERNA, USUARIOS_REMOTOS


def get_client_ip() -> str:
    try:
        headers = st.context.headers
        forwarded = headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = headers.get("X-Real-Ip", "")
        if real_ip:
            return real_ip.strip()
        return "desconhecido"
    except Exception:
        return "desconhecido"


def is_ip_interno(ip: str) -> bool:
    return any(ip.startswith(prefixo) for prefixo in REDE_INTERNA)


def usuario_pode_remoto(usuario: str) -> bool:
    return USUARIOS_REMOTOS.get(usuario, False)
