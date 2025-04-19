import sys
from PyQt5.QtWidgets import (QPushButton, QStyle, QVBoxLayout, QWidget, 
                             QDockWidget, QApplication) 
from PyQt5.QtGui import (QIcon, QDrag, QPainter, QColor, QPixmap, QBrush)
from PyQt5.QtCore import (Qt, QMimeData, QPoint)

import logging
logger = logging.getLogger(__name__)

 
class DragButton(QPushButton):
    def __init__(self, icon, text, element_type, parent=None, color=None):
        if isinstance(icon, str):
            icon = QIcon(icon)

        super().__init__(icon, text, parent)
        self.element_type = element_type
        self.color = color if color else self.get_default_color(element_type)  # Armazenar a cor como atributo
        self.setAcceptDrops(False)
        self.setFixedSize(80, 80)
        # Se uma cor foi fornecida, aplicá-la ao estilo do botão
        if color:
            self.setStyleSheet(f"background-color: {color};")

    def setCanvasMode(self):
        # Se for um botão de conexão
        if self.element_type == "connection":
            self.canvas.setMode("connection")
        else:
            # Para botões de elementos, configurar para modo de criação
            self.canvas.setMode("create")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
            
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        # Cria o drag com feedback visual
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData("application/x-bpmn-element", self.element_type.encode())
        drag.setMimeData(mime_data)
        
        # Cria um pixmap de preview
        pixmap = QPixmap(100, 60)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(self.color))
        
        if self.element_type == 'gateway':
            painter.drawPolygon([
                QPoint(50, 0), QPoint(100, 30),
                QPoint(50, 60), QPoint(0, 30)
            ])
        else:
            painter.drawRoundedRect(10, 10, 80, 40, 5, 5)
            
        painter.end()
        drag.setPixmap(pixmap)
        drag.exec_(Qt.CopyAction)

    def setCanvas(self, canvas):
        self.canvas = canvas
        # Conectar o clique do botão à mudança de modo
        self.clicked.connect(self.updateCanvasMode)
    
    def updateCanvasMode(self):
        if hasattr(self, 'canvas'):
            if self.element_type == "connection":
                self.canvas.mode = "connection"
                self.canvas.setCursor(Qt.CrossCursor)
            elif self.element_type == "select":
                self.canvas.mode = "select"
                self.canvas.setCursor(Qt.ArrowCursor)
            else:
                self.canvas.mode = "create"
                self.canvas.setCursor(Qt.PointingHandCursor)

    def get_default_color(self, element_type):
        colors = {
            'start': '#4CAF50',
            'task': '#2196F3',
            'gateway': '#FF9800',
            'select': '#607D8B',
            'connection': '#607D8B'
        }
        return colors.get(element_type, '#607D8B')

class BPMNPalette(QDockWidget):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.buttons = []
        self.setup_palette()

        # Configurar os botões para usar o canvas
        for button in self.buttons:
            button.setCanvas(self.canvas)

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

    def setup_palette(self):
        logging.debug("Configurando paleta de botões")
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Adicionar botões de elementos BPMN
        start_btn = DragButton(
            icon=QIcon("C:/Aplicações Python/Prodesso de modelagem de fluxo/src/bpmn_editor/start.png"),
            text="Início",
            element_type="start"
        )
        self.buttons.append(start_btn)
        layout.addWidget(start_btn)
        
        task_btn = DragButton(
            icon=QIcon("C:/Aplicações Python/Prodesso de modelagem de fluxo/src/bpmn_editor/task.png"),
            text="Tarefa",
            element_type="task"
        )
        self.buttons.append(task_btn)
        layout.addWidget(task_btn)
        
        gateway_btn = DragButton(
            icon=QIcon("C:/Aplicações Python/Prodesso de modelagem de fluxo/src/bpmn_editor/gateway.png"),
            text="Gateway",
            element_type="gateway"
        )
        self.buttons.append(gateway_btn)
        layout.addWidget(gateway_btn)
        
        # Adicionar botão de conexão
        connection_btn = DragButton(
            icon=QIcon("C:/Aplicações Python/Prodesso de modelagem de fluxo/src/bpmn_editor/connection.png"),
            text="Conexão",
            element_type="connection"
        )
        self.buttons.append(connection_btn)
        layout.addWidget(connection_btn)
        
        # Definir o container como widget central
        self.setWidget(container)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.setFixedWidth(200)


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

