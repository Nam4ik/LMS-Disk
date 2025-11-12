from os.path import abspath
import sys, os, webbrowser, datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QMessageBox, QWidget
)
from PyQt6.uic import loadUi
from PyQt6.QtCharts import (
    QChart, QChartView, QLineSeries, QCategoryAxis, QValueAxis, QBarSet, QBarSeries, QBarCategoryAxis
)
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from info import Info
from operator import itemgetter

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


class SysInfo(QWidget):
    def __init__(self):
        super().__init__()


class DiskTool(QMainWindow):
    def __init__(self):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), "DiskUI.ui")
        loadUi(ui_path, self)

        self.sourceButton.clicked.connect(self.source_code_open)
        self.scanButton.clicked.connect(self.on_scan_clicked)
        self.sysInfoButton.clicked.connect(self.show_sysinfo)
        self.setWindowIconText("Disk Tool")
        self._setup_chart()

        if not HAS_LIB:
            self.statusbar.showMessage(f"Не удалось импортировать libdiscscan: {_import_error}")

        self.scan_thread = None

    def source_code_open(self):
        webbrowser.open('https://github.com/Nam4ik/LMS-Disk')

    def show_snapshots(self):
        pass

    def _setup_chart(self):
        self.chart = QChart()
        self.chart.setTitle("Распределение размеров (топ)")
        self.chart.legend().setVisible(False)

        self.series = QLineSeries()
        self.chart.addSeries(self.series)

        self.axis_x = QCategoryAxis()
        self.axis_x.setLabelsAngle(-45)
        self.axis_x.setTitleText("Путь (топ элементов)")

        self.axis_y = QValueAxis()
        self.axis_y.setLabelFormat("%.0f")
        self.axis_y.setTitleText("Размер (MB)")

        self.chart_view = QChartView(self.chart, parent=self.diskChart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        layout = QVBoxLayout(self.diskChart)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chart_view)

    def on_scan_clicked(self):
        if not HAS_LIB:
            QMessageBox.warning(self, "Ошибка", f"Модуль libdiscscan не доступен:\n{_import_error}")
            return

        path_to_scan = abspath(os.sep)
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

        self.chart.setTitle(f"Топ {len(top_n)} элементов на {abspath(os.sep)}")
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

    def on_sysinfo_clicked(self):
        self.sysInfoButton.clicked.connect(self.show_sysinfo)
        self.show_sysinfo()


def main() -> None:
    app = QApplication(sys.argv)
    w = DiskTool()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
