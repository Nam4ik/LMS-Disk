from os.path import abspath
import sys, os, webbrowser, datetime, json
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QWidget,
)
from PyQt6.QtCharts import (
    QChart,
    QChartView,
    QValueAxis,
    QBarSet,
    QBarSeries,
    QBarCategoryAxis,
)
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from operator import itemgetter

from info import Info
from db_statistics import Statistics, StatisticsThread
from app_settings import Settings
from DiskUI import Ui_MainWindow


try:
    import libdiskscan as libdiscscan

    HAS_LIB = True
except Exception as e:
    libdiscscan = None
    HAS_LIB = False
    _import_error = e


def get_db_path():
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)

    return os.path.join(base_path, "snapshots.db")


class ScanThread(QThread):
    result_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, path_to_scan, auto_save=bool, follow_links=bool):
        super().__init__()
        self.path_to_scan = path_to_scan
        self.follow_links = follow_links
        self.auto_save = auto_save

    def run(self):
        try:
            if not HAS_LIB:
                raise RuntimeError(f"libdiscscan не найден: {_import_error}")

            try:
                result = libdiscscan.scan(self.path_to_scan, False, -1)
                if self.auto_save:
                    db_path = get_db_path()
                    libdiscscan.save_snapshot(
                        db_path, f"snapshot-{datetime.datetime.now()}", result
                    )
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

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setWindowTitle("LMS-Disk")
        self.setWindowIconText("Disk Tool")

        self.ui.sourceButton.clicked.connect(self.source_code_open)
        self.ui.scanButton.clicked.connect(self.on_scan_clicked)
        self.ui.sysInfoButton.clicked.connect(self.show_sysinfo)
        self.ui.snapshotsButton.clicked.connect(self.show_statistics)
        self.ui.settingsButton.clicked.connect(self.show_settings)

        logo = QPixmap(os.path.join(os.path.dirname(__file__), "logo.png"))
        self.ui.pixmapLabel.setPixmap(logo)
        self.ui.pixmapLabel.setScaledContents(True)

        self._setup_chart()
        self._setup_resizable_layout()

        if not HAS_LIB:
            self.ui.statusbar.showMessage(
                f"Не удалось импортировать libdiscscan: {_import_error}"
            )

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
            "default_path": os.path.sep,
        }

        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
            except Exception:
                pass

    def source_code_open(self):
        webbrowser.open("https://github.com/Nam4ik/LMS-Disk")

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
        self.ui.layoutWidget.setGeometry(0, 0, 0, 0)

        if self.ui.centralwidget.layout() is None:
            main_layout = QHBoxLayout(self.ui.centralwidget)
        else:
            main_layout = self.ui.centralwidget.layout()

        main_layout.addWidget(self.ui.layoutWidget)

        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 3)

    def _setup_chart(self):
        self.chart = QChart()
        self.chart.setTitle("Распределение размеров (топ)")
        self.chart.legend().setVisible(False) 

        self.series = QBarSeries()
        self.chart.addSeries(self.series)

        self.chart_view = QChartView(self.chart, parent=self.ui.diskChart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        layout = QVBoxLayout(self.ui.diskChart)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chart_view)

    def on_scan_clicked(self):
        if not HAS_LIB:
            QMessageBox.warning(
                self, "Ошибка", f"Модуль libdiscscan не доступен:\n{_import_error}"
            )
            return

        self._load_settings()
        follow_links = self.settings.get("follow_links", False)
        auto_save = self.settings.get("auto_save", False)
        default_path = self.settings.get("default_path", os.path.sep)
        path_to_scan = abspath(default_path)
        self.ui.statusbar.showMessage(f"Сканирование {path_to_scan} ...")
        QApplication.processEvents()

        self.scan_thread = ScanThread(path_to_scan, auto_save, follow_links)
        self.scan_thread.result_ready.connect(self.on_scan_finished)
        self.scan_thread.error.connect(self.on_scan_error)
        self.scan_thread.start()

        self.ui.scanButton.setEnabled(False)
        self.ui.scanButton.setText("Сканирование...")

    def on_scan_finished(self, result: dict):
        self.ui.scanButton.setEnabled(True)
        self.ui.scanButton.setText("Сканировать")
        new_chart = QChart()

        new_chart.setTitle(self.chart.title())
        new_chart.legend().setVisible(False) 

        for axis in self.series.attachedAxes():
            self.series.detachAxis(axis)
        self.series.clear()

        if not result:
            QMessageBox.information(self, "Пусто", "Ничего не найдено для отображения")
            self.ui.statusbar.showMessage("Готово — нет данных")

            axis_x = QBarCategoryAxis()
            axis_x.setTitleText("Путь (топ элементов)")
            axis_y = QValueAxis()
            axis_y.setTitleText("Размер (MB)")
            axis_y.setLabelFormat("%.0f")
            axis_y.setRange(0, 1)

            new_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            new_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            self.series.attachAxis(axis_x)
            self.series.attachAxis(axis_y)
            new_chart.addSeries(self.series)

            parent_layout = self.ui.diskChart.layout()
            parent_layout.removeWidget(self.chart_view)
            self.chart_view.setChart(new_chart)
            parent_layout.addWidget(self.chart_view)

            default_path = self.settings.get("default_path", os.path.sep)
            path_display = abspath(default_path)
            new_chart.setTitle(f"Топ 0 элементов на {path_display}") 
            return

        self._load_settings()
        top_count = self.settings.get("top_count", 10)

        items = []
        for p, (size, t, mtime) in result.items():
            try:
                size_int = int(size)
            except Exception:
                continue
            items.append((p, size_int, t))

        items_sorted = sorted(items, key=itemgetter(1), reverse=True)
        top_n = items_sorted[:top_count]

        if not top_n:
            QMessageBox.information(self, "Пусто", "Нет данных для графика")
            self.ui.statusbar.showMessage("Готово — нет данных")

            axis_x = QBarCategoryAxis()
            axis_x.setTitleText("Путь (топ элементов)")
            axis_y = QValueAxis()
            axis_y.setTitleText("Размер (MB)")
            axis_y.setLabelFormat("%.0f")
            axis_y.setRange(0, 1)

            new_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            new_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

            self.series.attachAxis(axis_x)
            self.series.attachAxis(axis_y)

            new_chart.addSeries(self.series)
            parent_layout = self.ui.diskChart.layout()
            parent_layout.removeWidget(self.chart_view)

            self.chart_view.setChart(new_chart)

            parent_layout.addWidget(self.chart_view)
            default_path = self.settings.get("default_path", os.path.sep)
            path_display = abspath(default_path)
            new_chart.setTitle(f"Топ 0 элементов на {path_display}")

            return

        bar_set = QBarSet("Размер (MB)")
        categories = []
        values_for_max = []
        for p, size_bytes, t in top_n:
            size_mb = size_bytes / (1024.0 * 1024.0)
            bar_set.append(size_mb)
            values_for_max.append(size_mb)
            label = os.path.basename(p) or p
            if len(label) > 20:
                label = label[:17] + "..."
            categories.append(label)

        self.series.append(bar_set)


        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsAngle(-45)
        axis_x.setTitleText("Путь (топ элементов)")

        axis_y = QValueAxis()
        axis_y.setTitleText("Размер (MB)")
        axis_y.setLabelFormat("%.0f")
        max_val = max(values_for_max) if values_for_max else 1
        axis_y.setRange(0, max_val * 1.1)

        new_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        new_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        self.series.attachAxis(axis_x)
        self.series.attachAxis(axis_y)
        new_chart.addSeries(self.series)

        
        default_path = self.settings.get("default_path", os.path.sep)
        path_display = abspath(default_path)
        new_chart.setTitle(f"Топ {len(top_n)} элементов на {path_display}")
        self.ui.statusbar.showMessage(
            f"Сканирование завершено — показаны {len(top_n)} элементов"
        )

        parent_layout = self.ui.diskChart.layout()
        parent_layout.removeWidget(self.chart_view)
        self.chart_view.setChart(new_chart)
        parent_layout.addWidget(self.chart_view)

    def on_scan_error(self, message: str):
        self.ui.scanButton.setEnabled(True)
        self.ui.scanButton.setText("Сканировать")
        QMessageBox.critical(self, "Ошибка при сканировании", message)
        self.ui.statusbar.showMessage("Ошибка при сканировании")

    def show_sysinfo(self):
        try:
            self.sysinfo_window = Info()
            self.sysinfo_window.show()
            self.sysinfo_window.render_data()

        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось открыть окно системной информации:\n{e}"
            )

    def show_statistics(self):
        db_path = get_db_path()

        self.statistics_thread = StatisticsThread(db_path)
        self.statistics_thread.status_update.connect(self.ui.statusbar.showMessage)
        self.statistics_thread.window_ready.connect(self._create_statistics_window)
        self.statistics_thread.data_ready.connect(self._populate_statistics_table)
        self.statistics_thread.error.connect(self._on_statistics_error)
        self.statistics_thread.start()

    def _create_statistics_window(self):
        try:
            db_path = get_db_path()
            self.statistics_window = Statistics(db_path)
            self.statistics_window.show()
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось открыть окно статистики:\n{e}"
            )
            self.statusbar.showMessage("Ошибка при открытии окна статистики")

    def _populate_statistics_table(self, rows):
        if hasattr(self, "statistics_window") and self.statistics_window:
            self.statistics_window._populate_table(rows)

    def _on_statistics_error(self, message: str):
        QMessageBox.critical(self, "Ошибка", message)
        self.ui.statusbar.showMessage("Ошибка при открытии базы данных")

    def show_settings(self):
        try:
            self.settings_window = Settings()
            self.settings_window.destroyed.connect(self._load_settings)
            self.settings_window.show()
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось открыть окно настроек:\n{e}"
            )


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
