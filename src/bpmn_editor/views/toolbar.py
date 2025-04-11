import sys
from PyQt5.QtWidgets import (QPushButton, QStyle, QVBoxLayout, QWidget) 
from PyQt5.QtGui import (QDrag, QPainter, QColor, QPixmap, QBrush)
from PyQt5.QtCore import (Qt, QMimeData, QPoint)

import logging
logger = logging.getLogger(__name__)

 
class DragButton(QPushButton):
    def __init__(self, element_type, parent):
        super().__init__(parent)
        self.element_type = element_type
        self.setFixedSize(120, 40)
        self.drag_start_position = QPoint()  # Adicionado

    # Remova todos os handlers de mouseMove/mouseRelease (estão no lugar errado)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if (event.buttons() == Qt.LeftButton and 
            (event.pos() - self.drag_start_position).manhattanLength() > 5):
            
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setData("application/x-bpmn-element", self.element_type.encode())
            drag.setMimeData(mime_data)
            
            # Configurar visualização do drag
            pixmap = QPixmap(100, 60)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QColor('#2196F3' if self.element_type == 'task' else '#4CAF50'))
            painter.drawRoundedRect(0, 0, 100, 60, 10, 10)
            painter.end()
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(50, 30))
            
            drag.exec_(Qt.CopyAction)
      
class BPMNPalette(QWidget):
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.drag_start_position = None
        self.drag_element_type = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        elements = [
            ('Evento Início', 'start', '#start_event'),
            ('Tarefa', 'task', '#task'),
            ('Gateway', 'gateway', '#gateway')
        ]

        for text, element_type, icon in elements:
            btn = DragButton(element_type, self)  # ← Usar botão customizado
            btn.setText(text)
            btn.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
            btn.setFocusPolicy(Qt.NoFocus) 
            layout.addWidget(btn)
                
        # print("Paleta visível?", self.palette.isVisible())  # Deve ser True
        layout.addStretch()

    def mouse_press(self, event, element_type):
        print("Mouse press iniciado") 
        self.drag_element_type = element_type
        self.drag_start_position = event.pos()
        self.setCursor(Qt.OpenHandCursor)


    def mouse_move(self, event):
        if not (event.buttons() & Qt.LeftButton):  # ← Novo check
            return
        
        print("Drag iniciado") 
        if (event.buttons() == Qt.LeftButton and 
            (event.pos() - self.drag_start_position).manhattanLength() > 3
            and self.drag_element_type is not None):  # Nova condição
            
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setData(
                "application/x-bpmn-element", 
                self.drag_element_type.encode()
            )
            drag.setMimeData(mime_data)  
            
            # Configurações restantes
            hotspot = QPoint(15, 15)
            drag.setPixmap(self.create_drag_pixmap())
            drag.setHotSpot(hotspot)
            
            # drag.exec_(Qt.CopyAction)
            action = drag.exec_(Qt.CopyAction | Qt.MoveAction)
            print("Ação do drag concluída:", action)  # Deve retornar 1 (CopyAction)
            self.drag_element_type = None  # Resetar após o drag

    def create_drag_pixmap(self):
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(self.get_element_color(self.drag_element_type)))
        painter.drawEllipse(0, 0, 40, 40)
        painter.end()
        return pixmap

    def get_element_color(self, element_type):
        colors = {
            'start': QColor('#4CAF50'),
            'task': QColor('#2196F3'),
            'gateway': QColor('#FF9800')
        }
        return colors.get(element_type, QColor('#607D8B'))

