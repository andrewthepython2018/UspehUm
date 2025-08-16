import json
from datetime import datetime, timezone

import streamlit as st

from sheets_backend import Sheets
from tests_core import load_subjects_from_sheet, render_test_form

st.set_page_config(page_title=st.secrets.get("app_title", "Онлайн‑школа УспехУм"), page_icon="📚", layout="wide")

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
@@ -102,101 +101,81 @@ def login_view():
            st.error("Доступ не найден. Обратитесь к куратору или подайте заявку.")
            if st.secrets.get("allow_signup", False):
                # Покажем форму заявки на следующем рендере
                st.session_state.signup_visible = True
                st.session_state.signup_email = email_clean

    # Форма заявки на доступ — рендерится независимо от нажатия кнопки входа
    if st.secrets.get("allow_signup", False) and st.session_state.signup_visible:
        st.info("Заполните заявку — мы добавим вас в список пользователей.")
        with st.form("signup_form"):
            name = st.text_input("Ваше имя")
            email2 = st.text_input("Ваш email", value=st.session_state.signup_email)
            req = st.text_area("Кратко о себе/класс/город")
            send = st.form_submit_button("Отправить заявку")
        if send:
            try:
                SHEETS.append_row(
                    "signup",
                    [datetime.now(timezone.utc).isoformat(), name, email2, req],
                )
                st.success("Заявка отправлена. Мы свяжемся с вами по email.")
                st.session_state.signup_visible = False
            except Exception:
                st.error("Не удалось записать заявку. Проверьте доступ сервиса к Google Sheet.")

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

    grp_label = st.radio("Группа", ["Младшая", "Старшая"], horizontal=True)
    group_code = "junior" if grp_label == "Младшая" else "senior"
    
    subjects = [
        ("biology", "🧬 Биология"),
        ("physics", "🧲 Физика"),
        ("chemistry", "⚗️ Химия"),
        ("math", "➗ Математика"),
        ("cs", "💻 Информатика"),
    ]

    data = load_subjects_from_sheet(SHEETS, group_code)

    tabs = st.tabs([label for _, label in subjects])

    for i, (code, label) in enumerate(subjects):
        with tabs[i]:
            questions = data.get(code, [])
            if not questions:
                st.warning("Вопросы пока не добавлены.")
                continue
            st.caption("Ответьте на вопросы, затем нажмите \"Отправить\".")
            score, total, answers = render_test_form(code, questions)
            if score is not None and total:
                try:
                    SHEETS.append_row(
                        "results",
                        [
                            datetime.now(timezone.utc).isoformat(),
                            a["email"],  # кто сдавал
                            code,        # предмет
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
