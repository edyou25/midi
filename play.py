import sys
import threading
import time

import fluidsynth
import mido

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from plot import create_viewer
from src.config import load_config


cfg = load_config()
mid = mido.MidiFile(cfg["mid_path"])

state = {
    "start": None,
}

stop = threading.Event()


def play_midi():
    synth = fluidsynth.Synth()

    synth.start(
        driver=cfg.get(
            "audio_driver",
            "pulseaudio",
        )
    )

    sfid = synth.sfload(
        str(cfg["soundfont"])
    )

    for channel in range(16):
        synth.program_select(
            channel,
            sfid,
            0,
            0,
        )

    # General MIDI percussion channel
    synth.program_select(
        9,
        sfid,
        128,
        0,
    )

    state["start"] = time.monotonic()

    try:
        for msg in mid.play():
            if stop.is_set():
                break

            if msg.is_meta:
                continue

            if msg.type == "note_on":
                if msg.velocity:
                    synth.noteon(
                        msg.channel,
                        msg.note,
                        msg.velocity,
                    )
                else:
                    synth.noteoff(
                        msg.channel,
                        msg.note,
                    )

            elif msg.type == "note_off":
                synth.noteoff(
                    msg.channel,
                    msg.note,
                )

            elif msg.type == "program_change":
                synth.program_change(
                    msg.channel,
                    msg.program,
                )

            elif msg.type == "control_change":
                synth.cc(
                    msg.channel,
                    msg.control,
                    msg.value,
                )

    finally:
        for channel in range(16):
            synth.cc(channel, 123, 0)

        synth.delete()


def main():
    app = QApplication(sys.argv)

    viewer = create_viewer(
        show_cursor=True
    )

    viewer.show()

    timer = QTimer()

    def update():
        if state["start"] is not None:
            viewer.set_time(
                time.monotonic()
                - state["start"]
            )

    timer.timeout.connect(update)
    timer.start(50)

    thread = threading.Thread(
        target=play_midi,
        daemon=True,
    )

    QTimer.singleShot(
        200,
        thread.start,
    )

    app.aboutToQuit.connect(
        stop.set
    )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()