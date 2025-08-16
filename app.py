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
    # Шапка
    st.title("Онлайн школа — личный кабинет")
    st.markdown(
        "Добро пожаловать! Пройдите входные тесты по биологии, физике, химии, математике и информатике. "
        "Если вы ещё не зарегистрированы — подайте заявку на доступ."
    )
    st.divider()

    # Сообщения об успехе/ошибке заявки — снаружи формы
    if st.session_state.pop("signup_success", False):
        st.success("Заявка отправлена! Мы свяжемся с вами по e-mail после активации.")
    if st.session_state.pop("signup_error", False):
        st.error("Не удалось отправить заявку. Попробуйте ещё раз или напишите администратору.")

    # Предзаполнение из сессии (если уже пробовали логин/заявку)
    last_email = st.session_state.get("signup_email", "")
    last_name = st.session_state.get("signup_name", "")

    # Форма входа — БЕЗ раннего return
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", value=last_email, placeholder="name@example.com", key="login_email")
        name = st.text_input("Имя (необязательно)", value=last_name, key="login_name")
        submitted = st.form_submit_button("Войти")

    # Обработка входа
    if submitted:
        email_norm = (email or "").strip().lower()
        if "@" not in email_norm:
            st.error("Введите корректный email.")
        else:
            try:
                user = SHEETS.get_user(email_norm)
            except Exception:
                user = None

            def _is_active(u: dict | None) -> bool:
                if not u:
                    return False
                val = str(u.get("active", "")).strip().lower()
                return val in ("true", "1", "yes", "y", "да")

            if user and _is_active(user):
                st.session_state["auth"] = {
                    "email": email_norm,
                    "name": user.get("name") or name or email_norm.split("@")[0],
                }
                st.rerun()
                return
            else:
                # Переключаемся в режим подачи заявки и перерисовываем страницу
                st.session_state["signup_mode"] = True
                st.session_state["signup_email"] = email_norm
                st.session_state["signup_name"] = name or (user.get("name", "") if user else "")
                st.session_state["signup_known"] = bool(user)  # найден, но не активен
                st.session_state["signup_open"] = True
                st.rerun()

    # Режим заявки — показываем и обрабатываем независимо от кнопки «Войти»
    if st.session_state.get("signup_mode"):
        email_norm = st.session_state.get("signup_email", "")
        name_pref = st.session_state.get("signup_name", "")
        known = st.session_state.get("signup_known", False)

        if not known:
            st.warning("Пользователь с таким e-mail не найден. Подайте заявку на регистрацию ниже.")
        else:
            st.info("Ваш аккаунт пока не активирован. Вы можете отправить заявку, чтобы ускорить процесс.")

        exp_open = st.session_state.get("signup_open", True)
        with st.expander("📝 Подать заявку на регистрацию", expanded=exp_open):
            with st.form("signup_form", clear_on_submit=False):
                s_name = st.text_input("Имя", value=name_pref, key="signup_name_input")
                s_email = st.text_input("Email для доступа", value=email_norm, disabled=True, key="signup_email_input")
                s_group = st.selectbox("Группа", ["Младшая", "Старшая"], index=0, key="signup_group_input")
                s_comment = st.text_area("Комментарий (необязательно)", placeholder="Класс, школа, пожелания…", key="signup_comment_input")
                send_req = st.form_submit_button("Отправить заявку")

            if send_req:
                try:
                    req_payload = {
                        "group": "junior" if s_group == "Младшая" else "senior",
                        "comment": s_comment or "",
                    }
                    SHEETS.append_row(
                        "signup",
                        [
                            datetime.now(timezone.utc).isoformat(),
                            s_name,
                            email_norm,
                            json.dumps(req_payload, ensure_ascii=False),
                        ],
                    )
                except Exception:
                    st.session_state["signup_error"] = True
                else:
                    st.session_state["signup_success"] = True

                # После клика: держим блок открытым, выходим из режима заявки и перерисовываем
                st.session_state["signup_open"] = True
                st.session_state["signup_mode"] = False
                st.rerun()




# ---- Дашборд и тесты ----
def dashboard_view():
    a = st.session_state.get("auth") or {}
    st.title("Личный кабинет")
    st.caption("Проходите входные тесты: результат сохраняется в журнал успеваемости.")
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
