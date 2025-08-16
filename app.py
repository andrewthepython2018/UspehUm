# app.py — Онлайн школа: вход + тесты (junior/senior)
import json
from datetime import datetime, timezone

import streamlit as st
from sheets_backend import Sheets
from tests_core import load_subjects_from_sheet, render_test_form

st.set_page_config(page_title="Онлайн школа — ЛК", page_icon="🎓", layout="wide")

# ---- Константы интерфейса ----
SUBJECTS = [
    ("biology", "Биология"),
    ("physics", "Физика"),
    ("chemistry", "Химия"),
    ("math", "Математика"),
    ("cs", "Информатика"),
]

# ---- Инициализация доступа к Google Sheets ----
def _build_sheets():
    # ничего лишнего не печатаем (без ключей и т.п.)
    spreadsheet_url = st.secrets.get("spreadsheet_url", "")
    sa_info = st.secrets.get("gcp_service_account", {})
    if not spreadsheet_url or not sa_info:
        st.error("Не настроены секреты: spreadsheet_url и/или gcp_service_account.")
        st.stop()
    try:
        return Sheets(spreadsheet_url=spreadsheet_url, sa_info=sa_info)
    except Exception as e:
        st.error("Не удалось подключиться к Google Sheets. Проверьте доступ сервисного аккаунта.")
        st.stop()

if "SHEETS" not in st.session_state:
    st.session_state.SHEETS = _build_sheets()
SHEETS: Sheets = st.session_state.SHEETS

# ---- Аутентификация ----
def login_view():
    st.title("Личный кабинет")
    st.subheader("Вход")
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="name@example.com")
        name = st.text_input("Имя (необязательно)")
        submitted = st.form_submit_button("Войти")

    if not submitted:
        return

    email_norm = (email or "").strip().lower()
    if "@" not in email_norm:
        st.error("Введите корректный email.")
        return

    # Пытаемся найти пользователя. Если нет — создадим запись (упростим тестирование).
    try:
        user = SHEETS.get_user(email_norm)
    except Exception:
        user = None

    if not user:
        try:
            SHEETS.append_row("users", [email_norm, (name or ""), "student", "TRUE"])
        except Exception:
            # если запись не удалась — всё равно пустим, но покажем предупреждение
            st.warning("Не удалось записать нового пользователя в 'users', продолжим без этого.")
        user = {"email": email_norm, "name": name or ""}

    st.session_state["auth"] = {
        "email": email_norm,
        "name": user.get("name") or name or email_norm.split("@")[0],
    }
    st.rerun()

# ---- Дашборд и тесты ----
def dashboard_view():
    a = st.session_state.get("auth") or {}
    st.title("Личный кабинет")
    left, right = st.columns([1, 1])
    with left:
        st.caption(f"Вы вошли как: **{a.get('name') or a.get('email')}**")
    with right:
        if st.button("Выйти", use_container_width=True):
            st.session_state.pop("auth", None)
            st.rerun()

    # Метрика «Сдано тестов»
    try:
        total_results = SHEETS.count_results(a.get("email")) or 0
    except Exception:
        total_results = 0
    st.metric("Сдано тестов", total_results)

    st.subheader("Входные тесты")
    grp_label = st.radio("Группа", ["Младшая", "Старшая"], horizontal=True)
    group_code = "junior" if grp_label == "Младшая" else "senior"

    # Загружаем банк вопросов с учётом группы (поддерживаются рус/англ subject/group и любой регистр заголовков)
    data = load_subjects_from_sheet(SHEETS, group_code)

    tabs = st.tabs([label for _, label in SUBJECTS])
    for i, (code, label) in enumerate(SUBJECTS):
        with tabs[i]:
            questions = data.get(code, [])
            if not questions:
                st.warning("Вопросы пока не добавлены для этой группы.")
                continue

            st.caption("Ответьте на вопросы, затем нажмите «Отправить».")
            score, total, answers = render_test_form(code, questions)

            # пишем результат только если форма отправлена и есть вопросы
            if score is not None and total:
                try:
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
                except Exception:
                    st.error("Не удалось записать результат. Попробуйте ещё раз.")
                else:
                    st.success(f"Результат сохранён: {score} / {total}")

# ---- Точка входа ----
def main():
    if not st.session_state.get("auth"):
        login_view()
    else:
        dashboard_view()

if __name__ == "__main__":
    main()
