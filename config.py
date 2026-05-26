import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

def _get(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

ACCESS_TOKEN  = _get("ACCESS_TOKEN")
REFRESH_TOKEN = _get("REFRESH_TOKEN")
CLIENT_ID     = _get("CLIENT_ID")
CLIENT_SECRET = _get("CLIENT_SECRET")
