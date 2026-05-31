import os, shutil, json
from datetime import datetime
from utils.database_session import get_db
from models.database import Base

class BackupService:

    def __init__(self, db_path: str = "home_money.db"):
        self.db_path = db_path

    def create_backup(self, backup_type: str = "full") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_{timestamp}_{backup_type}"

        try:
            if backup_type == "full":
                backup_file += ".sqlite"
                shutil.copy2(self.db_path, backup_file)
            elif backup_type == "json":
                backup_file += ".json"
                with get_db() as session:
                    data = {}
                    for table in Base.metadata.sorted_tables:
                        rows = session.query(table).all()
                        data[table.name] = [{c.name: getattr(row, c.name) for c in table.columns} for row in rows]
                with open(backup_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            else:
                return f"Неизвестный тип бэкапа: {backup_type}"

            return f"Бэкап создан: {backup_file} ({os.path.getsize(backup_file)} байт)"

        except Exception as e:
            return f"Ошибка при создании бэкапа: {str(e)}"

    def restore_from_backup(self, backup_file: str) -> str:
        if not os.path.exists(backup_file):
            return f"Файл '{backup_file}' не найден."
        if backup_file.endswith(".sqlite"):
            shutil.copy2(backup_file, self.db_path)
            return f"БД восстановлена из {backup_file}. Перезапустите приложение."
        return "JSON-восстановление требует ручного импорта через API."