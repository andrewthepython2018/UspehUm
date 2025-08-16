# tests_core.py
from typing import List, Dict, Any
import streamlit as st

# ---------- нормализация строк из таблицы ----------

def _normalize_row(r: Dict[str, Any]) -> Dict[str, Any]:
    text = (r.get("text") or r.get("question") or "").strip()
    opts = r.get("options")
    if not isinstance(opts, dict):
        # плоская схема из Google Sheets
        opts = {k: r.get(k) for k in ("a", "b", "c", "d")}
    correct = (r.get("correct") or "").strip().lower()
    group = (r.get("group") or "").strip().lower()

    return {
        "subject": r.get("subject"),
        "qid": r.get("qid"),
        "text": text,
        "options": {
            "a": str(opts.get("a") or ""),
            "b": str(opts.get("b") or ""),
            "c": str(opts.get("c") or ""),
            "d": str(opts.get("d") or ""),
        },
        "correct": correct if correct in ("a", "b", "c", "d") else "",
        "group": group,
    }

# ---------- загрузка банка вопросов ----------

def load_subjects_from_sheet(sheets, group_code: str | None = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Возвращает dict: subject_code -> List[questions].
    Если задан group_code ('junior'/'senior'), фильтрует вопросы по группе.
    Пустая/неизвестная группа в вопросе трактуется как «для всех».
    """
    rows = sheets.get_tests()
    subjects: Dict[str, List[Dict[str, Any]]] = {}

    for r in rows:
        q = _normalize_row(r)
        # фильтр по группе, если указан
        g = q["group"]
        if group_code and g and g != group_code:
            continue

        subj = (q["subject"] or "").strip()
        if not subj:
            continue

        subjects.setdefault(subj, []).append(q)

    # стабильный порядок
    for k in subjects:
        subjects[k].sort(key=lambda x: (x.get("qid") is None, x.get("qid")))
    return subjects

# ---------- рендер и проверка формы ----------

def render_test_form(subject_code: str, questions: List[Dict[str, Any]]):
    """
    Рисует форму теста для одного предмета.
    Возвращает (score, total, answers_dict).
    Если форма не отправлена — (0, 0, {}).
    """
    total = len(questions or [])
    if total == 0:
        st.info("Нет вопросов для этого раздела.")
        return 0, 0, {}

    with st.form(f"test_form_{subject_code}"):
        answers: Dict[Any, str] = {}

        for i, q in enumerate(questions, start=1):
            label_text = q.get("text") or f"Вопрос {q.get('qid', i)}"
            opts = q.get("options") or {}

            # пропускаем «битые» строки
            if not all(opts.get(k) for k in ("a", "b", "c", "d")):
                continue

            values = [("a", opts["a"]), ("b", opts["b"]), ("c", opts["c"]), ("d", opts["d"])]
            choice = st.radio(
                label_text,
                values,
                format_func=lambda t: f"{t[0].upper()}) {t[1]}",
                key=f"q_{subject_code}_{i}",
            )
            # сохраняем букву выбранного ответа
            answers[q.get("qid", i)] = choice[0]

        submitted = st.form_submit_button("Отправить ответы")

    if not submitted:
        return 0, 0, {}

    # подсчёт баллов
    score = 0
    for q in questions:
        corr = (q.get("correct") or "").strip().lower()
        qid = q.get("qid")
        sel = answers.get(qid)
        if sel and corr and sel == corr:
            score += 1

    return score, total, answers
