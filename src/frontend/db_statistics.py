import sqlite3
import os
from os.path import abspath
from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QMessageBox, QAbstractItemView
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.uic import loadUi


class StatisticsThread(QThread):
    status_update = pyqtSignal(str)
    window_ready = pyqtSignal()
    data_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path

    def run(self):
        try:
            self.status_update.emit("Открытие базы данных: Подождите, база данных может открываться какое-то время")
            if not os.path.exists(self.db_path):
                self.error.emit(f"База данных {self.db_path} не существует")
                return

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
                SELECT 
                    e.path,
                    e.size,
                    e.type,
                    s.name as snapshot_name
                FROM entries e
                JOIN snapshots s ON e.snapshot_id = s.id
                ORDER BY e.size DESC
                LIMIT 10
            """

            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            self.window_ready.emit()
            self.data_ready.emit(rows)
            self.status_update.emit("Открытие базы данных: Готово")
        except sqlite3.Error as e:
            self.error.emit(f"Ошибка при работе с базой данных:\n{str(e)}")
        except Exception as e:
            self.error.emit(f"Не удалось открыть базу данных:\n{e}")


class Statistics(QWidget):
    def __init__(self, db_path=None):
        super().__init__()
        loadUi(os.path.join(os.path.dirname(__file__), "Statistics.ui"), self)
        self.setWindowTitle("LMS-Disk - Snapshots viewer")
        self.db_path = db_path or abspath("snapshots.db")
        self.refreshButton.clicked.connect(self.load_statistics)

        self.statisticsTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        self.load_thread = None

    def load_statistics(self):
        if self.load_thread and self.load_thread.isRunning():
            return
        
        self.load_thread = StatisticsThread(self.db_path)
        self.load_thread.data_ready.connect(self._populate_table)
        self.load_thread.error.connect(self._on_load_error)
        self.load_thread.start()
    
    def _populate_table(self, rows):
        if not rows:
            QMessageBox.information(
                self,
                "Нет данных",
                "В базе данных нет записей.\nВыполните сканирование диска для создания снапшотов."
            )
            self.statisticsTable.setRowCount(0)
            return

        self.statisticsTable.setRowCount(len(rows))
        self.statisticsTable.setColumnCount(6)

        headers = ["№", "Путь", "Размер (MB)", "Размер (GB)", "Тип", "Снапшот"]
        self.statisticsTable.setHorizontalHeaderLabels(headers)

        for row_idx, (path, size_bytes, file_type, snapshot_name) in enumerate(rows):
            size_bytes = int(size_bytes) if size_bytes is not None else 0

            self.statisticsTable.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))

            path_item = QTableWidgetItem(path)
            path_item.setToolTip(path)
            self.statisticsTable.setItem(row_idx, 1, path_item)

            size_mb = size_bytes / (1024.0 * 1024.0)
            mb_item = QTableWidgetItem(f"{size_mb:,.2f}")
            mb_item.setToolTip(f"{size_bytes:,} байт")
            self.statisticsTable.setItem(row_idx, 2, mb_item)

            size_gb = size_bytes / (1024.0 * 1024.0 * 1024.0)
            gb_item = QTableWidgetItem(f"{size_gb:,.2f}")
            gb_item.setToolTip(f"{size_bytes:,} байт")
            self.statisticsTable.setItem(row_idx, 3, gb_item)

            self.statisticsTable.setItem(row_idx, 4, QTableWidgetItem(file_type or "unknown"))

            self.statisticsTable.setItem(row_idx, 5, QTableWidgetItem(snapshot_name))

        self.statisticsTable.resizeColumnsToContents()
    
    def _on_load_error(self, message: str):
        if "не существует" in message:
            QMessageBox.warning(
                self,
                "База данных не найдена",
                f"{message}\nВыполните сканирование диска для создания снапшотов."
            )
        else:
            QMessageBox.critical(
                self,
                "Ошибка",
                message
            )
        self.statisticsTable.setRowCount(0)

