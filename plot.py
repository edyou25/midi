import sys

from PySide6.QtWidgets import QApplication

from src.config import load_config
from src.plotter import MidiViewer


def create_viewer(
    show_cursor=False,
    playback_controls=False,
):
    cfg = load_config()

    return MidiViewer(
        cfg["mid_path"],
        show_cursor=show_cursor,
        playback_controls=playback_controls,
    )


def main():
    app = QApplication(sys.argv)

    viewer = create_viewer()
    viewer.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()