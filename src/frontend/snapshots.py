import sqlite3 
from os import abspath 
from PyQt6.QtWidgets import QWidget, QTableWidget
from PyQt6.uic import loadUi

class Snapshots(QWidget):
    def __init__(self):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), "Snapshots.ui")
        loadUi(ui_path, self)
        
        self.con = sqlite3.connect(abspath("snapshots.db"))
        self.cursor = self.con.cursor()
        self.cursor.execute("SELECT * FROM snapshots")
        self.rows = self.cursor.fetchall()
        self.table = QTableWidget()
        self.table.setRowCount(len(self.rows))