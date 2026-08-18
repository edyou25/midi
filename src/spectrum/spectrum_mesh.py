import numpy as np

from PySide6.QtOpenGL import QOpenGLBuffer


GL_FLOAT = 0x1406
GL_TRIANGLES = 0x0004
GL_COLOR_BUFFER_BIT = 0x00004000
GL_DEPTH_BUFFER_BIT = 0x00000100
GL_DEPTH_TEST = 0x0B71


def build_triangles(freq_bins, history):
    x = np.linspace(0.0, 1.0, freq_bins, dtype=np.float32)
    y = np.linspace(0.0, 1.0, history, dtype=np.float32)

    x0, y0 = np.meshgrid(x[:-1], y[:-1])
    x1, y1 = np.meshgrid(x[1:], y[1:])

    p00 = np.stack((x0, y0), axis=-1)
    p10 = np.stack((x1, y0), axis=-1)
    p01 = np.stack((x0, y1), axis=-1)
    p11 = np.stack((x1, y1), axis=-1)

    triangles = np.stack(
        (p00, p01, p10, p10, p01, p11),
        axis=-2,
    )
    return np.ascontiguousarray(
        triangles.reshape(-1, 2),
        dtype=np.float32,
    )


def make_vertex_buffer(vertices):
    vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
    if not vbo.create():
        raise RuntimeError("Failed to create VBO")
    if not vbo.bind():
        raise RuntimeError("Failed to bind VBO")

    data = vertices.tobytes()
    vbo.setUsagePattern(QOpenGLBuffer.UsagePattern.StaticDraw)
    vbo.allocate(data, len(data))
    vbo.release()
    return vbo
