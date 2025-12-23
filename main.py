import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QColorDialog,
    QToolBar, QSpinBox, QLabel
)
from PySide6.QtGui import (
    QPainter, QPen, QColor, QPixmap, QAction, QCursor, QIcon
)
from PySide6.QtCore import Qt, QPoint, QRect

# ---------- Tools ----------
class Tool:
    PEN = "Pen"
    ERASER = "Eraser"
    LINE = "Line"
    RECT = "Rectangle"
    ELLIPSE = "Ellipse"

# ---------- Canvas ----------
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
            background-color: #1e1e1e;
            border: 2px solid #333;
            border-radius: 12px;
        """)

    def resizeEvent(self, event):
        if self.pixmap.size() != self.size():
            new_pixmap = QPixmap(self.size())
            new_pixmap.fill(Qt.white)
            painter = QPainter(new_pixmap)
            painter.drawPixmap(0, 0, self.pixmap)
            self.pixmap = new_pixmap

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.save_state()
            self.start_point = event.position().toPoint()
            self.last_point = self.start_point

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            painter = QPainter(self.pixmap)
            pen = QPen(self.pen_color, self.pen_size) if self.tool != Tool.ERASER else QPen(Qt.white, self.pen_size * 3)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)

            current = event.position().toPoint()
            if self.tool in (Tool.PEN, Tool.ERASER):
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

# ---------- Main Window ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("GM-PENCIL")
        self.setWindowIcon(QIcon("logo.ico"))
        self.resize(1400, 800)

        self.canvas = Canvas()
        self.setCentralWidget(self.canvas)

        self.status = QLabel("Ready")
        self.statusBar().addWidget(self.status)

        self.init_toolbar()
        self.apply_dark_theme()

    def init_toolbar(self):
        bar = QToolBar("Tools")
        bar.setMovable(False)
        self.addToolBar(bar)

        def add_action(name, func, tooltip=""):
            a = QAction(name, self)
            if tooltip:
                a.setToolTip(tooltip)
            a.triggered.connect(func)
            bar.addAction(a)

        # Tools
        add_action("✏ Pen", lambda: self.set_tool(Tool.PEN), "Draw with pen")
        add_action("🧽 Eraser", lambda: self.set_tool(Tool.ERASER), "Erase content")
        add_action("📏 Line", lambda: self.set_tool(Tool.LINE), "Draw a line")
        add_action("⬛ Rect", lambda: self.set_tool(Tool.RECT), "Draw rectangle")
        add_action("⚪ Ellipse", lambda: self.set_tool(Tool.ELLIPSE), "Draw ellipse")

        bar.addSeparator()

        # Actions
        add_action("🎨 Color", self.pick_color, "Pick pen color")
        add_action("↩ Undo", self.canvas.undo, "Undo last action")
        add_action("↪ Redo", self.canvas.redo, "Redo last undone")
        add_action("🧹 Clear", self.canvas.clear, "Clear canvas")
        add_action("📂 Open", self.canvas.open_image, "Open image")
        add_action("💾 Save", self.canvas.save_image, "Save image")

        # Brush size
        size_box = QSpinBox()
        size_box.setRange(1, 60)
        size_box.setValue(self.canvas.pen_size)
        size_box.valueChanged.connect(self.set_size)
        bar.addWidget(size_box)

    def set_tool(self, tool):
        self.canvas.tool = tool
        self.status.setText(f"Tool: {tool}")

        cursors = {
            Tool.PEN: Qt.CrossCursor,
            Tool.ERASER: Qt.PointingHandCursor,
            Tool.LINE: Qt.CrossCursor,
            Tool.RECT: Qt.CrossCursor,
            Tool.ELLIPSE: Qt.CrossCursor,
        }
        self.canvas.setCursor(QCursor(cursors[tool]))

    def set_size(self, size):
        self.canvas.pen_size = size
        self.status.setText(f"Brush Size: {size}")

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.canvas.pen_color = color
            self.status.setText(f"Color: {color.name()}")

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
                color: #ffffff;
            }
            QToolBar {
                background: #1f1f1f;
                spacing: 8px;
                padding: 6px;
            }
            QToolButton {
                background: #2a2a2a;
                border-radius: 8px;
                padding: 6px 10px;
            }
            QToolButton:hover {
                background: #3a3a3a;
            }
            QSpinBox {
                background: #2a2a2a;
                border-radius: 6px;
                padding: 4px;
                color: #ffffff;
            }
            QStatusBar {
                background: #1f1f1f;
            }
        """)

# ---------- Run ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("logo.ico"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
