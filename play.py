import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from plot import create_viewer
from src.config import load_config
from src.player import MidiPlayer


def main():
    cfg = load_config()

    app = QApplication(sys.argv)

    viewer = create_viewer(
        show_cursor=True,
        playback_controls=True,
    )
    viewer.show()

    player = MidiPlayer(
        cfg["mid_path"],
        cfg["soundfont"],
        cfg.get("audio_driver", "pulseaudio"),
    )
    player.start()

    def toggle_play():
        player.toggle()

        viewer.play_button.setText(
            "Play" if player.paused else "Pause"
        )

    def seek(seconds):
        player.seek(seconds)
        viewer.set_time(seconds)

    def update():
        viewer.set_time(player.position)

        if player.paused:
            viewer.play_button.setText("Play")

    viewer.play_button.clicked.connect(toggle_play)
    viewer.view.time_clicked.connect(seek)

    timer = QTimer()
    timer.timeout.connect(update)
    timer.start(50)

    app.aboutToQuit.connect(player.stop)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()