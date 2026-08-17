from collections import defaultdict

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.midi import (
    extract_notes,
    instrument_name,
    load_midi,
)


PX_PER_SEC = 40
NOTE_H = 7


def format_time(seconds):
    seconds = max(0, int(seconds))

    return (
        f"{seconds // 60:02d}:"
        f"{seconds % 60:02d}"
    )


class PianoRoll(QGraphicsView):
    time_clicked = Signal(float)

    def __init__(self, scene):
        super().__init__(scene)

        self.setDragMode(
            QGraphicsView.ScrollHandDrag
        )

    def wheelEvent(self, event):
        if (
            event.modifiers()
            & Qt.ControlModifier
        ):
            factor = (
                1.15
                if event.angleDelta().y() > 0
                else 1 / 1.15
            )

            self.scale(
                factor,
                1,
            )

        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            point = self.mapToScene(
                event.position().toPoint()
            )

            seconds = max(
                0.0,
                point.x() / PX_PER_SEC,
            )

            self.time_clicked.emit(seconds)

        super().mousePressEvent(event)


class MidiViewer(QWidget):
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
        self.checks = {}

        self.scene = QGraphicsScene(self)
        self.view = PianoRoll(self.scene)

        self.scene_width = max(
            1000,
            self.duration * PX_PER_SEC,
        )

        self.scene_height = (
            128 * NOTE_H
        )

        self.scene.setSceneRect(
            0,
            0,
            self.scene_width,
            self.scene_height,
        )

        self._draw_grid()
        self._draw_notes()

        self.cursor = self.scene.addLine(
            0,
            0,
            0,
            self.scene_height,
            QPen(
                QColor("white"),
                2,
            ),
        )

        self.cursor.setZValue(10)
        self.cursor.setVisible(
            show_cursor
        )

        self.play_button = QPushButton(
            "Play"
        )

        self.play_button.setVisible(
            playback_controls
        )

        self.time_label = QLabel(
            "00:00 / "
            + format_time(
                self.duration
            )
        )

        controls = QHBoxLayout()

        controls.addWidget(
            self.play_button
        )

        controls.addWidget(
            self.time_label
        )

        controls.addStretch()

        main = QVBoxLayout()

        main.addWidget(
            self.view,
            1,
        )

        main.addLayout(
            controls
        )

        layout = QHBoxLayout(self)

        layout.addWidget(
            self._track_panel()
        )

        layout.addLayout(
            main,
            1,
        )

        self.setWindowTitle(
            str(mid_path)
        )

        self.resize(
            1500,
            850,
        )

    @staticmethod
    def _color(track_id):
        return QColor.fromHsv(
            (track_id * 47) % 360,
            180,
            220,
        )

    def _draw_grid(self):
        pen = QPen(
            QColor(
                100,
                100,
                100,
                60,
            )
        )

        for note in range(128):
            y = (
                127 - note
            ) * NOTE_H

            self.scene.addLine(
                0,
                y,
                self.scene_width,
                y,
                pen,
            )

        for sec in range(
            0,
            int(self.duration) + 10,
            10,
        ):
            x = (
                sec * PX_PER_SEC
            )

            self.scene.addLine(
                x,
                0,
                x,
                self.scene_height,
                pen,
            )

            text = self.scene.addText(
                format_time(sec)
            )

            text.setDefaultTextColor(
                QColor(
                    160,
                    160,
                    160,
                )
            )

            text.setPos(
                x + 2,
                0,
            )

    def _draw_notes(self):
        for note in self.notes:
            color = self._color(
                note.track
            )

            x = (
                note.start
                * PX_PER_SEC
            )

            y = (
                127 - note.pitch
            ) * NOTE_H

            width = max(
                1.5,
                note.duration
                * PX_PER_SEC,
            )

            item = self.scene.addRect(
                x,
                y,
                width,
                NOTE_H - 1,
                QPen(
                    color.darker(130)
                ),
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

            self.items[
                note.track
            ].append(item)

    def _track_panel(self):
        panel = QWidget()

        panel.setFixedWidth(
            300
        )

        layout = QVBoxLayout(
            panel
        )

        buttons = QHBoxLayout()

        all_btn = QPushButton(
            "All"
        )

        none_btn = QPushButton(
            "None"
        )

        all_btn.clicked.connect(
            lambda:
            self.set_all(True)
        )

        none_btn.clicked.connect(
            lambda:
            self.set_all(False)
        )

        buttons.addWidget(
            all_btn
        )

        buttons.addWidget(
            none_btn
        )

        layout.addLayout(
            buttons
        )

        scroll = QScrollArea()

        scroll.setWidgetResizable(
            True
        )

        content = QWidget()
        tracks = QVBoxLayout(
            content
        )

        for track_id in sorted(
            self.items
        ):
            name = instrument_name(
                self.mid.tracks[
                    track_id
                ]
            )

            check = QCheckBox(
                f"{track_id}: {name}"
            )

            check.setChecked(True)

            check.setStyleSheet(
                "QCheckBox {"
                f"color: "
                f"{self._color(track_id).name()};"
                "}"
            )

            check.toggled.connect(
                lambda visible,
                tid=track_id:
                self.set_track(
                    tid,
                    visible,
                )
            )

            self.checks[
                track_id
            ] = check

            tracks.addWidget(
                check
            )

        tracks.addStretch()

        scroll.setWidget(
            content
        )

        layout.addWidget(
            QLabel(
                "Tracks / Instruments"
            )
        )

        layout.addWidget(
            scroll,
            1,
        )

        layout.addWidget(
            QLabel(
                "Left click: seek"
                "   Drag: pan"
                "   Ctrl+wheel: zoom"
            )
        )

        return panel

    def set_track(
        self,
        track_id,
        visible,
    ):
        for item in self.items[
            track_id
        ]:
            item.setVisible(
                visible
            )

    def set_all(
        self,
        visible,
    ):
        for check in (
            self.checks.values()
        ):
            check.setChecked(
                visible
            )

    def set_time(
        self,
        seconds,
    ):
        seconds = min(
            max(
                seconds,
                0.0,
            ),
            self.duration,
        )

        x = (
            seconds
            * PX_PER_SEC
        )

        self.cursor.setVisible(
            True
        )

        self.cursor.setLine(
            x,
            0,
            x,
            self.scene_height,
        )

        self.time_label.setText(
            f"{format_time(seconds)}"
            f" / "
            f"{format_time(self.duration)}"
        )