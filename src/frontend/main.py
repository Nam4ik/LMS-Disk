from os.path import abspath
import sys, os, webbrowser, datetime, json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QMessageBox, QWidget
)
from PyQt6.uic import loadUi
from PyQt6.QtCharts import (
    QChart, QChartView, QCategoryAxis, QValueAxis, QBarSet, QBarSeries, QBarCategoryAxis
)
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from operator import itemgetter

from info import Info
from db_statistics import Statistics, StatisticsThread
from app_settings import Settings



try:
    import libdiskscan as libdiscscan

    HAS_LIB = True
except Exception as e:
    libdiscscan = None
    HAS_LIB = False
    _import_error = e


class ScanThread(QThread):
    result_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, path_to_scan):
        super().__init__()
        self.path_to_scan = path_to_scan

    def run(self):
        try:
            if not HAS_LIB:
                raise RuntimeError(f"libdiscscan не найден: {_import_error}")

            try:
                result = libdiscscan.scan(self.path_to_scan, False, -1)
                libdiscscan.save_snapshot(abspath("snapshots.db"), f"snapshot-{datetime.datetime.now()}", result)
            except TypeError:
                result = libdiscscan.scan(self.path_to_scan)
            if not isinstance(result, dict):
                raise TypeError("scan() вернул не dict")

            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class DiskTool(QMainWindow):
    def __init__(self):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), "DiskUI.ui")
        loadUi(ui_path, self)
        
        self.layoutWidget.setGeometry(0, 0, 0, 0)
        self.setWindowTitle("LMS-Disk")
        self.sourceButton.clicked.connect(self.source_code_open)
        self.scanButton.clicked.connect(self.on_scan_clicked)
        self.sysInfoButton.clicked.connect(self.show_sysinfo)
        self.snapshotsButton.clicked.connect(self.show_statistics)
        self.settingsButton.clicked.connect(self.show_settings)
        self.setWindowIconText("Disk Tool")
        
        logo = QPixmap(os.path.join(os.path.dirname(__file__), "logo.png"))
        self.pixmapLabel.setPixmap(logo)
        self.pixmapLabel.setScaledContents(True)
        #self.pixmapLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        #self.pixmapLabel.setScaledContents(True)
        #self.pixmapLabel.resize( )

        self._setup_chart()
        self._setup_resizable_layout()

        if not HAS_LIB:
            self.statusbar.showMessage(f"Не удалось импортировать libdiscscan: {_import_error}")

        self.scan_thread = None
        self.statistics_thread = None
        self.settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        self._load_settings()

    def _load_settings(self):
        self.settings = {
            "theme": "Светлая",
            "top_count": 10,
            "auto_save": True,
            "follow_links": False,
            "default_path": os.path.sep
        }
        
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
            except Exception:
                pass

    def source_code_open(self):
        webbrowser.open('https://github.com/Nam4ik/LMS-Disk')


    # Я не знал как это починить через qtdesigner, по этому пусть будет так хд
    # Вообще по идее не должен layoutWidget иметь фиксированный размер но он имеет
    """
    ...
    <widget class="QWidget" name="layoutWidget">
     <property name="geometry">
      <rect>
       <x>10</x>
       <y>10</y>
       <width>571</width>
       <height>321</height>
     </rect>
     </property>
     ...
     """
    def _setup_resizable_layout(self):
        self.layoutWidget.setGeometry(0, 0, 0, 0)
    
        if self.centralwidget.layout() is None:
            main_layout = QHBoxLayout(self.centralwidget)
        else:
         main_layout = self.centralwidget.layout()
    
        main_layout.addWidget(self.layoutWidget)
    
        main_layout.setStretch(0, 1)  
        main_layout.setStretch(1, 3) 

    def _setup_chart(self):
        self.chart = QChart()
        self.chart.setTitle("Распределение размеров (топ)")
        self.chart.legend().setVisible(False)

        self.series = QBarSeries()
        self.chart.addSeries(self.series)

        self.chart_view = QChartView(self.chart, parent=self.diskChart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        layout = QVBoxLayout(self.diskChart)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chart_view)

    def on_scan_clicked(self):
        if not HAS_LIB:
            QMessageBox.warning(self, "Ошибка", f"Модуль libdiscscan не доступен:\n{_import_error}")
            return

        self._load_settings()
        default_path = self.settings.get("default_path", os.path.sep)
        path_to_scan = abspath(default_path)
        self.statusbar.showMessage(f"Сканирование {path_to_scan} ...")
        QApplication.processEvents()

        self.scan_thread = ScanThread(path_to_scan)
        self.scan_thread.result_ready.connect(self.on_scan_finished)
        self.scan_thread.error.connect(self.on_scan_error)
        self.scan_thread.start()

        self.scanButton.setEnabled(False)
        self.scanButton.setText("Сканирование...")

    def on_scan_finished(self, result: dict):
        self.scanButton.setEnabled(True)
        self.scanButton.setText("Сканировать")

        if not result:
            QMessageBox.information(self, "Пусто", "Ничего не найдено для отображения")
            self.statusbar.showMessage("Готово — нет данных")
            return

        items = []
        for p, (size, t, mtime) in result.items():
            try:
                size_int = int(size)
            except Exception:
                continue
            items.append((p, size_int, t))

        items_sorted = sorted(items, key=itemgetter(1), reverse=True)
        top_n = items_sorted[:10]

        if not top_n:
            QMessageBox.information(self, "Пусто", "Нет данных для графика")
            self.statusbar.showMessage("Готово — нет данных")
            return

        self.chart.removeAllSeries()

        bar_series = QBarSeries()
        bar_set = QBarSet("Размер (MB)")

        categories = []
        for p, size_bytes, t in top_n:
            size_mb = size_bytes / (1024.0 * 1024.0)
            bar_set.append(size_mb)

            label = os.path.basename(p) or p
            if len(label) > 20:
                label = label[:17] + "..."
            categories.append(label)

        bar_series.append(bar_set)
        self.chart.addSeries(bar_series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsAngle(-45)
        axis_x.setTitleText("Путь (топ элементов)")

        axis_y = QValueAxis()
        axis_y.setTitleText("Размер (MB)")
        axis_y.setLabelFormat("%.0f")

        self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        bar_series.attachAxis(axis_x)
        bar_series.attachAxis(axis_y)

        axis_y.setRange(0, max(bar_set) * 1.1)

        default_path = self.settings.get("default_path", os.path.sep)
        path_display = abspath(default_path)
        self.chart.setTitle(f"Топ {len(top_n)} элементов на {path_display}")
        self.statusbar.showMessage(f"Сканирование завершено — показаны {len(top_n)} элементов")

    def on_scan_error(self, message: str):
        self.scanButton.setEnabled(True)
        self.scanButton.setText("Сканировать")
        QMessageBox.critical(self, "Ошибка при сканировании", message)
        self.statusbar.showMessage("Ошибка при сканировании")

    def show_sysinfo(self):
        try:
            self.sysinfo_window = Info()
            self.sysinfo_window.show()
            self.sysinfo_window.render_data()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть окно системной информации:\n{e}")

    def show_statistics(self):
        db_path = os.path.join(os.path.dirname(__file__), "snapshots.db")
        
        self.statistics_thread = StatisticsThread(db_path)
        self.statistics_thread.status_update.connect(self.statusbar.showMessage)
        self.statistics_thread.window_ready.connect(self._create_statistics_window)
        self.statistics_thread.data_ready.connect(self._populate_statistics_table)
        self.statistics_thread.error.connect(self._on_statistics_error)
        self.statistics_thread.start()

    def _create_statistics_window(self):
        try:
            db_path = os.path.join(os.path.dirname(__file__), "snapshots.db")
            self.statistics_window = Statistics(db_path)
            self.statistics_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть окно статистики:\n{e}")
            self.statusbar.showMessage("Ошибка при открытии окна статистики")
    
    def _populate_statistics_table(self, rows):
        if hasattr(self, 'statistics_window') and self.statistics_window:
            self.statistics_window._populate_table(rows)

    def _on_statistics_error(self, message: str):
        QMessageBox.critical(self, "Ошибка", message)
        self.statusbar.showMessage("Ошибка при открытии базы данных")

    def show_settings(self):
        try:
            self.settings_window = Settings()
            self.settings_window.destroyed.connect(self._load_settings)
            self.settings_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть окно настроек:\n{e}")

def except_hooks(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)

def main() -> None:
    app = QApplication(sys.argv)
    sys.__excepthook__ = except_hooks
    w = DiskTool()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
