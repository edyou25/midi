# MIDI Viewer / Player

## Run

```bash
conda activate midi
python plot.py
```

Interactive MIDI visualization with selectable tracks.

```bash
python play.py
```

Playback has two basic controls:

1. **Play / Pause**
2. **Click anywhere on the piano roll to jump to that time**

The white vertical line shows the current playback position.

Other view controls:

- Track checkbox: show/hide a track
- Drag: pan
- Ctrl + wheel: horizontal zoom

## Config

`config/config.yaml`

```yaml
mid_path: downloads/QueenBohemianRhapsody.mid
soundfont: /usr/share/sounds/sf2/FluidR3_GM.sf2
audio_driver: pulseaudio
```
