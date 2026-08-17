import time
import threading

import fluidsynth
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from plot import plot_midi, load_config


config = load_config()

fig, ax, cursor, time_text, mid = plot_midi(
    show=False,
    cursor=True
)

duration = mid.length

state = {
    "start": None,
    "done": False
}


def format_time(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def play():
    fs = fluidsynth.Synth()
    fs.start(driver="pulseaudio")

    sfid = fs.sfload(config["soundfont"])

    for ch in range(16):
        fs.program_select(ch, sfid, 0, 0)

    state["start"] = time.monotonic()

    for msg in mid.play():

        if msg.is_meta:
            continue

        if msg.type == "note_on":
            if msg.velocity > 0:
                fs.noteon(msg.channel, msg.note, msg.velocity)
            else:
                fs.noteoff(msg.channel, msg.note)

        elif msg.type == "note_off":
            fs.noteoff(msg.channel, msg.note)

        elif msg.type == "program_change":
            fs.program_change(msg.channel, msg.program)

        elif msg.type == "control_change":
            fs.cc(msg.channel, msg.control, msg.value)

    state["done"] = True

    for ch in range(16):
        fs.cc(ch, 123, 0)

    fs.delete()


def update(_):
    if state["start"] is None:
        return cursor, time_text

    elapsed = min(
        time.monotonic() - state["start"],
        duration
    )

    cursor.set_xdata([elapsed, elapsed])

    time_text.set_text(
        f"{format_time(elapsed)} / {format_time(duration)}"
    )

    return cursor, time_text


ani = FuncAnimation(
    fig,
    update,
    interval=50,
    cache_frame_data=False
)

thread = threading.Thread(
    target=play,
    daemon=True
)

thread.start()

plt.show()