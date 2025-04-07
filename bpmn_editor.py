import sys

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, 
                            QLabel, QDialog, QHBoxLayout, QLineEdit, QTextEdit, QSplitter,
                            QGraphicsView, QGraphicsScene, QGraphicsRectItem, QStatusBar,
                            QToolBar, QAction, QFileDialog, QMenu, QGraphicsLineItem, QStyle,
                            QGraphicsItem)
from PyQt5.QtGui import QIcon, QDrag, QPainter, QColor, QBrush, QFont, QPixmap, QPen
from PyQt5.QtCore import Qt, QMimeData, QPoint, QPointF, QSize

from functools import partial 

import traceback
import logging, json, uuid, pickle

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler('debug.log'), logging.StreamHandler()]
)

def excepthook(exc_type, exc_value, exc_traceback):
    traceback.print_exception(exc_type, exc_value, exc_traceback)
sys.excepthook = excepthook

class DragButton(QPushButton):
    def __init__(self, element_type, parent):
        super().__init__(parent)
        self.element_type = element_type
        self.setFixedSize(120, 40)
        
    def mousePressEvent(self, event):
        self.parent().mouse_press(event, self.element_type)
        
    def mouseMoveEvent(self, event):
        self.parent().mouse_move(event)
class BPMNElement(QGraphicsRectItem):
    def __init__(self, element_type, pos):
        super().__init__(0, 0, 100, 80)
        self.unique_id = uuid.uuid4().hex  # Gerar ID único
        self.setData(0, self.unique_id)   # Armazenar no item
        self.connections = []  # Lista de conexões
        self.element_type = element_type
        self.name = "Novo Elemento"
        self.description = ""
        self.setPos(pos)
        self.setBrush(QBrush(self.get_color()))
        self.setFlags(QGraphicsRectItem.ItemIsMovable | 
                    QGraphicsRectItem.ItemIsSelectable |
                    QGraphicsRectItem.ItemSendsGeometryChanges)

    def serialize(self):
        print(f"Serializando elemento {id(self)}: {self.serialize()}")
        return {
            'type': self.element_type,
            'x': self.x(),
            'y': self.y(),
            'name': self.name,
            'connections': [id(conn) for conn in self.connections]
        }
    
    def __getstate__(self):
        state = {
            'id': self.unique_id,
            'type': self.element_type,
            'pos': (self.x(), self.y()),
            'name': self.name,
            'connections': [c.unique_id for c in self.connections]
        }
        print(f"[SERIALIZAÇÃO] Elemento {self.unique_id}")
        return state

    def __setstate__(self, state):
        print(f"[DESSERIALIZAÇÃO] Elemento {state['id']}")
        self.unique_id = state['id']
        self.element_type = state['type']
        self.setPos(*state['pos'])
        self.name = state['name']
        self.connections = []  # Será preenchido posteriormente

    def get_persistent_id(self):
        return self.data(0)  # Recuperar ID armazenado
    
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
        self.viewport().setAcceptDrops(True)  # ← LINHA CRÍTICA ADICIONADA
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)
        self.elements = []
        self.setSceneRect(0, 0, 800, 600)  # Adicionar esta linha
        self.setMinimumSize(400, 300)      # Garantir tamanho mínimo
        self.editor_ref = None  # Inicializar atributo
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        print("Elementos na cena:", self.scene.items())  # Deve mostrar os elementos adicionados

    def add_element(self, element_type, pos):
        element = BPMNElement(element_type, pos)
        element.set_editor_reference(self.editor_ref)  # Nova linha
        self.scene.addItem(element)
        self.elements.append(element)
        return element

    def load_elements(self, data):
        # Primeira passada: cria elementos
        elements_map = {}
        for element_data in data['elements']:
            print(f"Elemento carregado na posição: {element.pos().x()}, {element.pos().y()}")
            element = self.add_element(
                element_data['type'], 
                QPointF(element_data['x'], element_data['y'])
            )
            element.name = element_data['name']
            elements_map[element_data['id']] = element
        
        # Segunda passada: reconecta
        for connection_data in data['connections']:
            start = elements_map[connection_data['start_id']]
            end = elements_map[connection_data['end_id']]
            self.create_connection(start, end)

    def dragEnterEvent(self, event):
        print(f"MIME Types recebidos: {event.mimeData().formats()}")  # Deve mostrar "application/x-bpmn-element"
        if event.mimeData().hasFormat("application/x-bpmn-element"):
            event.accept()  # ← Mudado para accept() em vez de acceptProposedAction()
            print("Drag ENTER aceito!")
            print("Drag accepted?", event.isAccepted())  # Deve ser True
        else:
            event.ignore()
        print("Formatos MIME disponíveis:", event.mimeData().formats())  # No dragEnterEvent

    def dropEvent(self, event):
        try:
            print("[DEBUG] Drop event iniciado")  # ← Verificar se o evento é chamado
            viewport_pos = event.pos()
            pos = self.mapToScene(viewport_pos)
            print(f"Posição calculada: X={pos.x():.1f}, Y={pos.y():.1f}")
        # ... restante do código
            pos = self.mapToScene(viewport_pos)
            print(f"DROP em: {pos.x():.1f}, {pos.y():.1f}")  # ← Debug garantido
            
            element_type = bytes(event.mimeData().data("application/x-bpmn-element")).decode()
            self.add_element(element_type, pos)
            event.acceptProposedAction()
            self.scene.update()  
            self.viewport().update()  # Atualizar visualização
            
        except Exception as e:
            print(f"ERRO NO DROP: {str(e)}")
            traceback.print_exc()


    def contextMenuEvent(self, event):
        # Obter itens selecionados
        selected_items = self.scene.selectedItems()  # ← Corrigir aqui
        
        # Criar menu
        menu = QMenu()
        
        if len(selected_items) == 2:
            # Verificar se são elementos BPMN (não conexões)
            if all(isinstance(item, BPMNElement) for item in selected_items):
                connect_action = menu.addAction("Conectar elementos")
                connect_action.triggered.connect(
                    lambda: self.create_connection(selected_items[0], selected_items[1])
                )
        
        menu.exec_(event.globalPos())
        
        # Limpar seleção após uso (opcional)
        for item in selected_items:
            item.setSelected(False)
        self.scene.update()

        
    def create_connection(self, source, target):
        connection = BPMNConnection(source, target)
        self.scene.addItem(connection)
        source.connections.append(connection)
        target.connections.append(connection)
        print(f"Conexão: {source.name} → {target.name} | Total: {len(self.scene.items())} itens")
        

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-bpmn-element"):
            event.accept()
            print('Movendo o Mouse...')
        else:
            event.ignore()
        
        print("Tipo de origem do drag:", event.source())  # Deve apontar para a BPMNPalette

class BPMNConnection(QGraphicsLineItem):
    def __init__(self, start_element, end_element):
        super().__init__()
        self.setPen(QPen(Qt.darkGray, 2, Qt.DashLine))
        self.start_element = start_element
        self.end_element = end_element
        self.update_position()

    def serialize(self):
        return {
            'start_id': id(self.start_element),
            'end_id': id(self.end_element)
        }

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
            btn = DragButton(element_type, self)  # ← Usar botão customizado
            btn.setText(text)
            btn.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
            btn.setFocusPolicy(Qt.NoFocus) 
            layout.addWidget(btn)
            
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

class PropertiesPanel(QWidget):
    def __init__(self, editor_ref=None):
        super().__init__()
        self.editor_ref = editor_ref
        self.selected_element = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Campo Nome
        self.name_label = QLabel("Nome do Elemento:")
        self.name_input = QLineEdit()
        self.name_input.textChanged.connect(self.update_name)
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)
        
        # Campo Descrição
        self.desc_label = QLabel("Descrição:")
        self.desc_input = QTextEdit()
        self.desc_input.textChanged.connect(self.update_description)
        layout.addWidget(self.desc_label)
        layout.addWidget(self.desc_input)
        
        # Botão Salvar
        self.save_btn = QPushButton("Salvar Alterações")
        self.save_btn.clicked.connect(self.close)
        layout.addWidget(self.save_btn)
        
        self.setLayout(layout)
        self.setWindowTitle("Propriedades")
        self.setMinimumSize(300, 200)

    def update_properties(self, element):
        self.selected_element = element
        self.name_input.setText(element.name)
        self.desc_input.setText(element.description)
        self.show()

    def update_name(self):
        if self.selected_element:
            self.selected_element.name = self.name_input.text()
            self.selected_element.update()  # Redesenha o elemento

    def update_description(self):
        if self.selected_element:
            self.selected_element.description = self.desc_input.toPlainText()

class BPMNEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.canvas = BPMNCanvas()
        self.properties = PropertiesPanel(self)
        
        # Primeiro criar todas as ações
        self.create_actions()  # ← Método modificado
        
        # Depois configurar a UI que depende das ações
        self.init_ui()
        self.setWindowTitle("Editor BPMN")
        self.setGeometry(100, 100, 1200, 800)

    def create_actions(self):
        """Configura todas as ações centralizadas"""
        # Ações de Arquivo
        self.new_action = QAction("Novo", self)
        self.open_action = QAction("Abrir...", self)
        self.save_action = QAction("Salvar", self)
        
        # Ações de Zoom
        self.zoom_in_action = QAction("Zoom +", self)
        self.zoom_in_action.setShortcut("Ctrl++")
        self.zoom_in_action.triggered.connect(self.zoom_in)
        
        self.zoom_out_action = QAction("Zoom -", self)
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.zoom_out_action.triggered.connect(self.zoom_out)


    def init_ui(self):
        """Configura elementos visuais que usam ações"""
        # Toolbar Principal
        toolbar = self.addToolBar("Principal")
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.zoom_in_action)
        toolbar.addAction(self.zoom_out_action)
        
        # Menu Ver
        view_menu = self.menuBar().addMenu("&Ver")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        
        # ... (restante do layout)        self.setWindowTitle("Editor BPMN")
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
        # file_menu = menu_bar.addMenu("Arquivo")
        # file_menu.addAction(self.new_action)  # ← Usar ação já criada
        # file_menu.addAction(self.open_action)
        # file_menu.addAction(self.save_action)
        # file_menu.addSeparator()
#        file_menu.addAction(self.create_actions("Sair", "#exit", self.close))

        # Menu Editar
        edit_menu = menu_bar.addMenu("Editar")
        edit_menu.addAction(self.delete_action)
        edit_menu.addAction(self.open_action)

        # Menu Visualizar
        # view_menu = menu_bar.addMenu("Visualizar")
        # view_menu.addAction(self.zoom_in_action)
        # view_menu.addAction(self.zoom_out_action)
        # view_menu.addAction(self.create_actions("Resetar Zoom", "#zoom_reset", self.zoom_reset))

        # Barra de ferramentas
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # actions = [
        #     ('Novo', '#new', self.new_diagram),
        #     ('Abrir', '#open', self.load_project),
        #     ('Salvar', '#save', self.save_project),
        #     ('Exportar', '#export', self.export_image),
        #     ('Deletar', '#delete', self.delete_element)
        # ]
        
        # for text, icon, callback in actions:
        #     action = self.create_actions(text, icon, callback)
        #     toolbar.addAction(action)

        self.statusBar().showMessage('Pronto')
        self.canvas.scene.selectionChanged.connect(self.on_element_selected)
        self.setCentralWidget(splitter)

    def create_actions(self):
        # Ação Novo Diagrama
        self.new_action = QAction(
            QIcon('new_icon.png'),  # Opcional
            "&Novo Diagrama", 
            self
        )
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(self.new_diagram)
        
        # Ação Salvar
        self.save_action = QAction(
            QIcon('save_icon.png'), 
            "&Salvar Projeto", 
            self
        )
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.save_project)
        
        # Ação Abrir
        self.open_action = QAction(
            QIcon('folder_icon.png'), 
            "&Abrir Projeto", 
            self
        )
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.load_project)
        
        self.delete_action = QAction(
        QIcon('delete_icon.png'),  # Opcional
        "&Deletar Elemento", 
        self
    )
        self.delete_action.setShortcut("Del")  # Tecla Delete
        self.delete_action.triggered.connect(self.delete_element)

        # Ação Zoom +
        self.zoom_in_action = QAction(
            QIcon(),  # Adicione um ícone se desejar
            "Zoom +", 
            self
        )
        self.zoom_in_action.setShortcut("Ctrl++")
        self.zoom_in_action.triggered.connect(self.zoom_in)

        # Ação Zoom -
        self.zoom_out_action = QAction(
            QIcon(),
            "Zoom -", 
            self
        )
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.zoom_out_action.triggered.connect(self.zoom_out)
        
    def create_toolbar(self):
        toolbar = self.addToolBar("Arquivo")
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)  # ← Agora visível na UI

    def new_diagram(self):
        self.canvas.scene.clear()
        self.canvas.elements.clear()
        self.statusBar().showMessage("Diagrama reiniciado", 2000)

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
                with open(file_name, 'r') as f:
                    data = json.load(f)
                    self.canvas.load_elements(data)
            except Exception as e:
                self.statusBar().showMessage(f'Erro ao abrir: {str(e)}')

        # if file_name:  # abre um arquivo txt comum
        #     try:
        #         self.canvas.scene.clear()
        #         with open(file_name, 'r') as f:
        #             lines = f.readlines()
        #             for line in lines[1:]:  # Ignora header
        #                 parts = line.strip().split('|')
        #                 if len(parts) >= 3:
        #                     element = self.canvas.add_element(parts[0], QPoint(0, 0))
        #                     element.name = parts[1]
        #                     element.description = parts[2]
        #         self.statusBar().showMessage(f'Diagrama carregado: {file_name}')
        #         self.current_file = file_name
        #     except Exception as e:
        #         self.statusBar().showMessage(f'Erro ao abrir: {str(e)}')

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

    def save_project(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Salvar Diagrama BPMN", 
            "", 
            "BPMN Files (*.bpmn)"
        )
        
        if filename:
            # Coletar dados dos elementos
            elements_data = {
                'version': 1.0,
                'elements': [elem.__getstate__() for elem in self.canvas.elements],
                'connections': [
                    {
                        'start_id': conn.start_element.unique_id,
                        'end_id': conn.end_element.unique_id
                    } 
                    for conn in self.canvas.scene.items() 
                    if isinstance(conn, BPMNConnection)
                ]
            }
            
            # Serializar com Pickle
            with open(filename, 'wb') as f:
                pickle.dump(elements_data, f)
            
            self.statusBar().showMessage(f"Projeto salvo em: {filename}", 3000)

    def load_project(self):  # ← IMPLEMENTAR
        filename, _ = QFileDialog.getOpenFileName(self, "Abrir Projeto", "", "BPMN Files (*.bpmn)")
        if filename:
            with open(filename, 'rb') as f:
                data = pickle.load(f)  # ← Dispara __setstate__
            self.canvas.load_elements(data)

    def delete_element(self):
        selected = self.canvas.scene.selectedItems()
        for item in selected:
            if isinstance(item, BPMNElement):
                # Remover conexões associadas
                for conn in item.connections:
                    self.canvas.scene.removeItem(conn)
                self.canvas.scene.removeItem(item)
        self.canvas.scene.update()


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
