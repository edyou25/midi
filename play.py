import yaml
import mido
import fluidsynth

with open("config.yaml") as f:
    config = yaml.safe_load(f)

mid = mido.MidiFile(config["mid_path"])

fs = fluidsynth.Synth()
fs.start(driver="pulseaudio")

sfid = fs.sfload(config["soundfont"])

# Default piano
for ch in range(16):
    fs.program_select(ch, sfid, 0, 0)

for msg in mid.play():
    if msg.type == "note_on":
        fs.noteon(msg.channel, msg.note, msg.velocity)

    elif msg.type == "note_off":
        fs.noteoff(msg.channel, msg.note)

    elif msg.type == "program_change":
        fs.program_change(msg.channel, msg.program)

fs.delete()