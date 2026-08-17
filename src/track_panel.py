from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class TrackPanel(QWidget):
    visibility_changed = Signal(int, bool)
    playback_changed = Signal(int, bool)

    def __init__(self, tracks, color_fn):
        super().__init__()
        self.show_checks = {}
        self.play_checks = {}

        self.setFixedWidth(360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Show   Play   Track / Instrument"))

        buttons = QHBoxLayout()
        show_all = QPushButton("Show All")
        show_none = QPushButton("Show None")
        show_all.clicked.connect(lambda: self.set_all_visible(True))
        show_none.clicked.connect(lambda: self.set_all_visible(False))
        buttons.addWidget(show_all)
        buttons.addWidget(show_none)
        layout.addLayout(buttons)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        rows = QVBoxLayout(content)

        for track_id, name in tracks:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            show_check = QCheckBox()
            play_check = QCheckBox()
            show_check.setChecked(True)
            play_check.setChecked(True)
            show_check.setToolTip("Show track")
            play_check.setToolTip("Play track")

            label = QLabel(f"{track_id}: {name}")
            label.setStyleSheet(
                f"color: {color_fn(track_id).name()};"
            )

            show_check.toggled.connect(
                lambda value, tid=track_id:
                    self.visibility_changed.emit(tid, value)
            )
            play_check.toggled.connect(
                lambda value, tid=track_id:
                    self.playback_changed.emit(tid, value)
            )

            self.show_checks[track_id] = show_check
            self.play_checks[track_id] = play_check

            row_layout.addWidget(show_check)
            row_layout.addWidget(play_check)
            row_layout.addWidget(label, 1)
            rows.addWidget(row)

        rows.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        layout.addWidget(
            QLabel("Click: seek   Drag: pan   Ctrl+wheel: zoom")
        )

    def set_all_visible(self, visible):
        for check in self.show_checks.values():
            check.setChecked(visible)
