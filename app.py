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
SHEETS = Sheets(
    spreadsheet_url=st.secrets["spreadsheet_url"],
    sa_info=st.secrets["gcp_service_account"],
)

# ── Состояние сессии
if "auth" not in st.session_state:
    st.session_state.auth = {"ok": False, "email": None, "name": None, "role": None}

# ── Хедер
col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("### 📚 Онлайн‑школа — Личный кабинет")
with col2:
    st.caption("Бесплатное веб‑приложение на Streamlit. Авторизация через Google Sheets · Тесты по биологии, физике, химии, математике и информатике.")

# ── Форма входа

def login_view():
    st.subheader("Вход")
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@example.com")
        submit = st.form_submit_button("Войти")
    if submit:
        user = SHEETS.get_user(email.strip().lower())
        if user and str(user.get("active")).upper() == "TRUE":
            st.session_state.auth = {
                "ok": True,
                "email": user.get("email"),
                "name": user.get("name", "Ученик"),
                "role": user.get("role", "stu"),
            }
            st.success(f"Добро пожаловать, {st.session_state.auth['name']}!")
            st.experimental_rerun()
        else:
            st.error("Доступ не найден. Обратитесь к куратору или подайте заявку.")
            if st.secrets.get("allow_signup", False):
                st.info("Заполните заявку — мы добавим вас в список пользователей.")
                with st.form("signup"):
                    name = st.text_input("Ваше имя")
                    email2 = st.text_input("Ваш email")
                    req = st.text_area("Кратко о себе/класс/город")
    dashboard_view()
