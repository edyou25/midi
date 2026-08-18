from mido import MidiFile, MidiTrack, Message, MetaMessage

mid = MidiFile()

scale_track = MidiTrack()
chord_track = MidiTrack()

mid.tracks.append(scale_track)
mid.tracks.append(chord_track)

scale_track.append(
    MetaMessage("track_name", name="Scales", time=0)
)

chord_track.append(
    MetaMessage("track_name", name="Chords", time=0)
)


# ============================================================
# 1. Major / Minor Scales
# ============================================================

notes = [
    # Major scales
    60, 62, 64, 65, 67, 69, 71, 72,  # C Major
    61, 63, 65, 66, 68, 70, 72, 73,  # C# Major
    62, 64, 66, 67, 69, 71, 73, 74,  # D Major
    63, 65, 67, 68, 70, 72, 74, 75,  # D# Major
    64, 66, 68, 69, 71, 73, 75, 76,  # E Major
    65, 67, 69, 70, 72, 74, 76, 77,  # F Major
    66, 68, 70, 71, 73, 75, 77, 78,  # F# Major
    67, 69, 71, 72, 74, 76, 78, 79,  # G Major
    68, 70, 72, 73, 75, 77, 79, 80,  # G# Major
    69, 71, 73, 74, 76, 78, 80, 81,  # A Major
    70, 72, 74, 75, 77, 79, 81, 82,  # A# Major
    71, 73, 75, 76, 78, 80, 82, 83,  # B Major

    # Natural minor scales
    60, 62, 63, 65, 67, 68, 70, 72,  # C Minor
    61, 63, 64, 66, 68, 69, 71, 73,  # C# Minor
    62, 64, 65, 67, 69, 70, 72, 74,  # D Minor
    63, 65, 66, 68, 70, 71, 73, 75,  # D# Minor
    64, 66, 67, 69, 71, 72, 74, 76,  # E Minor
    65, 67, 68, 70, 72, 73, 75, 77,  # F Minor
    66, 68, 69, 71, 73, 74, 76, 78,  # F# Minor
    67, 69, 70, 72, 74, 75, 77, 79,  # G Minor
    68, 70, 71, 73, 75, 76, 78, 80,  # G# Minor
    69, 71, 72, 74, 76, 77, 79, 81,  # A Minor
    70, 72, 73, 75, 77, 78, 80, 82,  # A# Minor
    71, 73, 74, 76, 78, 79, 81, 83,  # B Minor
]

for note in notes:
    scale_track.append(
        Message(
            "note_on",
            note=note,
            velocity=80,
            time=0,
            channel=0,
        )
    )

    scale_track.append(
        Message(
            "note_off",
            note=note,
            velocity=0,
            time=960,
            channel=0,
        )
    )


# ============================================================
# 2. Major / Minor Chords
# ============================================================

chords = [
    # Major chords
    [60, 64, 67],  # C Major
    [61, 65, 68],  # C# Major
    [62, 66, 69],  # D Major
    [63, 67, 70],  # D# Major
    [64, 68, 71],  # E Major
    [65, 69, 72],  # F Major
    [66, 70, 73],  # F# Major
    [67, 71, 74],  # G Major
    [68, 72, 75],  # G# Major
    [69, 73, 76],  # A Major
    [70, 74, 77],  # A# Major
    [71, 75, 78],  # B Major

    # Minor chords
    [60, 63, 67],  # C Minor
    [61, 64, 68],  # C# Minor
    [62, 65, 69],  # D Minor
    [63, 66, 70],  # D# Minor
    [64, 67, 71],  # E Minor
    [65, 68, 72],  # F Minor
    [66, 69, 73],  # F# Minor
    [67, 70, 74],  # G Minor
    [68, 71, 75],  # G# Minor
    [69, 72, 76],  # A Minor
    [70, 73, 77],  # A# Minor
    [71, 74, 78],  # B Minor
]


# Wait until all scales finish.
delay = len(notes) * 960

first_chord = True

for chord in chords:

    # Three notes start at exactly the same time.
    for i, note in enumerate(chord):
        chord_track.append(
            Message(
                "note_on",
                note=note,
                velocity=80,
                time=delay if first_chord and i == 0 else 0,
                channel=1,
            )
        )

    first_chord = False

    # Hold chord for 2 beats.
    for i, note in enumerate(chord):
        chord_track.append(
            Message(
                "note_off",
                note=note,
                velocity=0,
                time=960 if i == 0 else 0,
                channel=1,
            )
        )


mid.save("outputs/out.mid")

print("Saved: outputs/out.mid")