import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, 
                            QLabel, QDialog, QHBoxLayout, QLineEdit, QTextEdit, QSplitter,
                            QGraphicsView, QGraphicsScene, QGraphicsRectItem, QStatusBar,
                            QToolBar, QAction, QFileDialog, QMenu, QGraphicsLineItem, QStyle,
                            QGraphicsItem)

from PyQt5.QtGui import QIcon, QDrag, QPainter, QColor, QBrush, QFont, QPixmap, QPen
from PyQt5.QtCore import Qt, QMimeData, QPoint, QPointF, QSize

import traceback

def excepthook(exc_type, exc_value, exc_traceback):
    traceback.print_exception(exc_type, exc_value, exc_traceback)
sys.excepthook = excepthook

class BPMNElement(QGraphicsRectItem):
    def __init__(self, element_type, pos):
        super().__init__(0, 0, 100, 80)
        self.connections = []  # Lista de conexões
        self.element_type = element_type
        self.name = "Novo Elemento"
        self.description = ""
        self.setPos(pos)
        self.setBrush(QBrush(self.get_color()))
        self.setFlags(QGraphicsRectItem.ItemIsMovable | 
                    QGraphicsRectItem.ItemIsSelectable |
                    QGraphicsRectItem.ItemSendsGeometryChanges)

    def get_color(self):
        colors = {
            'start': QColor('#4CAF50'),
            'task': QColor('#2196F3'),
            'gateway': QColor('#FF9800')
        }
        return colors.get(self.element_type, QColor('#607D8B'))

    def paint(self, painter, option, widget):
        painter.setFont(QFont("Arial", 10))  
        super().paint(painter, option, widget)
        painter.drawText(self.rect(), Qt.AlignCenter, self.name)

    # Adicionar na classe BPMNElement:
    def set_editor_reference(self, editor_ref):
        self.editor_ref = editor_ref

    # Modificar o método:
    def mouseDoubleClickEvent(self, event):
        if hasattr(self, 'editor_ref'):
            self.editor_ref.properties.update_properties(self)
            self.editor_ref.properties.show()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for connection in self.connections:
                connection.update_position()
        return super().itemChange(change, value)

class BPMNCanvas(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)
        self.elements = []
        self.setSceneRect(0, 0, 800, 600)  # Adicionar esta linha
        self.setMinimumSize(400, 300)      # Garantir tamanho mínimo
        self.editor_ref = None  # Inicializar atributo

    def add_element(self, element_type, pos):
        element = BPMNElement(element_type, pos)
        element.set_editor_reference(self.editor_ref)  # Nova linha
        self.scene.addItem(element)
        self.elements.append(element)
        return element

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.source() in self.elements:
            # Lógica para conexão entre elementos
            source = event.source()
            target = self.itemAt(event.pos())
            if isinstance(target, BPMNElement):
                self.create_connection(source, target)
        else:
            pos = self.mapToScene(event.pos())
            element_type = event.mimeData().text()
            self.add_element(element_type, pos)
            event.acceptProposedAction()
            super().dropEvent(event)

    def create_connection(self, source, target):
        connection = BPMNConnection(source, target)
        self.scene.addItem(connection)
        source.connections.append(connection)
        target.connections.append(connection)

class BPMNConnection(QGraphicsLineItem):
    def __init__(self, start_element, end_element):
        super().__init__()
        self.setPen(QPen(Qt.darkGray, 2, Qt.DashLine))
        self.start_element = start_element
        self.end_element = end_element
        self.update_position()
    
    def update_position(self):
        start_pos = self.start_element.sceneBoundingRect().center()
        end_pos = self.end_element.sceneBoundingRect().center()
        self.setLine(start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y())

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
            btn = QPushButton(text, self)
            btn.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
            btn.setFixedSize(120, 40)
            btn.mousePressEvent = lambda event, et=element_type: self.mouse_press(event, et)
            btn.mouseMoveEvent = self.mouse_move
            layout.addWidget(btn)
            
        layout.addStretch()

    def mouse_press(self, event, element_type):
        self.drag_element_type = element_type
        self.drag_start_position = event.pos()
        self.setCursor(Qt.OpenHandCursor)

    def mouse_move(self, event):
        if (event.buttons() == Qt.LeftButton and 
            (event.pos() - self.drag_start_position).manhattanLength() > 5):
            
            self.setCursor(Qt.ClosedHandCursor)
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.drag_element_type)
            drag.setMimeData(mime_data)
            
            pixmap = QPixmap(100, 80)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QBrush(self.get_element_color(self.drag_element_type)))
            painter.drawRect(20, 20, 60, 40)
            painter.end()
            
            drag.setPixmap(pixmap)
            # Calcular offset relativo
            drag_offset = event.pos()  # Usar posição relativa ao botão
            drag.setHotSpot(drag_offset)
            drag.exec_(Qt.CopyAction)
            self.setCursor(Qt.ArrowCursor)
            drag_offset = event.pos() - QPoint(0,0)  # Offset relativo corrigido
            drag.setHotSpot(drag_offset)
            drag.exec_(Qt.CopyAction)
            
            self.setCursor(Qt.ArrowCursor)

    def get_element_color(self, element_type):
        colors = {
            'start': QColor('#4CAF50'),
            'task': QColor('#2196F3'),
            'gateway': QColor('#FF9800')
        }
        return colors.get(element_type, QColor('#607D8B'))

class PropertiesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_element = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.name_label = QLabel("Nome:")
        self.name_input = QLineEdit()
        self.desc_label = QLabel("Descrição:")
        self.desc_input = QTextEdit()
        
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.desc_label)
        layout.addWidget(self.desc_input)
        layout.addStretch()

        # Conexões
        self.name_input.textChanged.connect(self.update_element_name)
        self.desc_input.textChanged.connect(self.update_element_desc)

    def update_properties(self, element):
        self.current_element = element
        self.name_input.setText(element.name)
        self.desc_input.setPlainText(element.description)

    def update_element_name(self, text):
        if self.current_element:
            self.current_element.name = text
            self.current_element.update()

    def update_element_desc(self):
        if self.current_element:
            self.current_element.description = self.desc_input.toPlainText()

class BPMNEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.current_file = None

    def init_ui(self):
        self.setWindowTitle("Editor BPMN")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon('#icon'))

        # Componentes principais
        self.canvas = BPMNCanvas()
        self.canvas.editor_ref = self  # Passar referência
        self.palette = BPMNPalette(self.canvas)
        self.properties = PropertiesWindow()

        # Layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.palette)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.properties)
        splitter.setSizes([200, 600, 200])

        # Barra de menus
        menu_bar = self.menuBar()
        
        # Menu Arquivo
        file_menu = menu_bar.addMenu("Arquivo")
        file_menu.addAction(self.create_action("Novo", "#new", self.new_diagram))
        file_menu.addAction(self.create_action("Abrir", "#open", self.open_diagram))
        file_menu.addAction(self.create_action("Salvar", "#save", self.save_diagram))
        file_menu.addSeparator()
        file_menu.addAction(self.create_action("Sair", "#exit", self.close))

        # Menu Editar
        edit_menu = menu_bar.addMenu("Editar")
        edit_menu.addAction(self.create_action("Deletar Elemento", "#delete", self.delete_element))
        edit_menu.addAction(self.create_action("Editar Propriedades", "#edit", self.edit_properties))

        # Menu Visualizar
        view_menu = menu_bar.addMenu("Visualizar")
        view_menu.addAction(self.create_action("Zoom +", "#zoom_in", self.zoom_in))
        view_menu.addAction(self.create_action("Zoom -", "#zoom_out", self.zoom_out))
        view_menu.addAction(self.create_action("Resetar Zoom", "#zoom_reset", self.zoom_reset))

        # Barra de ferramentas
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        actions = [
            ('Novo', '#new', self.new_diagram),
            ('Abrir', '#open', self.open_diagram),
            ('Salvar', '#save', self.save_diagram),
            ('Exportar', '#export', self.export_image),
            ('Deletar', '#delete', self.delete_element)
        ]
        
        for text, icon, callback in actions:
            action = self.create_action(text, icon, callback)
            toolbar.addAction(action)

        self.statusBar().showMessage('Pronto')
        self.canvas.scene.selectionChanged.connect(self.on_element_selected)
        self.setCentralWidget(splitter)

    def create_action(self, text, icon, callback):
        action = QAction(QIcon(icon), text, self)
        action.triggered.connect(callback)
        return action

    def new_diagram(self):
        self.canvas.scene.clear()
        self.current_file = None
        self.statusBar().showMessage('Novo diagrama criado')

    def delete_element(self):
        selected = self.canvas.scene.selectedItems()
        if selected:
            for item in selected:
                self.canvas.scene.removeItem(item)
            self.statusBar().showMessage(f'{len(selected)} elemento(s) removido(s)')

    def edit_properties(self):
        selected = self.canvas.scene.selectedItems()
        if selected:
            self.properties.update_properties(selected[0])
            self.properties.show()

    def zoom_in(self):
        self.canvas.scale(1.2, 1.2)

    def zoom_out(self):
        self.canvas.scale(0.8, 0.8)

    def zoom_reset(self):
        self.canvas.resetTransform()

    def on_element_selected(self):
        selected = self.canvas.scene.selectedItems()
        if selected:
            self.properties.update_properties(selected[0])

    # ... manter métodos existentes de save/open/export ...
    def save_diagram(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Salvar Diagrama", "", "BPMN Files (*.bpmn);;All Files (*)", options=options)
        
        if file_name:
            # Lógica temporária de salvamento
            with open(file_name, 'w') as f:
                f.write("BPMN Diagram - Versão 1.0\n")
                for item in self.canvas.scene.items():
                    if isinstance(item, BPMNElement):
                        f.write(f"{item.element_type}|{item.name}|{item.description}\n")
            self.statusBar().showMessage(f'Diagrama salvo em: {file_name}')
            self.current_file = file_name

    def open_diagram(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Abrir Diagrama", "", "BPMN Files (*.bpmn);;All Files (*)", options=options)
        
        if file_name:
            try:
                self.canvas.scene.clear()
                with open(file_name, 'r') as f:
                    lines = f.readlines()
                    for line in lines[1:]:  # Ignora header
                        parts = line.strip().split('|')
                        if len(parts) >= 3:
                            element = self.canvas.add_element(parts[0], QPoint(0, 0))
                            element.name = parts[1]
                            element.description = parts[2]
                self.statusBar().showMessage(f'Diagrama carregado: {file_name}')
                self.current_file = file_name
            except Exception as e:
                self.statusBar().showMessage(f'Erro ao abrir: {str(e)}')

    def open_diagram(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Abrir Diagrama", "", "BPMN Files (*.bpmn);;All Files (*)", options=options)
        
        if file_name:
            # Implementar lógica de carregamento
            self.statusBar().showMessage(f'Diagrama carregado: {file_name}')

    def export_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Exportar Imagem", "", "PNG Files (*.png);;JPEG Files (*.jpg)", options=options)
        
        if file_name:
            # Implementar exportação da imagem
            self.statusBar().showMessage(f'Imagem exportada: {file_name}')


# Adicione no final do arquivo:
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BPMNEditor()
    
    # Teste de fluxo
    canvas = window.canvas
    element1 = canvas.add_element('start', QPointF(50, 50))
    element2 = canvas.add_element('task', QPointF(200, 50))
    canvas.create_connection(element1, element2)
    
    window.show()
    sys.exit(app.exec_())
