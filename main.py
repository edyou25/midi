from mido import MidiFile, MidiTrack, Message

mid = MidiFile()
track = MidiTrack()
mid.tracks.append(track)

# 小星星：C C G G A A G ...
notes = [
    60, 60, 67, 67, 69, 69, 67,
    65, 65, 64, 64, 62, 62, 60,
    67, 67, 65, 65, 64, 64, 62,
    67, 67, 65, 65, 64, 64, 62,
    60, 60, 67, 67, 69, 69, 67,
    65, 65, 64, 64, 62, 62, 60
]

for note in notes:
    track.append(Message("note_on", note=note, velocity=80, time=0))
    track.append(Message("note_off", note=note, velocity=80, time=480))

mid.save("outputs/out.mid")

print("Saved: outputs/out.mid")