from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass

import mido


GM_INSTRUMENTS = [
    "Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano",
    "Honky-tonk Piano", "Electric Piano 1", "Electric Piano 2",
    "Harpsichord", "Clavinet", "Celesta", "Glockenspiel", "Music Box",
    "Vibraphone", "Marimba", "Xylophone", "Tubular Bells", "Dulcimer",
    "Drawbar Organ", "Percussive Organ", "Rock Organ", "Church Organ",
    "Reed Organ", "Accordion", "Harmonica", "Tango Accordion",
    "Acoustic Guitar (nylon)", "Acoustic Guitar (steel)",
    "Electric Guitar (jazz)", "Electric Guitar (clean)",
    "Electric Guitar (muted)", "Overdriven Guitar", "Distortion Guitar",
    "Guitar Harmonics", "Acoustic Bass", "Electric Bass (finger)",
    "Electric Bass (pick)", "Fretless Bass", "Slap Bass 1", "Slap Bass 2",
    "Synth Bass 1", "Synth Bass 2", "Violin", "Viola", "Cello", "Contrabass",
    "Tremolo Strings", "Pizzicato Strings", "Orchestral Harp", "Timpani",
    "String Ensemble 1", "String Ensemble 2", "SynthStrings 1",
    "SynthStrings 2", "Choir Aahs", "Voice Oohs", "Synth Voice",
    "Orchestra Hit", "Trumpet", "Trombone", "Tuba", "Muted Trumpet",
    "French Horn", "Brass Section", "SynthBrass 1", "SynthBrass 2",
    "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax", "Oboe",
    "English Horn", "Bassoon", "Clarinet", "Piccolo", "Flute", "Recorder",
    "Pan Flute", "Blown Bottle", "Shakuhachi", "Whistle", "Ocarina",
    "Lead 1 (square)", "Lead 2 (sawtooth)", "Lead 3 (calliope)",
    "Lead 4 (chiff)", "Lead 5 (charang)", "Lead 6 (voice)",
    "Lead 7 (fifths)", "Lead 8 (bass + lead)", "Pad 1 (new age)",
    "Pad 2 (warm)", "Pad 3 (polysynth)", "Pad 4 (choir)", "Pad 5 (bowed)",
    "Pad 6 (metallic)", "Pad 7 (halo)", "Pad 8 (sweep)", "FX 1 (rain)",
    "FX 2 (soundtrack)", "FX 3 (crystal)", "FX 4 (atmosphere)",
    "FX 5 (brightness)", "FX 6 (goblins)", "FX 7 (echoes)",
    "FX 8 (sci-fi)", "Sitar", "Banjo", "Shamisen", "Koto", "Kalimba",
    "Bag Pipe", "Fiddle", "Shanai", "Tinkle Bell", "Agogo", "Steel Drums",
    "Woodblock", "Taiko Drum", "Melodic Tom", "Synth Drum",
    "Reverse Cymbal", "Guitar Fret Noise", "Breath Noise", "Seashore",
    "Bird Tweet", "Telephone Ring", "Helicopter", "Applause", "Gunshot",
]


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


def _tick_to_second(mid):
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

    def convert(tick):
        i = bisect_right(ticks, tick) - 1
        return seconds[i] + mido.tick2second(
            tick - ticks[i], mid.ticks_per_beat, tempos[i]
        )

    return convert


def extract_notes(mid):
    to_second = _tick_to_second(mid)
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
                    start = to_second(start_tick)
                    end = to_second(tick)
                    notes.append(
                        Note(
                            start=start,
                            duration=max(0.0, end - start),
                            pitch=msg.note,
                            velocity=velocity,
                            channel=msg.channel,
                            track=track_id,
                        )
                    )

    return notes


def instrument_name(track):
    programs = []
    has_notes = False
    has_drums = False

    for msg in track:
        if msg.type in ("note_on", "note_off"):
            has_notes = True
            if getattr(msg, "channel", -1) == 9:
                has_drums = True

        if msg.type == "program_change" and msg.channel != 9:
            name = GM_INSTRUMENTS[msg.program]
            if name not in programs:
                programs.append(name)

    if has_drums:
        programs.append("Drums")

    if not programs and has_notes:
        programs.append("Acoustic Grand Piano")

    return " / ".join(programs) or "Unknown"

def average_velocity(track):
    values = [
        msg.velocity
        for msg in track
        if msg.type == "note_on"
        and msg.velocity > 0
    ]

    if not values:
        return 0

    return round(
        sum(values) / len(values)
    )

def track_program(track):
    for msg in track:
        if msg.type == "program_change":
            return msg.program

    return 0


def is_drum_track(track):
    return any(
        hasattr(msg, "channel")
        and msg.channel == 9
        and msg.type in ("note_on", "note_off")
        for msg in track
    )