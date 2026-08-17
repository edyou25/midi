from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class TrackPanel(QWidget):
    visibility_changed = Signal(int, bool)
    playback_changed = Signal(int, bool)
    volume_changed = Signal(int, float)
    instrument_changed = Signal(int, int)

    def __init__(self, tracks, color_fn, instruments):
        super().__init__()

        self.show_checks = {}
        self.play_checks = {}
        self.volume_sliders = {}
        self.labels = {}

        self.setFixedWidth(470)

        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel("Show   Play   Volume   Inst   Track / Instrument")
        )

        buttons = QGridLayout()

        show_all = QPushButton("Show All")
        show_none = QPushButton("Show None")
        play_all = QPushButton("Play All")
        play_none = QPushButton("Play None")

        show_all.clicked.connect(
            lambda: self.set_all_visible(True)
        )
        show_none.clicked.connect(
            lambda: self.set_all_visible(False)
        )
        play_all.clicked.connect(
            lambda: self.set_all_playback(True)
        )
        play_none.clicked.connect(
            lambda: self.set_all_playback(False)
        )

        buttons.addWidget(show_all, 0, 0)
        buttons.addWidget(show_none, 0, 1)
        buttons.addWidget(play_all, 1, 0)
        buttons.addWidget(play_none, 1, 1)

        layout.addLayout(buttons)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        rows = QVBoxLayout(content)

        for (
            track_id,
            track_name,
            avg_velocity,
            program,
            is_drum,
        ) in tracks:

            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            # Show / Play
            show_check = QCheckBox()
            play_check = QCheckBox()

            show_check.setChecked(True)
            play_check.setChecked(True)

            # Volume
            volume_slider = QSlider(Qt.Horizontal)
            volume_slider.setRange(0, 127)
            volume_slider.setValue(avg_velocity)
            volume_slider.setFixedWidth(100)

            volume_label = QLabel(str(avg_velocity))
            volume_label.setFixedWidth(28)

            # Instrument
            instrument_box = QComboBox()
            instrument_box.setEditable(True)
            instrument_box.lineEdit().setReadOnly(True)
            instrument_box.setFixedWidth(70)

            for i, instrument_name in enumerate(instruments):
                instrument_box.addItem(
                    f"{i}",
                    i,
                )

            instrument_box.setCurrentIndex(program)

            # Legend
            label = QLabel(
                f"{track_id}: {track_name}"
            )
            label.setStyleSheet(
                f"color: {color_fn(track_id).name()};"
            )

            self.labels[track_id] = label

            # Signals
            show_check.toggled.connect(
                lambda value, tid=track_id:
                    self.visibility_changed.emit(
                        tid,
                        value,
                    )
            )

            play_check.toggled.connect(
                lambda value, tid=track_id:
                    self.playback_changed.emit(
                        tid,
                        value,
                    )
            )

            volume_slider.valueChanged.connect(
                lambda value,
                tid=track_id,
                text=volume_label:
                    self._volume_changed(
                        tid,
                        value,
                        text,
                    )
            )

            if is_drum:
                instrument_box.setEnabled(False)
                instrument_box.lineEdit().setText("Drum")

            else:
                # Collapsed state only shows program number.
                instrument_box.lineEdit().setText(
                    str(program)
                )

                instrument_box.currentIndexChanged.connect(
                    lambda index,
                    tid=track_id,
                    box=instrument_box:
                        self._instrument_changed(
                            tid,
                            index,
                            box,
                            instruments,
                        )
                )

            self.show_checks[track_id] = show_check
            self.play_checks[track_id] = play_check
            self.volume_sliders[track_id] = volume_slider

            row_layout.addWidget(show_check)
            row_layout.addWidget(play_check)
            row_layout.addWidget(volume_slider)
            row_layout.addWidget(volume_label)
            row_layout.addWidget(instrument_box)
            row_layout.addWidget(label, 1)

            rows.addWidget(row)

        rows.addStretch()
        scroll.setWidget(content)

        layout.addWidget(scroll, 1)

        layout.addWidget(
            QLabel(
                "Click: seek   Drag: pan   Ctrl+wheel: zoom"
            )
        )

    def _instrument_changed(
        self,
        track_id,
        index,
        box,
        instruments,
    ):
        program = box.itemData(index)

        if program is None:
            return

        box.lineEdit().setText(
            str(program)
        )

        self.labels[track_id].setText(
            f"{track_id}: {instruments[program]}"
        )

        self.instrument_changed.emit(
            track_id,
            program,
        )

    def _volume_changed(
        self,
        track_id,
        value,
        label,
    ):
        label.setText(str(value))

        self.volume_changed.emit(
            track_id,
            float(value),
        )

    def set_all_visible(
        self,
        visible,
    ):
        for check in self.show_checks.values():
            check.setChecked(visible)

    def set_all_playback(
        self,
        enabled,
    ):
        for check in self.play_checks.values():
            check.setChecked(enabled)