import json
from datetime import datetime, timezone
from typing import Dict, List

import streamlit as st

from sheets_backend import Sheets
from tests_core import load_subjects_from_sheet, render_test_form

st.set_page_config(page_title=st.secrets.get("app_title", "Онлайн‑школа"), page_icon="📚", layout="wide")

# ── Стили (минимальный аккуратный вид)
CUSTOM_CSS = """
<style>
.main .block-container{max-width:1100px}
.kpi-card{border-radius:16px; padding:16px; box-shadow:0 2px 10px rgba(0,0,0,.06);}
.small{opacity:.8; font-size:0.9rem}
.fullwidth > div[data-baseweb="select"]{width:100%}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Инициализация Sheets клиента (без debug и сайдбара)
sa = st.secrets.get("gcp_service_account")
url = st.secrets.get("spreadsheet_url")
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
2. Дайте доступ **Editor** к Google Sheet для `client_email`.
3. Нажмите **Reboot app**.
"""
        )
    st.stop()

try:
    SHEETS = Sheets(spreadsheet_url=url, sa_info=sa)
except Exception:
    st.error("Не удалось подключиться к Google Sheets (проверьте доступ и URL).")
    st.stop()

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
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()
            return
        else:
            st.error("Доступ не найден. Обратитесь к куратору или подайте заявку.")
            if st.secrets.get("allow_signup", False):
                st.info("Заполните заявку — мы добавим вас в список пользователей.")
                with st.form("signup"):
                    name = st.text_input("Ваше имя")
                    email2 = st.text_input("Ваш email")
                    req = st.text_area("Кратко о себе/класс/город")
                    send = st.form_submit_button("Отправить заявку")
                if send:
                    SHEETS.append_row("signup", [datetime.now(timezone.utc).isoformat(), name, email2, req])
                    st.success("Заявка отправлена. Мы свяжемся с вами по email.")

# ── Домашняя страница после входа

def dashboard_view():
    a = st.session_state.auth
    st.success(f"Вы вошли как {a['name']} ({a['email']})")

    # Карточки
    colA, colB, colC = st.columns(3)
    with colA:
        st.markdown("<div class='kpi-card'><b>Статус</b><br><span class='small'>Входные тесты доступны</span></div>", unsafe_allow_html=True)
    with colB:
        total_results = SHEETS.count_results(a["email"]) or 0
        st.markdown(f"<div class='kpi-card'><b>Сдано тестов</b><br><span class='small'>{total_results}</span></div>", unsafe_allow_html=True)
    with colC:
        st.markdown("<div class='kpi-card'><b>Домашки</b><br><span class='small'>Скоро</span></div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("Входные тесты")

    subjects = [
        ("biology", "🧬 Биология"),
        ("physics", "🧲 Физика"),
        ("chemistry", "⚗️ Химия"),
        ("math", "➗ Математика"),
        ("cs", "💻 Информатика"),
    ]

    data = load_subjects_from_sheet(SHEETS)

    tabs = st.tabs([label for _, label in subjects])

    for i, (code, label) in enumerate(subjects):
        with tabs[i]:
            questions = data.get(code, [])
            if not questions:
                st.warning("Вопросы пока не добавлены. Откройте лист tests и заполните.")
                continue
            st.caption("Ответьте на вопросы, затем нажмите \"Отправить\".")
            score, total, answers = render_test_form(code, questions)
            if score is not None:
                # Запись результата
                SHEETS.append_row(
                    "results",
                    [
                        datetime.now(timezone.utc).isoformat(),
                        a["email"],
                        code,
                        score,
                        total,
                        json.dumps(answers, ensure_ascii=False),
                    ],
                )
                st.success(f"Результат сохранён: {score} / {total}")

# ── Маршрутизация
if not st.session_state.auth["ok"]:
    login_view()
else:
    dashboard_view()
