import sys
import os
import ctypes
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar,
    QSpinBox, QLabel, QFileDialog, QColorDialog, QHBoxLayout, QVBoxLayout, QPushButton
)
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap, QCursor, QIcon, QAction, QFont
from PySide6.QtCore import Qt, QPoint, QRect

APP_NAME = "GM-PENCIL"
APP_ID = "com.gm.pencil.ultimate.2025"

# Taskbar icon fix
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
            pen = QPen(self.pen_color, self.pen_size if self.tool != Tool.ERASER else self.pen_size*3)
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.icon = QIcon("logo.ico")
        self.setWindowIcon(self.icon)
        self.resize(1400, 800)

        self.canvas = Canvas()
        self.setCentralWidget(self.canvas)

        self.status = QLabel("Tool: Pen | Size: 4 | Color: #000000")
        self.statusBar().addWidget(self.status)

        self.init_toolbar()
        self.apply_modern_theme()

    def init_toolbar(self):
        bar = QToolBar()
        bar.setMovable(False)
        bar.setStyleSheet("background:#1f1f1f; border-bottom:1px solid #333;")
        self.addToolBar(Qt.TopToolBarArea, bar)

        # Tool Buttons
        self.tool_buttons = {}
        tools = [
            ("✏", Tool.PEN), ("🧽", Tool.ERASER),
            ("📏", Tool.LINE), ("⬛", Tool.RECT), ("⚪", Tool.ELLIPSE)
        ]
        for icon, tool in tools:
            btn = QPushButton(icon)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=tool: self.set_tool(t))
            btn.setStyleSheet(self.button_style())
            bar.addWidget(btn)
            self.tool_buttons[tool] = btn

        bar.addSeparator()

        # Color Picker
        color_btn = QPushButton("🎨")
        color_btn.clicked.connect(self.pick_color)
        color_btn.setStyleSheet(self.button_style())
        bar.addWidget(color_btn)

        # Undo/Redo/Clear/Open/Save
        actions = [
            ("↩", self.canvas.undo), ("↪", self.canvas.redo),
            ("🧹", self.canvas.clear), ("📂", self.canvas.open_image),
            ("💾", self.canvas.save_image)
        ]
        for icon, func in actions:
            btn = QPushButton(icon)
            btn.clicked.connect(func)
            btn.setStyleSheet(self.button_style())
            bar.addWidget(btn)

        # Brush Size
        self.size_box = QSpinBox()
        self.size_box.setRange(1, 60)
        self.size_box.setValue(self.canvas.pen_size)
        self.size_box.valueChanged.connect(self.set_size)
        self.size_box.setStyleSheet("""
            QSpinBox { background:#2a2a2a; color:#fff; border-radius:6px; padding:2px 6px; min-width:50px;}
        """)
        bar.addWidget(self.size_box)

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
            QSpinBox { background:#2a2a2a; color:#fff; border-radius:6px; padding:2px 6px; }
            QStatusBar { background:#1f1f1f; padding:4px; color:#ccc; }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("logo.ico"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
