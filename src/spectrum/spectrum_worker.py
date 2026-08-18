import shutil
import subprocess

import numpy as np

from PySide6.QtCore import QThread, Signal


SAMPLE_RATE = 48000
FFT_SIZE = 4096
FFT_FPS = 50
FREQ_BINS = 512
FREQ_MIN = 30.0
FREQ_MAX = 18000.0
DB_MIN = -85.0
DB_MAX = -15.0


class SpectrumWorker(QThread):
    spectrum_ready = Signal(object)
    status_changed = Signal(str)

    def __init__(
        self,
        sample_rate=SAMPLE_RATE,
        fft_size=FFT_SIZE,
        fps=FFT_FPS,
        bins=FREQ_BINS,
    ):
        super().__init__()
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.fps = fps
        self.bins = bins
        self.process = None

    def _monitor_device(self):
        if shutil.which("pactl"):
            try:
                sink = subprocess.check_output(
                    ["pactl", "get-default-sink"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
                if sink:
                    return f"{sink}.monitor"
            except Exception:
                pass
        return "@DEFAULT_MONITOR@"

    @staticmethod
    def _read_exact(stream, size):
        data = bytearray()
        while len(data) < size:
            chunk = stream.read(size - len(data))
            if not chunk:
                return None
            data.extend(chunk)
        return bytes(data)

    def run(self):
        if not shutil.which("parec"):
            self.status_changed.emit(
                "parec not found: install pulseaudio-utils"
            )
            return

        hop = max(1, round(self.sample_rate / self.fps))
        window = np.hanning(self.fft_size).astype(np.float32)
        scale = max(float(window.sum()) / 2.0, 1.0)

        freqs = np.fft.rfftfreq(
            self.fft_size,
            1.0 / self.sample_rate,
        )
        target_freqs = np.geomspace(
            FREQ_MIN,
            min(FREQ_MAX, self.sample_rate / 2.0),
            self.bins,
        )

        command = [
            "parec",
            "--raw",
            f"--device={self._monitor_device()}",
            "--format=s16le",
            f"--rate={self.sample_rate}",
            "--channels=1",
        ]

        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
            self.status_changed.emit("Listening to system audio")

            buffer = np.zeros(self.fft_size, dtype=np.float32)
            filled = 0
            byte_count = hop * 2

            while not self.isInterruptionRequested():
                raw = self._read_exact(
                    self.process.stdout,
                    byte_count,
                )
                if raw is None:
                    break

                chunk = np.frombuffer(
                    raw,
                    dtype=np.int16,
                ).astype(np.float32)
                chunk *= 1.0 / 32768.0

                if hop >= self.fft_size:
                    buffer[:] = chunk[-self.fft_size:]
                else:
                    buffer[:-hop] = buffer[hop:]
                    buffer[-hop:] = chunk

                filled = min(
                    self.fft_size,
                    filled + len(chunk),
                )
                if filled < self.fft_size:
                    continue

                spectrum = np.abs(
                    np.fft.rfft(buffer * window)
                )
                spectrum /= scale

                db = 20.0 * np.log10(
                    spectrum + 1e-10
                )
                level = np.clip(
                    (db - DB_MIN) / (DB_MAX - DB_MIN),
                    0.0,
                    1.0,
                )

                log_spectrum = np.interp(
                    target_freqs,
                    freqs,
                    level,
                ).astype(np.float32)
                print(
                    "FFT:",
                    float(log_spectrum.min()),
                    float(log_spectrum.max()),
                )
                self.spectrum_ready.emit(log_spectrum)

        except Exception as exc:
            self.status_changed.emit(str(exc))

        finally:
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            self.process = None

    def stop(self):
        self.requestInterruption()
        if self.process:
            self.process.terminate()
        self.wait(1500)
