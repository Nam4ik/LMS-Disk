import sqlite3
import os
from os.path import abspath
from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QMessageBox, QAbstractItemView
from PyQt6.uic import loadUi


class Statistics(QWidget):
    def __init__(self):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), "Statistics.ui")
        loadUi(ui_path, self)
        self.setWindowTitle("LMS-Disk - Snapshots viewer")
        self.db_path = abspath("snapshots.db")
        self.refreshButton.clicked.connect(self.load_statistics)

        self.statisticsTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.load_statistics()
    
    def load_statistics(self):
        try:
            if not os.path.exists(self.db_path):
                QMessageBox.warning(
                    self, 
                    "База данных не найдена", 
                    f"База данных {self.db_path} не существует.\nВыполните сканирование диска для создания снапшотов."
                )
                self.statisticsTable.setRowCount(0)
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
            
            if len(rows) == 0:
                QMessageBox.information(
                    self,
                    "Нет данных",
                    "В базе данных нет записей.\nВыполните сканирование диска для создания снапшотов."
                )
                
        except sqlite3.Error as e:
            QMessageBox.critical(
                self,
                "Ошибка базы данных",
                f"Ошибка при работе с базой данных:\n{str(e)}"
            )
            self.statisticsTable.setRowCount(0)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Неожиданная ошибка:\n{str(e)}"
            )
            self.statisticsTable.setRowCount(0)


