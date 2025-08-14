import json
import time
from datetime import datetime, timezone
from typing import Dict, List

import streamlit as st

from sheets_backend import Sheets
from tests_core import load_subjects_from_sheet, render_test_form

st.set_page_config(page_title=st.secrets.get("app_title", "Онлайн‑школа"), page_icon="📚", layout="wide")

# ── Стили (минимальный фирменный вид)
CUSTOM_CSS = """
<style>
.main .block-container{max-width:1100px}
.kpi-card{border-radius:16px; padding:16px; box-shadow:0 2px 10px rgba(0,0,0,.06);}
.small{opacity:.8; font-size:0.9rem}
.fullwidth > div[data-baseweb="select"]{width:100%}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Инициализация Sheets клиента
# ── Инициализация Sheets клиента (с защитой от отсутствующих secret'ов)
sa = st.secrets.get("gcp_service_account")
url = st.secrets.get("spreadsheet_url")

# Debug-режим: включается параметром ?debug=1 или тумблером в сайдбаре
qp = getattr(st, "query_params", {})
DEBUG = False
try:
    DEBUG = ("debug" in qp and str(qp.get("debug", "1")).lower() not in ("0","false"))
except Exception:
    pass
DEBUG = st.sidebar.toggle("Debug", value=DEBUG, help="Показать служебную диагностику")

# Показать какие ключи Secrets доступны (без значений)
with st.sidebar:
    st.caption("🔐 Secrets keys detected:")
    try:
        st.code("
".join(sorted(map(str, st.secrets.keys()))))
    except Exception:
        st.code("(no secrets)")

if not sa or not url:
    st.error("Не настроены секреты: gcp_service_account и/или spreadsheet_url.")
    with st.expander("Как это исправить?"):
        st.markdown(
            """
1. В Streamlit Cloud → **Manage app → Settings → Secrets** вставьте:
```toml
spreadsheet_url = "https://docs.google.com/spreadsheets/d/XXXXXXXXXXXX/edit"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "SERVICE-ACCOUNT@PROJECT.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```
2. Откройте доступ (Editor) к этой Google‑таблице для `client_email` из секрета.
3. Нажмите **Reboot app**.
"""
        )
    st.stop()

# Пробуем подключиться к таблице и вывести диагностику
