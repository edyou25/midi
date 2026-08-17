import threading
import time
from bisect import bisect_left

import fluidsynth
import mido


class MidiPlayer:
    def __init__(self, mid_path, soundfont, driver="pulseaudio"):
        self.mid = mido.MidiFile(mid_path)
        self.soundfont = str(soundfont)
        self.driver = driver

        self.events = self._build_events()
        self.times = [t for t, _, _ in self.events]
        self.enabled_tracks = set(range(len(self.mid.tracks)))

        self.position = 0.0
        self._seek_to = None

        self._stop = threading.Event()
        self._paused = threading.Event()
        self._paused.set()

        self._lock = threading.Lock()
        self._thread = None
        self._synth = None

    @property
    def paused(self):
        return self._paused.is_set()

    def _tempo_events(self):
        events = []

        for track in self.mid.tracks:
            tick = 0
            for msg in track:
                tick += msg.time
                if msg.type == "set_tempo":
                    events.append((tick, msg.tempo))

        events.sort()
        return events

    def _tick_to_seconds(self, target_tick, tempo_events):
        tempo = 500000
        last_tick = 0
        seconds = 0.0

        for tick, new_tempo in tempo_events:
            if tick > target_tick:
                break

            seconds += mido.tick2second(
                tick - last_tick,
                self.mid.ticks_per_beat,
                tempo,
            )
            last_tick = tick
            tempo = new_tempo

        return seconds + mido.tick2second(
            target_tick - last_tick,
            self.mid.ticks_per_beat,
            tempo,
        )

    def _build_events(self):
        tempo_events = self._tempo_events()
        events = []

        for track_id, track in enumerate(self.mid.tracks):
            tick = 0

            for msg in track:
                tick += msg.time

                if msg.is_meta:
                    continue

                events.append(
                    (
                        self._tick_to_seconds(
                            tick,
                            tempo_events,
                        ),
                        track_id,
                        msg,
                    )
                )

        events.sort(key=lambda item: item[0])
        return events

    def _send(self, msg):
        if msg.type == "note_on":
            if msg.velocity:
                self._synth.noteon(
                    msg.channel,
                    msg.note,
                    msg.velocity,
                )
            else:
                self._synth.noteoff(
                    msg.channel,
                    msg.note,
                )

        elif msg.type == "note_off":
            self._synth.noteoff(
                msg.channel,
                msg.note,
            )

        elif msg.type == "program_change":
            self._synth.program_change(
                msg.channel,
                msg.program,
            )

        elif msg.type == "control_change":
            self._synth.cc(
                msg.channel,
                msg.control,
                msg.value,
            )

        elif msg.type == "pitchwheel":
            self._synth.pitch_bend(
                msg.channel,
                msg.pitch,
            )

    def _all_notes_off(self):
        if not self._synth:
            return

        for channel in range(16):
            self._synth.cc(channel, 123, 0)

    def _restore_state(self, target):
        for t, track_id, msg in self.events:
            if t >= target:
                break

            if (
                track_id in self.enabled_tracks
                and msg.type in (
                    "program_change",
                    "control_change",
                )
            ):
                self._send(msg)

    def start(self):
        self._synth = fluidsynth.Synth()
        self._synth.start(driver=self.driver)

        sfid = self._synth.sfload(self.soundfont)

        for channel in range(16):
            self._synth.program_select(
                channel,
                sfid,
                0,
                0,
            )

        self._synth.program_select(
            9,
            sfid,
            128,
            0,
        )

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
        )
        self._thread.start()

    def _run(self):
        index = 0
        clock = time.monotonic()

        try:
            while not self._stop.is_set():
                with self._lock:
                    target = self._seek_to
                    self._seek_to = None

                if target is not None:
                    self._all_notes_off()
                    self._restore_state(target)
                    index = bisect_left(
                        self.times,
                        target,
                    )
                    self.position = target
                    clock = time.monotonic() - target

                if self.paused:
                    clock = time.monotonic() - self.position
                    time.sleep(0.01)
                    continue

                self.position = time.monotonic() - clock

                while (
                    index < len(self.events)
                    and self.events[index][0] <= self.position
                ):
                    _, track_id, msg = self.events[index]

                    if track_id in self.enabled_tracks:
                        self._send(msg)

                    index += 1

                if index >= len(self.events):
                    self.position = self.mid.length
                    self._paused.set()
                    self._all_notes_off()
                    time.sleep(0.01)
                    continue

                time.sleep(0.005)

        finally:
            self._all_notes_off()

            if self._synth:
                self._synth.delete()

    def play(self):
        if self.position >= self.mid.length:
            self.seek(0.0)

        self._paused.clear()

    def pause(self):
        self._paused.set()
        self._all_notes_off()

    def toggle(self):
        if self.paused:
            self.play()
        else:
            self.pause()

    def seek(self, seconds):
        target = max(
            0.0,
            min(
                float(seconds),
                self.mid.length,
            ),
        )

        with self._lock:
            self._seek_to = target

        self.position = target

    def set_track_enabled(self, track_id, enabled):
        if enabled:
            self.enabled_tracks.add(track_id)
        else:
            self.enabled_tracks.discard(track_id)
            self._all_notes_off()

    def stop(self):
        self._stop.set()
        self._all_notes_off()
