import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QMatrix4x4, QSurfaceFormat, QVector3D, QVector2D
from PySide6.QtOpenGL import (
    QOpenGLShader,
    QOpenGLShaderProgram,
    QOpenGLTexture,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication

from src.spectrum.spectrum_mesh import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_FLOAT,
    GL_TRIANGLES,
    build_triangles,
    make_vertex_buffer,
)
from src.spectrum.spectrum_worker import (
    FFT_FPS,
    FREQ_BINS,
    SpectrumWorker,
)
from src.spectrum.spectrogram_shaders import shader_sources

HISTORY = 256
DISPLAY_SECONDS = HISTORY / FFT_FPS
RENDER_FPS = 60


class SpectrogramGL(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(230)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.program = None
        self.vbo = None
        self.texture = None
        self.gl = None
        self.attr_uv = -1
        self.vertex_count = 0

        self.history = np.zeros((HISTORY, FREQ_BINS), dtype=np.uint8)
        self.pending = None
        self.pitch, self.yaw, self.zoom = 22.0, 0.0, 1.0
        self.last_mouse = None

        self.worker = SpectrumWorker()
        self.worker.spectrum_ready.connect(self._set_pending)
        self.worker.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(round(1000 / RENDER_FPS))

        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self.stop)

    def _set_pending(self, spectrum):
        self.pending = np.asarray(spectrum, dtype=np.float32)

    def _history_image(self):
        data = self.history.tobytes()
        image = QImage(
            data,
            FREQ_BINS,
            HISTORY,
            FREQ_BINS,
            QImage.Format.Format_Grayscale8,
        )
        return image.copy()

    def initializeGL(self):
        context = self.context()
        self.gl = context.functions()

        print(
            "[GL] context:",
            context.format().majorVersion(),
            context.format().minorVersion(),
            context.format().renderableType(),
        )

        self.gl.glClearColor(0.008, 0.008, 0.025, 1.0)
        self.gl.glEnable(GL_DEPTH_TEST)

        is_gles = (
            context.format().renderableType()
            == QSurfaceFormat.RenderableType.OpenGLES
        )
        vertex_source, fragment_source = shader_sources(is_gles)

        self.program = QOpenGLShaderProgram(self)
        if not self.program.addShaderFromSourceCode(
            QOpenGLShader.ShaderTypeBit.Vertex,
            vertex_source,
        ):
            raise RuntimeError(self.program.log())
        if not self.program.addShaderFromSourceCode(
            QOpenGLShader.ShaderTypeBit.Fragment,
            fragment_source,
        ):
            raise RuntimeError(self.program.log())
        if not self.program.link():
            raise RuntimeError(self.program.log())

        self.attr_uv = self.program.attributeLocation("aUV")
        print("[GL] shaders ready")

        vertices = build_triangles(FREQ_BINS, HISTORY)
        self.vertex_count = len(vertices)
        self.vbo = make_vertex_buffer(vertices)
        print("[GL] VBO ready:", self.vertex_count, "vertices")

        self.texture = QOpenGLTexture(
            self._history_image(),
            QOpenGLTexture.MipMapGeneration.DontGenerateMipMaps,
        )
        self.texture.setMinificationFilter(QOpenGLTexture.Filter.Linear)
        self.texture.setMagnificationFilter(QOpenGLTexture.Filter.Linear)
        self.texture.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
        print("[GL] texture ready")

        self.u_mvp = self.program.uniformLocation("uMVP")
        self.u_spectrum = self.program.uniformLocation("uSpectrum")
        self.u_height = self.program.uniformLocation("uHeight")
        self.u_texel = self.program.uniformLocation("uTexel")

    def _consume_pending(self):
        if self.pending is None:
            return

        spectrum, self.pending = self.pending, None

        if spectrum.shape != (FREQ_BINS,):
            return

        self.history[:-1] = self.history[1:]

        self.history[-1] = np.clip(
            spectrum * 255.0,
            0.0,
            255.0,
        ).astype(np.uint8)

        rgba = np.empty(
            (HISTORY, FREQ_BINS, 4),
            dtype=np.uint8,
        )

        rgba[..., 0] = self.history
        rgba[..., 1] = self.history
        rgba[..., 2] = self.history
        rgba[..., 3] = 255

        self.texture.setData(
            QOpenGLTexture.PixelFormat.RGBA,
            QOpenGLTexture.PixelType.UInt8,
            rgba.tobytes(),
        )

    def _mvp(self):
        projection = QMatrix4x4()

        aspect = max(
            self.width() / max(self.height(), 1),
            0.1,
        )

        projection.perspective(
            42.0,
            aspect,
            0.1,
            100.0,
        )

        view = QMatrix4x4()

        view.lookAt(
            QVector3D(
                1.4,   # only slightly from the right
                1.3,   # above
                5.8,   # mainly from the front
            ),
            QVector3D(
                0.0,
                0.0,
                0.0,
            ),
            QVector3D(
                0.0,
                0.1,
                0.0,
            ),
        )

        model = QMatrix4x4()
        model.scale(1.0)

        return projection * view * model
    def paintGL(self):
        try:
            self._paint()
        except BaseException:
            import traceback
            traceback.print_exc()
            self.timer.stop()
    def _paint(self):
        self.gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self.program is None or self.texture is None:
            return

        self._consume_pending()

        self.program.bind()
        # self.program.setUniformValue("uMVP", self._mvp())
        # self.program.setUniformValue("uSpectrum", 0)
        # self.program.setUniformValue("uHeight", 1.7)
        # self.program.setUniformValue(
        #     "uTexel",
        #     1.0 / (FREQ_BINS - 1),
        #     1.0 / (HISTORY - 1),
        # )
        
        self.program.setUniformValue(
            self.u_mvp,
            self._mvp(),
        )

        self.program.setUniformValue1i(
            self.u_spectrum,
            0,
        )

        self.program.setUniformValue1f(
            self.u_height,
            1.7,
        )

        self.program.setUniformValue(
            self.u_texel,
            QVector2D(
                1.0 / (FREQ_BINS - 1),
                1.0 / (HISTORY - 1),
            ),
        )
        self.texture.bind(0)
        self.vbo.bind()

        self.program.enableAttributeArray(self.attr_uv)
        self.program.setAttributeBuffer(
            self.attr_uv,
            GL_FLOAT,
            0,
            2,
            8,
        )

        self.gl.glDrawArrays(
            GL_TRIANGLES,
            0,
            self.vertex_count,
        )

        self.program.disableAttributeArray(self.attr_uv)
        self.vbo.release()
        self.texture.release()
        self.program.release()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse = event.position()

    def mouseMoveEvent(self, event):
        if (
            self.last_mouse is None
            or not event.buttons() & Qt.MouseButton.LeftButton
        ):
            return

        pos = event.position()
        delta = pos - self.last_mouse
        self.last_mouse = pos
        self.yaw += delta.x() * 0.35
        self.pitch = max(
            20.0,
            min(82.0, self.pitch + delta.y() * 0.25),
        )
        self.update()

    def mouseReleaseEvent(self, event):
        self.last_mouse = None

    def wheelEvent(self, event):
        step = event.angleDelta().y() / 120.0
        self.zoom *= 1.08 ** step
        self.zoom = max(0.55, min(2.2, self.zoom))
        self.update()

    def mouseDoubleClickEvent(self, event):
        self.pitch, self.yaw, self.zoom = 22.0, 0.0, 1.0
        self.update()

    def stop(self):
        if self.worker.isRunning():
            self.worker.stop()

    def closeEvent(self, event):
        self.stop()
        super().closeEvent(event)
