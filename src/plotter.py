from collections import defaultdict

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from src.spectrum.spectrogram_gl import SpectrogramGL
from src.midi import (
    GM_INSTRUMENTS,
    average_velocity,
    extract_notes,
    instrument_name,
    is_drum_track,
    load_midi,
    track_program,
)
from src.track_panel import TrackPanel

PX_PER_SEC = 40
NOTE_H = 7


def format_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class PianoRoll(QGraphicsView):
    time_clicked = Signal(float)

    def __init__(self, scene):
        super().__init__(scene)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self._press_pos = None

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, 1)
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        if event.button() != Qt.LeftButton or self._press_pos is None:
            return

        release_pos = event.position().toPoint()
        distance = (release_pos - self._press_pos).manhattanLength()
        self._press_pos = None

        if distance > 6:
            return

        point = self.mapToScene(release_pos)
        self.time_clicked.emit(max(0.0, point.x() / PX_PER_SEC))


class MidiViewer(QWidget):
    track_play_changed = Signal(int, bool)
    track_volume_changed = Signal(int, float)
    track_instrument_changed = Signal(int, int)

    def __init__(
        self,
        mid_path,
        show_cursor=False,
        playback_controls=False,
    ):
        super().__init__()

        self.mid = load_midi(mid_path)
        self.notes = extract_notes(self.mid)
        self.duration = self.mid.length
        self.items = defaultdict(list)

        self.scene = QGraphicsScene(self)
        self.view = PianoRoll(self.scene)

        self.scene_width = max(1000, self.duration * PX_PER_SEC)
        self.scene_height = 128 * NOTE_H
        self.scene.setSceneRect(
            0,
            0,
            self.scene_width,
            self.scene_height,
        )

        self._draw_grid()
        self._draw_notes()

        cursor_pen = QPen(QColor("white"), 2)
        cursor_pen.setCosmetic(True)

        self.cursor = self.scene.addLine(
            0,
            0,
            0,
            self.scene_height,
            cursor_pen,
        )
        self.cursor.setZValue(10)
        self.cursor.setVisible(show_cursor)

        self.play_button = QPushButton("Play")
        self.play_button.setVisible(playback_controls)

        self.time_label = QLabel(
            f"00:00 / {format_time(self.duration)}"
        )

        controls = QHBoxLayout()
        controls.addWidget(self.play_button)
        controls.addWidget(self.time_label)
        controls.addStretch()

        main = QVBoxLayout()
        main.addWidget(self.view, 1)
        main.addLayout(controls)

        tracks = [
            (
                track_id,
                instrument_name(
                    self.mid.tracks[track_id]
                ),
                average_velocity(
                    self.mid.tracks[track_id]
                ),
                track_program(
                    self.mid.tracks[track_id]
                ),
                is_drum_track(
                    self.mid.tracks[track_id]
                ),
            )
            for track_id in sorted(self.items)
        ]
        self.track_panel = TrackPanel(
            tracks,
            self._color,
            GM_INSTRUMENTS,
        )
        self.track_panel.visibility_changed.connect(
            self.set_track_visible
        )
        self.track_panel.playback_changed.connect(
            self.track_play_changed
        )
        self.track_panel.volume_changed.connect(
            self.track_volume_changed
        )
        self.track_panel.instrument_changed.connect(
            self.track_instrument_changed
        )

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(4)

        left.addWidget(self.track_panel, 1)

        self.spectrogram = None
        if playback_controls:
            self.spectrogram = SpectrogramGL(self)
            self.spectrogram.setFixedWidth(470)
            left.addWidget(self.spectrogram, 0)

        layout = QHBoxLayout(self)
        layout.addLayout(left)
        layout.addLayout(main, 1)

        self.setWindowTitle(str(mid_path))
        self.resize(1500, 850)

    @staticmethod
    def _color(track_id):
        return QColor.fromHsv(
            (track_id * 47) % 360,
            180,
            220,
        )

    def _draw_grid(self):
        pen = QPen(QColor(100, 100, 100, 60))
        pen.setCosmetic(True)

        for note in range(128):
            y = (127 - note) * NOTE_H
            self.scene.addLine(
                0,
                y,
                self.scene_width,
                y,
                pen,
            )

        for sec in range(0, int(self.duration) + 10, 10):
            x = sec * PX_PER_SEC
            self.scene.addLine(
                x,
                0,
                x,
                self.scene_height,
                pen,
            )

            text = self.scene.addText(format_time(sec))
            text.setDefaultTextColor(
                QColor(160, 160, 160)
            )
            text.setPos(x + 2, 0)

    def _draw_notes(self):
        for note in self.notes:
            color = self._color(note.track)
            x = note.start * PX_PER_SEC
            y = (127 - note.pitch) * NOTE_H
            width = max(
                1.5,
                note.duration * PX_PER_SEC,
            )

            item = self.scene.addRect(
                x,
                y,
                width,
                NOTE_H - 1,
                QPen(color.darker(130)),
                QBrush(color),
            )
            item.setToolTip(
                f"Track: {note.track}\n"
                f"Note: {note.pitch}\n"
                f"Time: {note.start:.2f}s\n"
                f"Duration: {note.duration:.2f}s\n"
                f"Velocity: {note.velocity}\n"
                f"Channel: {note.channel}"
            )
            self.items[note.track].append(item)

    def set_track_visible(self, track_id, visible):
        for item in self.items[track_id]:
            item.setVisible(visible)

    def set_time(self, seconds):
        seconds = min(
            max(seconds, 0.0),
            self.duration,
        )
        x = seconds * PX_PER_SEC

        self.cursor.setVisible(True)
        self.cursor.setLine(
            x,
            0,
            x,
            self.scene_height,
        )
        self.time_label.setText(
            f"{format_time(seconds)} / {format_time(self.duration)}"
        )
