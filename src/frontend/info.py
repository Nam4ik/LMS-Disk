import psutil, os, platform
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.uic import loadUi

"""
def sysinfo_json() -> str: 
    systype = os.name()

    sysinfo = {
        "cpu_name": platform.processor(),
        "gpu_name": platform.gpu_name(),  
        "cpu_count": psutil.cpu_count(logical=False),
        "cpu_percentage": psutil.cpu_percent(),
        "gpu_temp": psutil.sensors_temperatures()['coretemp'][0].current,
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/' if systype == 'posix' else 'C:').percent,
        "os": os.uname() 
    }

    return json_str
     

"""


class Info(QWidget):
    def __init__(self):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), "SysInfo.ui")
        loadUi(ui_path, self)
        self.setWindowTitle("LMS-Disk - SysInfo")

    def render_data(self) -> None:
        try:

            cpu_name = platform.processor() or "Неизвестно"
            self.CPU.setText(cpu_name)

            cpu_cores = psutil.cpu_count(logical=False) or psutil.cpu_count()
            self.CPUCore.setText(str(cpu_cores))

            cpu_load = psutil.cpu_percent(interval=0.1)
            self.CPULoad.setText(f"{cpu_load:.1f}%")

            try:
                sensors = psutil.sensors_temperatures()
                if 'coretemp' in sensors and len(sensors['coretemp']) > 0:
                    gpu_temp = sensors['coretemp'][0].current
                    self.GPUTemp.setText(f"{gpu_temp:.1f}°C")
                else:
                    self.GPUTemp.setText("Недоступно")
            except (KeyError, IndexError, AttributeError):
                self.GPUTemp.setText("Недоступно")

            ram_percent = psutil.virtual_memory().percent
            self.RAM.setText(f"{ram_percent:.1f}%")

            disk_path = '/' if os.name == 'posix' else 'C:'
            disk_percent = psutil.disk_usage(disk_path).percent
            self.Disk.setText(f"{disk_percent:.1f}%")

            try:
                if os.name == 'posix':
                    uname = os.uname()
                    os_info = f"{uname.sysname} {uname.release}"
                else:
                    os_info = f"{platform.system()} {platform.release()}"
                self.OS.setText(os_info)
            except AttributeError:
                self.OS.setText(platform.system())

        except Exception as e:
            print("Cannot render data: " + str(e))
            print("Did dependencies installed?")
