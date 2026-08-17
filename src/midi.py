from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass

import mido


@dataclass
class Note:
    start: float
    duration: float
    pitch: int
    velocity: int
    channel: int
    track: int


def load_midi(path):
    return mido.MidiFile(path)


def _tick_converter(mid):
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
        seconds.append(
            seconds[-1]
            + mido.tick2second(
                ticks[i] - ticks[i - 1],
                mid.ticks_per_beat,
                tempos[i - 1],
            )
        )

    def to_seconds(tick):
        i = bisect_right(ticks, tick) - 1
        return seconds[i] + mido.tick2second(
            tick - ticks[i],
            mid.ticks_per_beat,
            tempos[i],
        )

    return to_seconds


def extract_notes(mid):
    to_seconds = _tick_converter(mid)
    notes = []

    for track_id, track in enumerate(mid.tracks):
        tick = 0
        active = defaultdict(list)

        for msg in track:
            tick += msg.time

            if not hasattr(msg, "channel"):
                continue

            key = (msg.channel, getattr(msg, "note", -1))

            if msg.type == "note_on" and msg.velocity > 0:
                active[key].append((tick, msg.velocity))

            elif msg.type == "note_off" or (
                msg.type == "note_on" and msg.velocity == 0
            ):
                if active[key]:
                    start_tick, velocity = active[key].pop(0)

                    start = to_seconds(start_tick)
                    end = to_seconds(tick)

                    notes.append(
                        Note(
                            start,
                            end - start,
                            msg.note,
                            velocity,
                            msg.channel,
                            track_id,
                        )
                    )

    return notes


def track_name(track, track_id):
    return track.name.strip() or f"Track {track_id}"