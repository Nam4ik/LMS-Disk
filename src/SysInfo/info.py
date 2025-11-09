import psutil, json, os, platform

def envpath() -> str: 
    if os.name == 'posix':
        cachedir = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
        return cachedir
    else:
        cachedir = os.path.join()  
        return cachedir

def sysinfo_json() -> str: 
    sysinfo = {
        "cpu_name": platform.processor(),
        "gpu_name": platform.gpu_name(),  
        "cpu_count": psutil.cpu_count(logical=False),
        "cpu_percentage": psutil.cpu_percent(),
        "gpu_temp": psutil.sensors_temperatures()['coretemp'][0].current,
        "ram": psutil.virtual_memory().percent,
        "disk": if os.name == 'posix': psutil.disk_usage('/').percent else: psutil.disk_usage('C:\ ').percent,
        "os": os.uname() 
    }

    cache_sysinfo = json.dumps(sysinfo)
    return json_str
     

