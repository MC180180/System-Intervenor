import time
import psutil
import ctypes

def get_cpu_freq_ntpower():
    try:
        cores = psutil.cpu_count()
        class PROCESSOR_POWER_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("Number", ctypes.c_ulong),
                ("MaxMhz", ctypes.c_ulong),
                ("CurrentMhz", ctypes.c_ulong),
                ("MhzLimit", ctypes.c_ulong),
                ("MaxIdleState", ctypes.c_ulong),
                ("CurrentIdleState", ctypes.c_ulong),
            ]
        buffer_size = ctypes.sizeof(PROCESSOR_POWER_INFORMATION) * cores
        buffer = (PROCESSOR_POWER_INFORMATION * cores)()
        status = ctypes.windll.powrprof.CallNtPowerInformation(11, None, 0, ctypes.byref(buffer), buffer_size)
        if status == 0:
            mhz_list = [buffer[i].CurrentMhz for i in range(cores)]
            return sum(mhz_list) / len(mhz_list)
    except Exception as e:
        print("NtPower Error:", e)
    return 0

t0 = time.time()
freq = get_cpu_freq_ntpower()
t1 = time.time()
print(f"Freq (NtPower): {freq} MHz (took {t1-t0:.4f}s)")

t0 = time.time()
print("psutil freq:", psutil.cpu_freq())
t1 = time.time()
print(f"psutil freq took {t1-t0:.4f}s")


t0 = time.time()
threads = 0
handles = 0
count = 0
for p in psutil.process_iter(['num_threads', 'num_handles']):
    try:
        t = p.info.get('num_threads')
        h = p.info.get('num_handles')
        if t: threads += t
        if h: handles += h
        count += 1
    except:
        pass
t1 = time.time()

print(f"Processes: {count}, Threads: {threads}, Handles: {handles} (took {t1-t0:.4f}s)")

