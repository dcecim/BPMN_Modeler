from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtCore import Qt, QRectF, QLineF
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush

class GridScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.setSceneRect(QRectF(0, 0, 800, 600))
        self.grid_visible = True
        self.minor_spacing = 20
        self.major_spacing = 100
        self.setBackgroundBrush(QBrush(Qt.white))

    def selectedItems(self):
        try:
            selected = []
            for item in super().selectedItems():
                try:
                    if item and not item.isDeleted():
                        selected.append(item)
                except (RuntimeError, AttributeError):
                    continue
            return selected
        except Exception:
            return []

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        if not self.grid_visible:
            return

        # Configurações iniciais
        painter.setRenderHint(QPainter.Antialiasing, False)
        left = int(rect.left()) - (int(rect.left()) % self.minor_spacing)
        top = int(rect.top()) - (int(rect.top()) % self.minor_spacing)

        # Linhas menores
        minor_pen = QPen(QColor(220, 220, 220), 0.5)
        painter.setPen(minor_pen)
        
        # Linhas horizontais
        y = top
        while y < rect.bottom():
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += self.minor_spacing
            
        # Linhas verticais
        x = left
        while x < rect.right():
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += self.minor_spacing

        # Linhas principais
        major_pen = QPen(QColor(200, 200, 200), 1)
        painter.setPen(major_pen)
        
        # Linhas horizontais principais
        y = top
        while y < rect.bottom():
            if y % self.major_spacing == 0:
                painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += self.minor_spacing
            
        # Linhas verticais principais
        x = left
        while x < rect.right():
            if x % self.major_spacing == 0:
                painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += self.minor_spacing

