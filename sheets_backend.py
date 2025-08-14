from typing import Any, Optional, List
import gspread

class Sheets:
    def __init__(self, spreadsheet_url: str, sa_info: dict):
        self.gc = gspread.service_account_from_dict(sa_info)
        self.sh = self.gc.open_by_url(spreadsheet_url)

    def _get_ws(self, title: str):
        try:
            return self.sh.worksheet(title)
        except gspread.WorksheetNotFound:
            # если листа нет — создадим и положим заголовки по умолчанию
            ws = self.sh.add_worksheet(title=title, rows=1000, cols=26)
            if title == "users":
                ws.append_row(["email", "name", "role", "active"])            
            elif title == "tests":
                ws.append_row(["subject", "qid", "question", "a", "b", "c", "d", "correct"]) 
            elif title == "results":
                ws.append_row(["timestamp", "email", "subject", "score", "total", "answers_json"]) 
            elif title == "signup":
                ws.append_row(["timestamp", "name", "email", "request"]) 
            return ws

    def get_user(self, email: str) -> Optional[dict]:
        ws = self._get_ws("users")
        rows = ws.get_all_records()
        for r in rows:
            if str(r.get("email", "")).strip().lower() == email:
                return r
        return None

    def get_tests(self) -> List[dict]:
        ws = self._get_ws("tests")
        return ws.get_all_records()

    def count_results(self, email: str) -> int:
        ws = self._get_ws("results")
        vals = ws.col_values(2)  # email колонка
        return sum(1 for v in vals if v.strip().lower() == email.strip().lower())

    def append_row(self, sheet: str, row: List[Any]):
        ws = self._get_ws(sheet)
        ws.append_row(row)
