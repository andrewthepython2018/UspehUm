from typing import Dict, List, Tuple
import streamlit as st

SUBJECT_LABELS = {
    "biology": "🧬 Биология",
    "physics": "🧲 Физика",
    "chemistry": "⚗️ Химия",
    "math": "➗ Математика",
    "cs": "💻 Информатика",
}

# Формат строки tests: subject, qid, question, a, b, c, d, correct

def load_subjects_from_sheet(SHEETS) -> Dict[str, List[dict]]:
    rows = SHEETS.get_tests()
    buckets: Dict[str, List[dict]] = {k: [] for k in SUBJECT_LABELS.keys()}
    for r in rows:
        subj = str(r.get("subject", "")).strip().lower()
        if subj in buckets:
            buckets[subj].append({
                "qid": r.get("qid"),
                "question": r.get("question"),
                "options": {
                    "a": r.get("a"),
                    "b": r.get("b"),
                    "c": r.get("c"),
                    "d": r.get("d"),
                },
                "correct": str(r.get("correct", "")).strip().lower(),
            })
    # сортировка по qid
    for k in buckets:
        buckets[k].sort(key=lambda x: (str(x.get("qid")),))
    return buckets


def render_test_form(subject_code: str, questions: List[dict]):
    key_prefix = f"test_{subject_code}"
    answers = {}
    for q in questions:
        qkey = f"{key_prefix}_{q['qid']}"
        st.markdown(f"**Вопрос {q['qid']}.** {q['question']}")
        choice = st.radio(
            "Выберите ответ",
            label_text = (q.get("text") or q.get("question") or f"Вопрос {q.get('qid')}").strip()

            opts = q.get("options") or {k: q.get(k) for k in ("a", "b", "c", "d")}
            # Защитимся от пустых/сломанных строк в таблице
            if not all(isinstance(opts.get(k), str) and opts.get(k).strip() for k in ("a", "b", "c", "d")):
                # можно показать предупреждение и пропустить вопрос
                # st.warning(f"Пропущен вопрос {q.get('qid')} из-за неполных вариантов.")
                continue
            
            options = [("a", opts["a"]), ("b", opts["b"]), ("c", opts["c"]), ("d", opts["d"])]
        
            format_func=lambda x: x[1],
            horizontal=False,
            key=qkey,
            label_visibility="collapsed",
        )
        answers[str(q["qid"])] = choice[0]
        st.divider()

    submitted = st.button("Отправить", key=f"submit_{subject_code}")
    if submitted:
        score = sum(1 for q in questions if answers.get(str(q["qid"])) == q["correct"])
        total = len(questions)
        st.info(f"Ваш результат: {score} / {total}")
        return score, total, answers
    return None, None, None
