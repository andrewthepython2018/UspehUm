# sheets_backend.py — устойчивый слой для Google Sheets
from typing import Any, Optional, List, Dict
import time
import gspread
from gspread.exceptions import WorksheetNotFound, APIError

HEADERS: Dict[str, List[str]] = {
    "users":   ["email", "name", "role", "active"],
    "tests": ["subject", "qid", "question", "a", "b", "c", "d", "correct", "group"],
    "results": ["timestamp", "email", "subject", "score", "total", "answers"],
    "signup":  ["timestamp", "name", "email", "request"],
}

class Sheets:
    def __init__(self, spreadsheet_url: str, sa_info: dict):
        self.gc = gspread.service_account_from_dict(sa_info)
        self.sh = self.gc.open_by_url(spreadsheet_url)

    # ---------- internals ----------
    def _get_ws(self, title: str, headers=None, **_):
        """Вернёт лист, при отсутствии создаст; с ретраями на 429/5xx."""
        for delay in (0.0, 0.3, 0.8):
            try:
                try:
                    ws = self.sh.worksheet(title)
                except WorksheetNotFound:
                    cols = len(headers) if headers else 10
                    ws = self.sh.add_worksheet(title=title, rows=1000, cols=cols)
                if headers:
                    first = ws.row_values(1)
                    if not first:
                        ws.update("1:1", [headers])
                return ws
            except APIError as e:
                code = getattr(getattr(e, "response", None), "status_code", None)
                if code not in (429, 500, 502, 503, 504):
                    raise
                time.sleep(delay)
        # финальная попытка
        try:
            ws = self.sh.worksheet(title)
        except WorksheetNotFound:
            cols = len(headers) if headers else 10
            ws = self.sh.add_worksheet(title=title, rows=1000, cols=cols)
        if headers and not ws.row_values(1):
            ws.update("1:1", [headers])
        return ws

    def _get_all_records_retry(self, ws, attempts=(0.0, 0.3, 0.7, 1.2)):
        last = None
        for delay in attempts:
            try:
                return ws.get_all_records()
            except APIError as e:
                last = e
                time.sleep(delay)
        # финальная попытка без sleep
        try:
            return ws.get_all_records()
        except APIError:
            return []

    # ---------- public API ----------
    def append_row(self, sheet: str, row: list) -> None:
        ws = self._get_ws(sheet, HEADERS.get(sheet))
        for delay in (0.0, 0.3, 0.8):
            try:
                ws.append_row(row, value_input_option="USER_ENTERED")
                return
            except APIError as e:
                code = getattr(getattr(e, "response", None), "status_code", None)
                if code not in (429, 500, 502, 503, 504):
                    raise
                time.sleep(delay)
        ws.append_row(row, value_input_option="USER_ENTERED")

    def get_user(self, email: str) -> Optional[dict]:
        ws = self._get_ws("users", HEADERS["users"])
        rows = self._get_all_records_retry(ws)
        em = (email or "").strip().lower()
        for r in rows:
            if str(r.get("email", "")).strip().lower() == em:
                return r
        return None

    def get_tests(self) -> List[dict]:
        ws = self._get_ws("tests", HEADERS["tests"])
        rows = self._get_all_records_retry(ws)
        # нормализуем qid -> int, если возможно
        out = []
        for r in rows:
            if not r.get("subject"):
                continue
            try:
                r["qid"] = int(r.get("qid"))
            except Exception:
                pass
            out.append(r)
        return out

    def count_results(self, email: str) -> int:
        ws = self._get_ws("results", HEADERS["results"])
        rows = self._get_all_records_retry(ws)
        em = (email or "").strip().lower()
        return sum(1 for r in rows if str(r.get("email", "")).strip().lower() == em)
