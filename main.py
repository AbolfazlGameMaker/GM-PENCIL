import sys
import ctypes
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QSlider,
    QLabel, QFileDialog, QColorDialog, QPushButton, QHBoxLayout, QVBoxLayout
)
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap, QCursor, QIcon
from PySide6.QtCore import Qt, QPoint, QRect
from collections import deque

APP_NAME = "GM-PENCIL"
APP_ID = "com.gm.pencil.ultimate.2025"

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except:
    pass

class Tool:
    PEN = "Pen"
    ERASER = "Eraser"
    LINE = "Line"
    RECT = "Rectangle"
    ELLIPSE = "Ellipse"
    BUCKET = "Bucket"

class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(1000, 600)
        self.setCursor(Qt.CrossCursor)
        self.pixmap = QPixmap(self.size())
        self.pixmap.fill(Qt.white)
        self.history = []
        self.redo_stack = []
        self.pen_color = QColor("#000000")
        self.pen_size = 4
        self.tool = Tool.PEN
        self.start_point = QPoint()
        self.last_point = QPoint()
        self.setStyleSheet("""
            background-color:#1e1e1e;
            border:2px solid #333;
            border-radius:12px;
        """)

    def resizeEvent(self, event):
        if self.pixmap.size() != self.size():
            new_pixmap = QPixmap(self.size())
            new_pixmap.fill(Qt.white)
            painter = QPainter(new_pixmap)
            painter.drawPixmap(0, 0, self.pixmap)
            self.pixmap = new_pixmap
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.save_state()
            self.start_point = event.position().toPoint()
            self.last_point = self.start_point
            if self.tool == Tool.BUCKET:
                self.bucket_fill(self.start_point)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            painter = QPainter(self.pixmap)
            if self.tool in (Tool.PEN, Tool.ERASER):
                pen = QPen(self.pen_color if self.tool != Tool.ERASER else QColor("#ffffff"),
                           self.pen_size if self.tool != Tool.ERASER else self.pen_size*3)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                current = event.position().toPoint()
                painter.drawLine(self.last_point, current)
                self.last_point = current
                self.update()

    def mouseReleaseEvent(self, event):
        painter = QPainter(self.pixmap)
        painter.setPen(QPen(self.pen_color, self.pen_size))
        end = event.position().toPoint()
        if self.tool == Tool.LINE:
            painter.drawLine(self.start_point, end)
        elif self.tool == Tool.RECT:
            painter.drawRect(QRect(self.start_point, end))
        elif self.tool == Tool.ELLIPSE:
            painter.drawEllipse(QRect(self.start_point, end))
        self.update()

    def save_state(self):
        self.history.append(self.pixmap.copy())
        if len(self.history) > 50:
            self.history.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if self.history:
            self.redo_stack.append(self.pixmap.copy())
            self.pixmap = self.history.pop()
            self.update()

    def redo(self):
        if self.redo_stack:
            self.history.append(self.pixmap.copy())
            self.pixmap = self.redo_stack.pop()
            self.update()

    def clear(self):
        self.save_state()
        self.pixmap.fill(Qt.white)
        self.update()

    def save_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG (*.png);;JPG (*.jpg)")
        if path:
            self.pixmap.save(path)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.bmp)")
        if path:
            loaded = QPixmap(path)
            if not loaded.isNull():
                self.save_state()
                self.pixmap = loaded.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.update()

    def bucket_fill(self, start_point):
        img = self.pixmap.toImage()
        width = img.width()
        height = img.height()
        target_color = img.pixelColor(start_point)
        replacement_color = self.pen_color
        if target_color == replacement_color:
            return

        def similar(c1, c2, tol=10):
            return (abs(c1.red() - c2.red()) <= tol and
                    abs(c1.green() - c2.green()) <= tol and
                    abs(c1.blue() - c2.blue()) <= tol)

        stack = [start_point]
        while stack:
            p = stack.pop()
            x, y = p.x(), p.y()
            if x < 0 or x >= width or y < 0 or y >= height:
                continue
            if not similar(img.pixelColor(x, y), target_color):
                continue

            left = x
            while left > 0 and similar(img.pixelColor(left - 1, y), target_color):
                left -= 1
            right = x
            while right < width - 1 and similar(img.pixelColor(right + 1, y), target_color):
                right += 1

            for i in range(left, right + 1):
                img.setPixelColor(i, y, replacement_color)
                if y > 0 and similar(img.pixelColor(i, y - 1), target_color):
                    stack.append(QPoint(i, y - 1))
                if y < height - 1 and similar(img.pixelColor(i, y + 1), target_color):
                    stack.append(QPoint(i, y + 1))

        self.pixmap.convertFromImage(img)
        self.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GM-PENCIL")
        self.setWindowIcon(QIcon("logo.ico"))
        self.resize(1400, 800)

        self.canvas = Canvas()
        self.setCentralWidget(self.canvas)

        self.status = QLabel()
        self.statusBar().addWidget(self.status)
        self.update_status()

        self.init_toolbar()
        self.apply_modern_theme()

    def init_toolbar(self):
        bar = QToolBar()
        bar.setMovable(False)
        bar.setStyleSheet("background:#1f1f1f; border-bottom:1px solid #333;")
        self.addToolBar(Qt.TopToolBarArea, bar)

        self.tool_buttons = {}
        tools = [
            ("✏", Tool.PEN, "Draw with pen"),
            ("🧽", Tool.ERASER, "Erase"),
            ("📏", Tool.LINE, "Draw line"),
            ("⬛", Tool.RECT, "Draw rectangle"),
            ("⚪", Tool.ELLIPSE, "Draw ellipse"),
            ("🪣", Tool.BUCKET, "Fill area")
        ]
        for icon, tool, tooltip in tools:
            btn = QPushButton(icon)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda checked, t=tool: self.set_tool(t))
            btn.setStyleSheet(self.button_style())
            bar.addWidget(btn)
            self.tool_buttons[tool] = btn

        bar.addSeparator()

        color_btn = QPushButton("🎨")
        color_btn.setToolTip("Pick color")
        color_btn.clicked.connect(self.pick_color)
        color_btn.setStyleSheet(self.button_style())
        bar.addWidget(color_btn)

        actions = [
            ("↩", self.canvas.undo, "Undo"),
            ("↪", self.canvas.redo, "Redo"),
            ("🧹", self.canvas.clear, "Clear"),
            ("📂", self.canvas.open_image, "Open image"),
            ("💾", self.canvas.save_image, "Save image")
        ]
        for icon, func, tooltip in actions:
            btn = QPushButton(icon)
            btn.setToolTip(tooltip)
            btn.clicked.connect(func)
            btn.setStyleSheet(self.button_style())
            bar.addWidget(btn)

        layout = QVBoxLayout()
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 60)
        self.size_slider.setValue(self.canvas.pen_size)
        self.size_slider.valueChanged.connect(self.set_size)
        self.size_slider.setToolTip("Brush size")
        layout.addWidget(QLabel("Brush size"))
        layout.addWidget(self.size_slider)
        container = QWidget()
        container.setLayout(layout)
        bar.addWidget(container)

        self.update_tool_buttons()

    def button_style(self):
        return """
            QPushButton {
                background:#2a2a2a; color:#fff; border-radius:8px; font-size:16px;
                padding:6px;
            }
            QPushButton:hover { background:#3a3a3a; }
            QPushButton:checked { background:#1a73e8; }
        """

    def set_tool(self, tool):
        self.canvas.tool = tool
        self.update_tool_buttons()
        self.update_status()

    def update_tool_buttons(self):
        for t, btn in self.tool_buttons.items():
            btn.setChecked(self.canvas.tool == t)

    def set_size(self, size):
        self.canvas.pen_size = size
        self.update_status()

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.canvas.pen_color = color
            self.update_status()

    def update_status(self):
        self.status.setText(f"Tool: {self.canvas.tool} | Size: {self.canvas.pen_size} | Color: {self.canvas.pen_color.name()}")

    def apply_modern_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color:#121212; color:#ffffff; }
            QToolBar { background:#1f1f1f; spacing:6px; padding:4px; }
            QSlider::groove:horizontal { height:6px; background:#333; border-radius:3px; }
            QSlider::handle:horizontal { background:#1a73e8; width:14px; margin:-4px 0; border-radius:7px; }
            QStatusBar { background:#1f1f1f; padding:4px; color:#ccc; }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("logo.ico"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
