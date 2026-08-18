import shutil
import subprocess
import time

import numpy as np

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QWidget
SCROLL_STEP = 1


SAMPLE_RATE = 48000
FFT_SIZE = 1024
FPS = 60

HEIGHT = 130
WIDTH = 320


class SpectrumWorker(QThread):
    column_ready = Signal(object)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.process = None

    def run(self):
        if not shutil.which("parec"):
            self.error.emit("parec not found")
            return

        window = np.hanning(FFT_SIZE)

        freqs = np.fft.rfftfreq(
            FFT_SIZE,
            1.0 / SAMPLE_RATE,
        )

        target_freqs = np.geomspace(
            40,
            20000,
            HEIGHT,
        )

        command = [
            "parec",
            "--raw",
            "--device=@DEFAULT_MONITOR@",
            "--format=s16le",
            f"--rate={SAMPLE_RATE}",
            "--channels=1",
        ]

        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )

            last_update = 0.0
            block_size = FFT_SIZE * 2

            while not self.isInterruptionRequested():
                data = self.process.stdout.read(
                    block_size
                )

                if len(data) != block_size:
                    continue

                now = time.monotonic()

                if now - last_update < 1.0 / FPS:
                    continue

                last_update = now

                samples = np.frombuffer(
                    data,
                    dtype=np.int16,
                ).astype(np.float32)

                samples *= 1.0 / 32768.0
                samples *= window

                spectrum = np.abs(
                    np.fft.rfft(samples)
                )

                db = 20.0 * np.log10(
                    spectrum + 1e-8
                )

                values = np.clip(
                    (db + 80.0) / 80.0,
                    0.0,
                    1.0,
                )

                column = np.interp(
                    target_freqs,
                    freqs,
                    values,
                )[::-1]

                rgb = self._colorize(column)

                self.column_ready.emit(rgb)

        except Exception as e:
            self.error.emit(str(e))

        finally:
            if self.process:
                self.process.terminate()

    @staticmethod
    def _colorize(values):
        r = np.clip(
            values * 3.0 - 1.0,
            0.0,
            1.0,
        )

        g = np.clip(
            values * 3.0,
            0.0,
            1.0,
        )

        b = np.clip(
            1.5 - values * 2.0,
            0.0,
            1.0,
        )

        return (
            np.stack([r, g, b], axis=1)
            * 255
        ).astype(np.uint8)

    def stop(self):
        self.requestInterruption()

        if self.process:
            self.process.terminate()

        self.wait(1000)


class Spectrogram(QWidget):
    def __init__(self):
        super().__init__()

        self.setFixedHeight(150)

        self.image = np.zeros(
            (HEIGHT, WIDTH, 3),
            dtype=np.uint8,
        )

        self.message = ""

        self.worker = SpectrumWorker()

        self.worker.column_ready.connect(
            self._add_column
        )

        self.worker.error.connect(
            self._set_error
        )

        self.worker.start()

    def _add_column(self, column):
        self.image[:, :-SCROLL_STEP] = self.image[:, SCROLL_STEP:]

        for i in range(SCROLL_STEP):
            self.image[:, -1 - i] = column

        self.update()

    def _set_error(self, message):
        self.message = message
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)

        image = QImage(
            self.image.data,
            WIDTH,
            HEIGHT,
            self.image.strides[0],
            QImage.Format_RGB888,
        )

        painter.drawImage(
            self.rect(),
            image,
        )

        painter.setPen(
            QColor("white")
        )

        painter.drawText(
            6,
            14,
            "Spectrogram",
        )

        if self.message:
            painter.drawText(
                6,
                30,
                self.message,
            )

    def closeEvent(self, event):
        self.worker.stop()
        super().closeEvent(event)