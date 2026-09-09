"""Board telemetry: die temperature, CPU clock and throttling flags.

This is the part that makes the benchmark specific to a Raspberry Pi. A frame
rate on its own is not a result: if the board was throttling, the number
describes the cooling, not the machine. `vcgencmd get_throttled` is the
authoritative source for that on a Pi, so it is sampled alongside the frames
and printed with them.

Every reader degrades to a neutral value on other hardware (NaN / 0 / "?"), so
the benchmark still runs anywhere - it just reports less.

Sampling happens on its own thread at 1 Hz. Reading sysfs and spawning
`vcgencmd` from inside the render loop would show up as frame-time spikes and
poison the very measurement it is there to qualify.
"""

import subprocess
import threading

TEMP_PATH = "/sys/class/thermal/thermal_zone0/temp"
FREQ_PATH = "/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq"


class Sensors:
    def __init__(self):
        self.temp = self.read_temp()
        self.temp_max = self.temp
        self.freq = self.read_freq()
        self.throttled = self.read_throttled()
        self.throttled_seen = self.throttled
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._loop, daemon=True)

    @staticmethod
    def read_temp():
        """Die temperature in Celsius, or NaN where it cannot be read."""
        try:
            with open(TEMP_PATH) as f:
                return int(f.read()) / 1000.0
        except OSError:
            return float("nan")

    @staticmethod
    def read_freq():
        """Current CPU clock in MHz, or 0 where it cannot be read."""
        try:
            with open(FREQ_PATH) as f:
                return int(f.read()) // 1000
        except OSError:
            return 0

    @staticmethod
    def read_throttled():
        """Raw `vcgencmd get_throttled` value ("0x0" when healthy), or "?"."""
        try:
            out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True,
                                 text=True, timeout=3).stdout.strip()
            return out.split("=", 1)[1] if "=" in out else "?"
        except (OSError, subprocess.SubprocessError, IndexError):
            return "?"

    def start(self):
        self._t.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.wait(1.0):
            self.temp = self.read_temp()
            if self.temp == self.temp:  # not NaN
                self.temp_max = max(self.temp_max, self.temp)
            self.freq = self.read_freq()
            self.throttled = self.read_throttled()
            # Latch it: a throttling event that lasts one second still
            # invalidates the run, and must survive to the final report.
            if self.throttled not in ("0x0", "?"):
                self.throttled_seen = self.throttled
