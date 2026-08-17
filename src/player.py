import threading
import time
from bisect import bisect_left

import fluidsynth
import mido


class MidiPlayer:
    def __init__(
        self,
        mid_path,
        soundfont,
        driver="pulseaudio",
    ):
        self.mid = mido.MidiFile(mid_path)

        self.soundfont = str(soundfont)
        self.driver = driver

        self.events = self._build_events()
        self.times = [
            t
            for t, _, _ in self.events
        ]

        self.enabled_tracks = set(
            range(len(self.mid.tracks))
        )

        self.track_programs = {}

        self.track_base_volumes = {}
        self.track_volumes = {}

        self.active_notes = {
            track_id: set()
            for track_id in range(
                len(self.mid.tracks)
            )
        }

        self._init_track_volumes()

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

    def _init_track_volumes(self):
        for track_id, track in enumerate(
            self.mid.tracks
        ):
            velocities = [
                msg.velocity
                for msg in track
                if msg.type == "note_on"
                and msg.velocity > 0
            ]

            base = (
                sum(velocities) / len(velocities)
                if velocities
                else 127
            )

            self.track_base_volumes[
                track_id
            ] = base

            self.track_volumes[
                track_id
            ] = base

    def _tempo_events(self):
        events = []

        for track in self.mid.tracks:
            tick = 0

            for msg in track:
                tick += msg.time

                if msg.type == "set_tempo":
                    events.append(
                        (tick, msg.tempo)
                    )

        events.sort()

        return events

    def _tick_to_seconds(
        self,
        target_tick,
        tempo_events,
    ):
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

        seconds += mido.tick2second(
            target_tick - last_tick,
            self.mid.ticks_per_beat,
            tempo,
        )

        return seconds

    def _build_events(self):
        tempo_events = self._tempo_events()

        events = []

        for track_id, track in enumerate(
            self.mid.tracks
        ):
            tick = 0

            for msg in track:
                tick += msg.time

                if msg.is_meta:
                    continue

                seconds = self._tick_to_seconds(
                    tick,
                    tempo_events,
                )

                events.append(
                    (
                        seconds,
                        track_id,
                        msg,
                    )
                )

        events.sort(
            key=lambda item: item[0]
        )

        return events

    def _send(
        self,
        msg,
        track_id=None,
    ):
        if msg.type == "note_on":
            if msg.velocity > 0:
                self._synth.noteon(
                    msg.channel,
                    msg.note,
                    msg.velocity,
                )

                if track_id is not None:
                    self.active_notes[
                        track_id
                    ].add(
                        (
                            msg.channel,
                            msg.note,
                        )
                    )

            else:
                self._note_off(
                    msg.channel,
                    msg.note,
                    track_id,
                )

        elif msg.type == "note_off":
            self._note_off(
                msg.channel,
                msg.note,
                track_id,
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

    def _note_off(
        self,
        channel,
        note,
        track_id=None,
    ):
        self._synth.noteoff(
            channel,
            note,
        )

        if track_id is not None:
            self.active_notes[
                track_id
            ].discard(
                (
                    channel,
                    note,
                )
            )

    def _track_notes_off(
        self,
        track_id,
    ):
        if not self._synth:
            return

        notes = list(
            self.active_notes[track_id]
        )

        for channel, note in notes:
            self._synth.noteoff(
                channel,
                note,
            )

        self.active_notes[
            track_id
        ].clear()

    def _all_notes_off(self):
        if not self._synth:
            return

        for track_id in self.active_notes:
            self._track_notes_off(
                track_id
            )

        for channel in range(16):
            self._synth.cc(
                channel,
                123,
                0,
            )

    def _track_channels(
        self,
        track_id,
    ):
        return {
            msg.channel
            for _, tid, msg in self.events
            if tid == track_id
            and hasattr(msg, "channel")
            and msg.channel != 9
        }

    def _apply_track_program(
        self,
        track_id,
    ):
        if (
            not self._synth
            or track_id
            not in self.track_programs
        ):
            return

        program = self.track_programs[
            track_id
        ]

        for channel in self._track_channels(
            track_id
        ):
            self._synth.program_change(
                channel,
                program,
            )

    def _apply_manual_programs(self):
        for track_id in sorted(
            self.track_programs
        ):
            self._apply_track_program(
                track_id
            )

    def _restore_state(
        self,
        target,
    ):
        for t, track_id, msg in self.events:
            if t > target:
                break

            if msg.type == "program_change":
                if (
                    track_id
                    not in self.track_programs
                ):
                    self._send(msg)

            elif msg.type in (
                "control_change",
                "pitchwheel",
            ):
                self._send(msg)

        # Manual selections always win.
        self._apply_manual_programs()

    def start(self):
        self._synth = fluidsynth.Synth(
            **{
                "audio.realtime-prio": 0
            }
        )

        self._synth.start(
            driver=self.driver
        )

        sfid = self._synth.sfload(
            self.soundfont
        )

        for channel in range(16):
            self._synth.program_select(
                channel,
                sfid,
                0,
                0,
            )

        # General MIDI drum channel.
        self._synth.program_select(
            9,
            sfid,
            128,
            0,
        )

        self._restore_state(0)

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
                    seek_target = self._seek_to
                    self._seek_to = None

                if seek_target is not None:
                    self._all_notes_off()

                    self._restore_state(
                        seek_target
                    )

                    index = bisect_left(
                        self.times,
                        seek_target,
                    )

                    self.position = seek_target

                    clock = (
                        time.monotonic()
                        - seek_target
                    )

                if self.paused:
                    clock = (
                        time.monotonic()
                        - self.position
                    )

                    time.sleep(0.01)
                    continue

                self.position = (
                    time.monotonic()
                    - clock
                )

                while (
                    index < len(self.events)
                    and self.events[index][0]
                    <= self.position
                ):
                    _, track_id, msg = (
                        self.events[index]
                    )

                    self._process_event(
                        track_id,
                        msg,
                    )

                    index += 1

                if index >= len(self.events):
                    self.position = (
                        self.mid.length
                    )

                    self._paused.set()

                    self._all_notes_off()

                    time.sleep(0.01)
                    continue

                time.sleep(0.005)

        finally:
            self._all_notes_off()

            if self._synth:
                self._synth.delete()

    def _process_event(
        self,
        track_id,
        msg,
    ):
        if msg.type == "program_change":
            # Ignore original program if user
            # manually selected an instrument.
            if (
                track_id
                not in self.track_programs
            ):
                self._send(msg)

            return

        if msg.type not in (
            "note_on",
            "note_off",
        ):
            self._send(msg)
            return

        if (
            track_id
            not in self.enabled_tracks
        ):
            return

        if (
            msg.type == "note_on"
            and msg.velocity > 0
        ):
            base = self.track_base_volumes[
                track_id
            ]

            target = self.track_volumes[
                track_id
            ]

            scale = (
                target / base
                if base > 0
                else 1.0
            )

            velocity = int(
                msg.velocity * scale
            )

            if velocity <= 0:
                return

            msg = msg.copy(
                velocity=min(
                    velocity,
                    127,
                )
            )

        self._send(
            msg,
            track_id,
        )

    def play(self):
        if (
            self.position
            >= self.mid.length
        ):
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

    def seek(
        self,
        seconds,
    ):
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

    def set_track_enabled(
        self,
        track_id,
        enabled,
    ):
        if enabled:
            self.enabled_tracks.add(
                track_id
            )

            # Restore only this track's
            # manual instrument.
            self._apply_track_program(
                track_id
            )

        else:
            self.enabled_tracks.discard(
                track_id
            )

            # Stop only this track.
            self._track_notes_off(
                track_id
            )

    def set_track_volume(
        self,
        track_id,
        volume,
    ):
        self.track_volumes[
            track_id
        ] = max(
            0.0,
            min(
                float(volume),
                127.0,
            ),
        )

    def set_track_instrument(
        self,
        track_id,
        program,
    ):
        self.track_programs[
            track_id
        ] = int(program)

        self._apply_track_program(
            track_id
        )

    def stop(self):
        self._stop.set()
        self._all_notes_off()