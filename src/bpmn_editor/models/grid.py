from PyQt5.QtWidgets import (QGraphicsScene)
from PyQt5.QtGui import (QPainter, QColor, QBrush, QPen)
from PyQt5.QtCore import (Qt, QLineF)
import logging
logger = logging.getLogger(__name__)


class GridScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_visible = True
        self.minor_spacing = 20  # Espaçamento menor (20px)
        self.major_spacing = 100  # Espaçamento maior (100px)
        self.setBackgroundBrush(QBrush(Qt.white))
        
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

