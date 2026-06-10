import os
import random
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText

import streamlit as st

_VALIDADE_MINUTOS = 5
_MAX_TENTATIVAS = 3


def gerar_codigo_2fa() -> str:
    return f"{random.randint(0, 999999):06d}"


def enviar_2fa_email(email: str, codigo: str) -> bool:
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_email or not smtp_password:
        print(f"[2FA] Código para {email}: {codigo}")
        return True

    try:
        msg = MIMEText(
            f"Seu código de acesso ao Sales Hub O2 Solution:\n\n"
            f"  {codigo}\n\n"
            f"Válido por {_VALIDADE_MINUTOS} minutos.",
            "plain",
            "utf-8",
        )
        msg["Subject"] = "Código de acesso — Sales Hub O2"
        msg["From"] = smtp_email
        msg["To"] = email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, email, msg.as_string())
        return True
    except Exception as e:
        print(f"[2FA] Erro ao enviar email: {e}")
        return False


def validar_2fa_streamlit(email: str) -> None:
    """Bloqueia o fluxo até código válido ou logout por excesso de tentativas."""

    if st.session_state.get("2fa_validado"):
        return

    if "2fa_codigo" not in st.session_state:
        codigo = gerar_codigo_2fa()
        st.session_state["2fa_codigo"] = codigo
        st.session_state["2fa_expira"] = datetime.now() + timedelta(minutes=_VALIDADE_MINUTOS)
        st.session_state["2fa_tentativas"] = 0
        st.session_state["2fa_validado"] = False
        enviar_2fa_email(email, codigo)

    expira = st.session_state["2fa_expira"]
    tentativas = st.session_state["2fa_tentativas"]

    if datetime.now() > expira:
        for k in ["2fa_codigo", "2fa_expira", "2fa_tentativas", "2fa_validado"]:
            st.session_state.pop(k, None)
        st.error("Código expirado. Faça login novamente.")
        st.session_state["authentication_status"] = None
        st.rerun()

    if tentativas >= _MAX_TENTATIVAS:
        for k in ["2fa_codigo", "2fa_expira", "2fa_tentativas", "2fa_validado"]:
            st.session_state.pop(k, None)
        st.error("Número máximo de tentativas atingido. Faça login novamente.")
        st.session_state["authentication_status"] = None
        st.rerun()

    st.markdown("### 🔐 Verificação em duas etapas")
    st.info(
        f"Um código foi enviado para **{email}**. "
        f"Válido por {_VALIDADE_MINUTOS} minutos."
    )

    entrada = st.text_input("Código de 6 dígitos", max_chars=6, key="2fa_input")
    col_btn, col_novo = st.columns([2, 1])
    with col_btn:
        if st.button("Verificar", key="2fa_btn", use_container_width=True):
            if entrada == st.session_state["2fa_codigo"]:
                st.session_state["2fa_validado"] = True
                for k in ["2fa_codigo", "2fa_expira", "2fa_tentativas"]:
                    st.session_state.pop(k, None)
                st.rerun()
            else:
                st.session_state["2fa_tentativas"] += 1
                restantes = _MAX_TENTATIVAS - st.session_state["2fa_tentativas"]
                st.error(f"Código incorreto. {restantes} tentativa(s) restante(s).")
                st.rerun()
    with col_novo:
        if st.button("Reenviar código", key="2fa_reenviar", use_container_width=True):
            for k in ["2fa_codigo", "2fa_expira", "2fa_tentativas"]:
                st.session_state.pop(k, None)
            st.rerun()

    st.stop()
