import psutil, os, platform
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.uic import loadUi


def envpath() -> str:
    if os.name == 'posix':
        cachedir = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
        return cachedir
    else:
        cachedir = os.path.join()
        return cachedir


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

    def render_data(self) -> None:
        try:
            self.CPU.setText(platform.processor())
            self.CPUCore.setText(str(psutil.cpu_count(logical=False)))
            self.CPULoad.setText(f"{str(psutil.cpu_percent())}%")
            self.GPUTemp.setText(str(psutil.sensors_temperatures()['coretemp'][0].current).join('C'))
            self.RAM.setText(f"{str(psutil.virtual_memory().percent)}%")
            self.Disk.setText(f"{str(psutil.disk_usage('/' if os.name == 'posix' else 'C:').percent)}%")
            self.OS.setText(str(os.uname()))

            stats = ['CPU', 'CPUCore', 'CPULoad', 'GPUTemp', 'RAM', 'Disk', 'OS']

            for stat in stats:
                self.stat.setReadOnly(True)

        except Exception as e:
            print("Cannot render data: " + str(e))
            print("Did dependencies installed?")
