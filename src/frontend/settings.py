import os
import webbrowser
import json
from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox
from PyQt6.uic import loadUi

class Settings(QWidget):
    def __init__(self):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), "Settings.ui")
        loadUi(ui_path, self)
        self.setWindowTitle("Настройки - LMS-Disk")
        
        self.settings_file = os.path.join(os.path.dirname(__file__), "settings.json")
        self.default_settings = {
            "theme": "Светлая",
            "top_count": 10,
            "auto_save": True,
            "follow_links": False,
            "default_path": os.path.sep
        }
        
        self._load_settings()
        self._connect_signals()
        self._initialize_widgets()
    
    def _connect_signals(self):
        self.browseBtn.clicked.connect(self._on_browse_clicked)
        self.resetBtn.clicked.connect(self._on_reset_clicked)
        self.cancelBtn.clicked.connect(self.close)
        self.saveBtn.clicked.connect(self._on_save_clicked)
        self.pushButton.clicked.connect(self._on_developer_site_clicked)
    
    def _initialize_widgets(self):
        self.themeCombo.addItems(["Светлая", "Тёмная", "Системная"])
        self.topCountSpin.setMinimum(1)
        self.topCountSpin.setMaximum(100)
        self.topCountSpin.setValue(self.default_settings["top_count"])
    
    def _load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.default_settings.update(settings)
            except Exception:
                pass
        
        self.themeCombo.setCurrentText(self.default_settings.get("theme", "Светлая"))
        self.topCountSpin.setValue(self.default_settings.get("top_count", 10))
        self.autoSaveCb.setChecked(self.default_settings.get("auto_save", True))
        self.followLinksCb.setChecked(self.default_settings.get("follow_links", False))
        self.defaultPathEdit.setText(self.default_settings.get("default_path", os.path.sep))
    
    def _on_browse_clicked(self):
        current_path = self.defaultPathEdit.text() or os.path.sep
        directory = QFileDialog.getExistingDirectory(
            self,
            "Выберите путь по умолчанию для сканирования",
            current_path
        )
        if directory:
            self.defaultPathEdit.setText(directory)
    
    def _on_reset_clicked(self):
        reply = QMessageBox.question(
            self,
            "Сброс настроек",
            "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.themeCombo.setCurrentText("Светлая")
            self.topCountSpin.setValue(10)
            self.autoSaveCb.setChecked(True)
            self.followLinksCb.setChecked(False)
            self.defaultPathEdit.setText(os.path.sep)
    
    def _on_save_clicked(self):
        settings = {
            "theme": self.themeCombo.currentText(),
            "top_count": self.topCountSpin.value(),
            "auto_save": self.autoSaveCb.isChecked(),
            "follow_links": self.followLinksCb.isChecked(),
            "default_path": self.defaultPathEdit.text()
        }
        
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Успех", "Настройки сохранены")
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки:\n{e}")
    
    def _on_developer_site_clicked(self):
        webbrowser.open('https://www.namilsk.tech')
    
    def get_settings(self):
        return {
            "theme": self.themeCombo.currentText(),
            "top_count": self.topCountSpin.value(),
            "auto_save": self.autoSaveCb.isChecked(),
            "follow_links": self.followLinksCb.isChecked(),
            "default_path": self.defaultPathEdit.text()
        }

s