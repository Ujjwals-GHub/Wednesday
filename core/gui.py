import sys
import math
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QRadialGradient
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve

class GUIBridge(QObject):
    """Thread-safe signal dispatcher between Python background threads and Qt."""
    show_signal = pyqtSignal()
    hide_signal = pyqtSignal()
    close_signal = pyqtSignal()
    label_signal = pyqtSignal(str)

class WaveOrbWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.w, self.h = 280, 280
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.w - 20
        y = screen.height() - self.h - 60
        self.setGeometry(x, y, self.w, self.h)
        
        self.phase = 0.0
        self.particle_phase = 0.0
        self.label = "WEDNESDAY"
        
        layer_specs = [
            ("#4B0082", 64, 150),
            ("#8A2BE2", 76, 170),
            ("#BA55D3", 88, 190),
            ("#E0B0FF", 100, 215),
        ]
        self.pens = []
        self.layer_radii = []
        for hex_color, radius, alpha in layer_specs:
            color = QColor(hex_color)
            color.setAlpha(alpha)
            pen = QPen(color, 2.4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            self.pens.append(pen)
            self.layer_radii.append(radius)
            
        self.text_color = QColor("#E0B0FF")
        self.text_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        
        self.particles = [
            {
                "radius": 88 + (i * 7) % 28,
                "speed": 0.5 + i * 0.13,
                "size": 2 + (i % 3),
                "offset": i * 47,
            }
            for i in range(7)
        ]
        
        self._fade_anim = None
        
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.update_frame)

    def set_label(self, text):
        self.label = text.upper()
        self.update()

    def update_frame(self):
        self.phase -= 0.08
        self.particle_phase += 0.02
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx, cy = self.w / 2, self.h / 2
        
        bloom_pulse = 3 * math.sin(self.phase * 0.12)
        for radius, alpha in ((128, 10), (108, 16), (92, 24)):
            r = radius + bloom_pulse
            bloom = QRadialGradient(cx, cy, r)
            bloom.setColorAt(0.0, QColor(186, 85, 211, alpha))
            bloom.setColorAt(1.0, QColor(186, 85, 211, 0))
            painter.setBrush(bloom)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
        
        gradient = QRadialGradient(cx, cy, 110)
        gradient.setColorAt(0.0, QColor(26, 0, 44, 190))
        gradient.setColorAt(0.65, QColor(42, 8, 69, 120))
        gradient.setColorAt(1.0, QColor(75, 0, 130, 0))
        
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
        
        for p in self.particles:
            angle = self.particle_phase * p["speed"] + p["offset"]
            wobble = 6 * math.sin(self.particle_phase * 2 + p["offset"])
            r = p["radius"] + wobble
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle) * 0.9
            twinkle = 90 + int(90 * (0.5 + 0.5 * math.sin(self.particle_phase * 3 + p["offset"])))
            painter.setBrush(QColor(224, 176, 255, twinkle))
            painter.setPen(Qt.PenStyle.NoPen)
            size = p["size"]
            painter.drawEllipse(int(x - size), int(y - size), size * 2, size * 2)
        
        core_radius = 20 + math.sin(self.phase * 0.15) * 5
        core = QRadialGradient(cx, cy, core_radius)
        core.setColorAt(0.0, QColor(255, 255, 255, 200))
        core.setColorAt(0.4, QColor(224, 176, 255, 140))
        core.setColorAt(1.0, QColor(224, 176, 255, 0))
        painter.setBrush(core)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            int(cx - core_radius), int(cy - core_radius),
            int(core_radius * 2), int(core_radius * 2)
        )
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i, (pen, base_radius) in enumerate(zip(self.pens, self.layer_radii)):
            painter.setPen(pen)
            
            amplitude = 8 + math.sin(self.phase * 0.5 + i) * 10
            k = 3 + i
            
            points = []
            for angle_deg in range(0, 360, 6):
                theta = math.radians(angle_deg)
                r = base_radius + math.sin(k * theta + self.phase + i * 1.5) * amplitude
                x = cx + r * math.cos(theta)
                y = cy + r * math.sin(theta)
                points.append((x, y))
            
            path = QPainterPath()
            n = len(points)
            start_x = (points[-1][0] + points[0][0]) / 2
            start_y = (points[-1][1] + points[0][1]) / 2
            path.moveTo(start_x, start_y)
            for j in range(n):
                px, py = points[j]
                nx, ny = points[(j + 1) % n]
                mid_x, mid_y = (px + nx) / 2, (py + ny) / 2
                path.quadTo(px, py, mid_x, mid_y)
            path.closeSubpath()
            
            painter.drawPath(path)
            
        painter.setFont(self.text_font)
        glow_alpha = 200 + int(55 * math.sin(self.phase * 0.15))
        text_color = QColor(self.text_color)
        text_color.setAlpha(max(0, min(255, glow_alpha)))
        painter.setPen(text_color)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.label)

    def start_animation(self):
        self.setWindowOpacity(0.0)
        self.show()
        self.timer.start()
        self._fade(1.0, 220)

    def stop_animation(self):
        anim = self._fade(0.0, 180)

        def _on_faded():
            # Only hide if a newer fade (e.g. show() called again right
            # after this hide()) hasn't already replaced this animation.
            if self._fade_anim is anim:
                self.timer.stop()
                self.hide()

        anim.finished.connect(_on_faded)

    def _fade(self, target, duration_ms):
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(duration_ms)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_anim = anim
        anim.start()
        return anim

    def close_app(self):
        self.timer.stop()
        self.close()
        QApplication.instance().quit()


class AssistantGUI:
    def __init__(self):
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
            
        self.bridge = GUIBridge()
        self.widget = WaveOrbWidget()
        
        self.bridge.show_signal.connect(self.widget.start_animation)
        self.bridge.hide_signal.connect(self.widget.stop_animation)
        self.bridge.close_signal.connect(self.widget.close_app)
        self.bridge.label_signal.connect(self.widget.set_label)

    def show(self):
        self.bridge.show_signal.emit()

    def hide(self):
        self.bridge.hide_signal.emit()

    def close(self):
        self.bridge.close_signal.emit()

    def set_label(self, text):
        """Optional: gui.set_label('Listening') to update the HUD's status word.
        Routed through the bridge so it's safe to call from a background thread."""
        self.bridge.label_signal.emit(text)

    def run(self):
        self.app.exec()