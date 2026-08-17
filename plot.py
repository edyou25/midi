from pathlib import Path
from collections import defaultdict
from bisect import bisect_right

import yaml
import mido
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


CONFIG_PATH = Path(__file__).with_name("config.yaml")


def load_config(config_path=CONFIG_PATH):
    with open(config_path) as f:
        return yaml.safe_load(f)


def build_tick_to_second(mid):
    tempo_at = {0: 500000}

    for track in mid.tracks:
        tick = 0

        for msg in track:
            tick += msg.time

            if msg.type == "set_tempo":
                tempo_at[tick] = msg.tempo

    ticks = sorted(tempo_at)
    tempos = [tempo_at[t] for t in ticks]

    seconds = [0.0]

    for i in range(1, len(ticks)):
        dt = ticks[i] - ticks[i - 1]

        seconds.append(
            seconds[-1]
            + mido.tick2second(
                dt,
                mid.ticks_per_beat,
                tempos[i - 1]
            )
        )

    def tick_to_second(tick):
        i = bisect_right(ticks, tick) - 1

        return (
            seconds[i]
            + mido.tick2second(
                tick - ticks[i],
                mid.ticks_per_beat,
                tempos[i]
            )
        )

    return tick_to_second


def extract_notes(mid):
    tick_to_second = build_tick_to_second(mid)

    notes = []

    for track_id, track in enumerate(mid.tracks):
        tick = 0
        active = defaultdict(list)

        for msg in track:
            tick += msg.time

            if msg.type == "note_on" and msg.velocity > 0:
                active[(msg.channel, msg.note)].append(tick)

            elif msg.type == "note_off" or (
                msg.type == "note_on"
                and msg.velocity == 0
            ):
                key = (msg.channel, msg.note)

                if active[key]:
                    start_tick = active[key].pop(0)

                    start = tick_to_second(start_tick)
                    end = tick_to_second(tick)

                    notes.append(
                        (
                            start,
                            end - start,
                            msg.note,
                            track_id
                        )
                    )

    return notes


def plot_midi(config_path=CONFIG_PATH, show=True, cursor=False):
    config = load_config(config_path)

    mid = mido.MidiFile(config["mid_path"])
    notes = extract_notes(mid)

    fig, ax = plt.subplots(figsize=(16, 8))

    cmap = plt.get_cmap("tab20")

    track_colors = {}
    track_names = {}
    used_tracks = set()

    for track_id, track in enumerate(mid.tracks):
        track_colors[track_id] = cmap(track_id % 20)

        track_names[track_id] = (
            track.name
            if track.name
            else f"Track {track_id}"
        )

    for start, duration, note, track_id in notes:
        ax.barh(
            note,
            duration,
            left=start,
            height=0.8,
            color=track_colors[track_id]
        )

        used_tracks.add(track_id)

    legend = [
        Patch(
            color=track_colors[track_id],
            label=f"{track_id}: {track_names[track_id]}"
        )
        for track_id in sorted(used_tracks)
    ]

    ax.legend(
        handles=legend,
        loc="upper left",
        bbox_to_anchor=(1.01, 1)
    )

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("MIDI Note")
    ax.set_title(config["mid_path"])

    ax.grid(axis="x", alpha=0.3)

    play_cursor = None
    time_text = None

    if cursor:
        play_cursor = ax.axvline(
            0,
            linewidth=2
        )

        time_text = ax.text(
            0.01,
            0.98,
            "00:00 / 00:00",
            transform=ax.transAxes,
            verticalalignment="top"
        )

    fig.tight_layout()

    if show:
        plt.show()

    return fig, ax, play_cursor, time_text, mid


if __name__ == "__main__":
    plot_midi()