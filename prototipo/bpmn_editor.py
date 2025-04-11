import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, 
                            QLabel, QDialog, QHBoxLayout, QLineEdit, QTextEdit, QSplitter,
                            QGraphicsView, QGraphicsScene, QGraphicsRectItem, QStatusBar,
                            QToolBar, QAction, QFileDialog, QMenu, QGraphicsLineItem, QStyle,
                            QGraphicsItem, QMessageBox, QShortcut)
from PyQt5.QtGui import (QIcon, QDrag, QPainter, QColor, QBrush, QCursor, 
                         QFont, QPixmap, QPen, QPolygonF, QPainterPath, QKeySequence)
from PyQt5.QtCore import (Qt, QMimeData, QPoint, QPointF, QSize, 
                          QRectF, QLineF, QTimer)

from functools import partial 
from weakref import ref
from datetime import datetime

import traceback
import logging, json, uuid, pickle
import locale

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')  # Forçar locale compatível
sys.stdout.reconfigure(encoding='utf-8')  # Configurar saída padrão

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def excepthook(exc_type, exc_value, exc_traceback):
    traceback.print_exception(exc_type, exc_value, exc_traceback)
sys.excepthook = excepthook

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
      
class BPMNElement(QGraphicsRectItem):
    def __init__(self, element_type, pos):
        super().__init__()
        self.unique_id = uuid.uuid4().hex  # Gerar ID único
        self.setData(0, self.unique_id)   # Armazenar no item
        self.connections = []  # Lista de conexões
        self.element_type = element_type
        self.name = "Novo Elemento"
        self.description = ""
        self.setPos(pos)
        self.setBrush(QBrush(self.get_color()))
        self.setFlags(QGraphicsItem.ItemIsMovable | 
                    QGraphicsItem.ItemIsSelectable |
                    QGraphicsItem.ItemSendsGeometryChanges |
                    QGraphicsItem.ItemSendsScenePositionChanges)
        # self.setFlag(QGraphicsItem.ItemIsMovable, True)
        # self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        

    def serialize(self):
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
            'connections': [c.unique_id for c in self.connections 
                        if isinstance(c, BPMNConnection)]
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
    
    def boundingRect(self):
        # if self.element_type == 'gateway':
        #     return QRectF(-10, -10, 100, 70)  # Aumentar área para o losango
        return QRectF(-10, -10, 120, 100)  # Margem extra
    
    def shape(self):
        path = QPainterPath()
        if self.element_type == 'start':
            path.addEllipse(25, 10, 50, 50)
        elif self.element_type == 'gateway':
            diamond = QPolygonF([QPointF(50,0), QPointF(100,35), QPointF(50,70), QPointF(0,35)])
            path.addPolygon(diamond)
        else:
            path.addRoundedRect(0, 0, 100, 60, 10, 10)
        return path
    
    def paint(self, painter, option, widget):
        # Destacar seleção
        if self.isSelected():
            painter.setPen(QPen(Qt.yellow, 3))
        else:
            painter.setPen(QPen(Qt.black, 1))

        painter.setPen(QPen(Qt.black if self.isSelected() else Qt.gray, 2))
        # Desenha ícone de conexão quando selecionado
        if self.isSelected():
            painter.drawEllipse(self.boundingRect().topRight(), 5, 5)

        painter.setBrush(self.get_color())
        
        # Formas específicas por tipo
        if self.element_type == 'start':
            # Círculo para evento de início
            painter.drawEllipse(25, 10, 50, 50)
            painter.drawText(QRectF(0, 60, 100, 20), Qt.AlignCenter, self.name)
            
        elif self.element_type == 'gateway':
            # Losango para gateway
            diamond = QPolygonF([
                QPointF(50, 0), 
                QPointF(100, 35),
                QPointF(50, 70),
                QPointF(0, 35)
            ])
            painter.drawPolygon(diamond)
            painter.drawText(QRectF(0, 70, 100, 20), Qt.AlignCenter, self.name)
            
        else:  # Tarefas
            # Retângulo com cantos arredondados
            painter.drawRoundedRect(0, 0, 100, 60, 10, 10)
            painter.drawText(QRectF(0, 60, 100, 20), Qt.AlignCenter, self.name)

    # Adicionar na classe BPMNElement:
    def set_editor_reference(self, editor_ref):
        self.editor_ref = editor_ref

    # Modificar o método:
    def mouseDoubleClickEvent(self, event):
        if hasattr(self, 'editor_ref'):
            self.editor_ref.properties.update_properties(self)
            self.editor_ref.properties.show()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # Atualizar conexões ao mover
            for conn in self.connections:
                conn.update_position()
        # print("Itens selecionados:", [item.unique_id for item in self.selected_elements])
        return super().itemChange(change, value)
    
    def mouseMoveEvent(self, event):
        # Forçar atualização em tempo real
        super().mouseMoveEvent(event)
        if self.isSelected():
            for conn in self.connections:
                conn.update_position()
            self.scene().update()

    def add_connection(self, connection):
        if connection not in self.connections:
            self.connections.append(connection)

    def remove_connection(self, connection):
        if connection in self.connections:
            self.connections.remove(connection)

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

class BPMNCanvas(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.viewport().setAcceptDrops(True)  # ← LINHA CRÍTICA ADICIONADA
        # self.scene = QGraphicsScene(self)
        self.scene = GridScene(self)  # ← Alterado para nossa cena personalizada
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)
        self.elements = []
        self.setSceneRect(0, 0, 800, 600)  # Adicionar esta linha
        self.setMinimumSize(400, 300)      # Garantir tamanho mínimo
        self.editor_ref = None  # Inicializar atributo
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.drag_start_position = QPoint()
        self.connection_source = None
        self.temp_connection = None        
        self.selected_elements = []  # Nova lista de seleção
        self.setRubberBandSelectionMode(Qt.ContainsItemBoundingRect)  # ← Nova linha

        self.setDragMode(QGraphicsView.ScrollHandDrag)  # Modo de arrastar com botão esquerdo
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.viewport().update()

        # Habilitar eventos de arrasto para scroll
        self.setInteractive(True)
        self.setRubberBandSelectionMode(Qt.ContainsItemShape)

        self.delete_shortcut = QShortcut(QKeySequence.Delete, self)
        self.delete_shortcut.activated.connect(
            lambda: (self.delete_selected_connections() 
                    or self.delete_selected_elements())
        )

        self.delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        self.delete_shortcut.activated.connect(self.delete_selected_elements)

        self.scene.selectionChanged.connect(self.on_selection_change)
        self.editor_ref = ref(self.editor_ref) if self.editor_ref else None

        # Nova configuração de performance
        self.setCacheMode(QGraphicsView.CacheBackground)
        self.scene.setItemIndexMethod(QGraphicsScene.NoIndex)

        print("Elementos na cena:", self.scene.items())  # Deve mostrar os elementos adicionados

    def add_element(self, element_type, pos):
        # Garantir que o tipo seja 'gateway' (não 'getway' ou variações)
        valid_types = ['start', 'task', 'gateway']  # ← Nomes padronizados
        if element_type not in valid_types:
            raise ValueError(f"Tipo inválido: {element_type}")
        
        element = BPMNElement(element_type, pos)
        element.set_editor_reference(self.editor_ref)  # Nova linha
        element.setPos(pos)  # ← Garantir posicionamento correto
        self.scene.addItem(element)
        self.elements.append(element)
        return element

    def load_elements(self, data):
        # Fase 1: Criar elementos
        elements_map = {}
        for elem_data in data['elements']:
            element = self.add_element(
                elem_data['type'], 
                QPointF(elem_data['x'], elem_data['y'])
            )
            element.name = elem_data['name']
            elements_map[elem_data['id']] = element
        
        # Fase 2: Criar conexões
        for conn_data in data['connections']:
            try:
                start = elements_map[conn_data['start_id']]
                end = elements_map[conn_data['end_id']]
                self.create_connection(start, end)  # ← Usar método correto
            except KeyError as e:
                print(f"Erro na conexão: elemento {e} não encontrado")

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-bpmn-element"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        # Correção crucial:
        mime_data = event.mimeData()
        element_type = bytes(mime_data.data("application/x-bpmn-element")).decode('utf-8')
        
        pos = self.mapToScene(event.pos())
        self.add_element(element_type, pos)
        event.acceptProposedAction()
        # self.viewport().update()

    def contextMenuEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        items = self.scene.items(scene_pos)
        menu = QMenu()

        # Ação para remover seleção múltipla
        delete_selected_action = QAction("🗑️ Remover Seleção", self)
        delete_selected_action.triggered.connect(self.delete_selected_elements)
        if self.scene.selectedItems():  # Verifica se há itens selecionados
            menu.addAction(delete_selected_action)

        # Verificar conexões primeiro
        connections = [item for item in items if isinstance(item, BPMNConnection)]
        if connections:
            delete_conn_action = QAction("🗑️ Remover Conexão", self)
            delete_conn_action.triggered.connect(self.delete_selected_connections)
            menu.addAction(delete_conn_action)
        
        # Verificar elementos BPMN
        elements = [item for item in items if isinstance(item, BPMNElement)]
        if elements:
            element = elements[0]  # Pega o elemento superior
            connect_action = QAction("🔗 Conectar a...", self)
            connect_action.triggered.connect(
                lambda: self.initiate_connection_mode(element)
            )
            menu.addAction(connect_action)
        
        if menu.actions():
            menu.exec_(event.globalPos())

    def initiate_connection_mode(self, source_element):
        # self.connection_source = source_element
        self.setDragMode(QGraphicsView.NoDrag)
        self.viewport().setCursor(Qt.CrossCursor)
        
        # Conexão temporária visual
        self.temp_connection = QGraphicsLineItem(QLineF(
            source_element.sceneBoundingRect().center(),
            self.mapToScene(self.viewport().mapFromGlobal(QCursor.pos()))
        ))
        self.temp_connection.setPen(QPen(Qt.gray, 2, Qt.DashLine))
        self.scene.addItem(self.temp_connection)
        
        # Monitorar movimento do mouse
        self.mouseMoveEvent = self.connection_mouse_move
        self.mousePressEvent = self.connection_mouse_press

    def connection_mouse_move(self, event):
        end_pos = self.mapToScene(event.pos())
        line = QLineF(
            self.connection_source.sceneBoundingRect().center(),
            end_pos
        )
        self.temp_connection.setLine(line)

    def connection_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, BPMNElement) and item != self.connection_source:
                self.create_connection(self.connection_source, item)
        self.cleanup_connection_mode()

    def cleanup_connection_mode(self):
        self.scene.removeItem(self.temp_connection)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.viewport().unsetCursor()
        self.mouseMoveEvent = super().mouseMoveEvent
        self.mousePressEvent = super().mousePressEvent

    def create_connection(self, source, target):
        # Validação crítica
        if (isinstance(source, BPMNElement) and 
            isinstance(target, BPMNElement) and 
            source != target):
            
            connection = BPMNConnection(source, target)
            self.scene.addItem(connection)
            logging.info(f"Conexão criada: {source.unique_id} -> {target.unique_id}")
        

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-bpmn-element"):
            event.accept()
            print('Movendo o Mouse...')
        else:
            event.ignore()
        
        print("Tipo de origem do drag:", event.source())  # Deve apontar para a BPMNPalette

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-bpmn-element"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        element_type = event.mimeData().data("application/x-bpmn-element").data().decode()
        pos = self.mapToScene(event.pos())
        self.add_element(element_type, pos)
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        # Limpar seleção apenas ao clicar em área vazia
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if not item:  # Só limpa se clicar fora dos elementos
                self.scene.clearSelection()
        if event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            fake_event = event
            fake_event.setButton(Qt.LeftButton)  # Simular clique esquerdo
            super().mousePressEvent(fake_event)
        else:        
            super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        if self.temp_connection:
            end_pos = self.mapToScene(event.pos())
            self.temp_connection.end_pos = end_pos
            self.temp_connection.update_position()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.RubberBandDrag)  # Novo código
            
            # Mantenha a lógica existente de conexão
            selected_items = [item for item in self.scene.selectedItems() 
                            if isinstance(item, BPMNElement)]

            if len(self.scene.selectedItems()) == 0:
                return  # Ignorar clique direito em área vazia
            
            if len(selected_items) == 2:
                source, target = selected_items
                self.create_connection(source, target)
            else:
                QMessageBox.warning(self, "Erro", 
                    "Selecione exatamente 2 elementos para conectar.")
        
        super().mouseReleaseEvent(event)

    def delete_selected_elements(self):
        try:
            # Obter todos os itens selecionados
            selected_items = self.scene.selectedItems()

            for item in selected_items:
                if isinstance(item, BPMNElement) and item in self.elements:
                    self.elements.remove(item)  # Atualiza lista interna
            try:
                self.scene.blockSignals(True)

                for item in selected_items:
                    if isinstance(item, (BPMNElement, BPMNConnection)):
                        # Remove conexões bidirecionais
                        if hasattr(item, 'connections'):
                            for conn in item.connections[:]:  # Cópia para iteração segura
                                conn.source.connections.remove(conn)
                                conn.target.connections.remove(conn)
                                self.scene.removeItem(conn)
                        self.scene.removeItem(item)

            finally:
                self.scene.blockSignals(False)
                self.scene.update()  # Força atualização única
                
                # Dispara manualmente se necessário
                self.scene.selectionChanged.emit() 

                if self.editor_ref:  # ← Fechar propriedades
                    self.editor_ref.properties.hide()
                    
                logging.info(f"{len(selected_items)} elementos removidos")


        except Exception as e:
            logging.error(f"Erro ao remover elementos: {str(e)}")

    def delete_selected_connections(self):
        try:
            selected = [item for item in self.scene.selectedItems() 
                      if isinstance(item, BPMNConnection)]
            
            for connection in selected:
                # Remover das listas de conexões dos elementos
                connection.source.remove_connection(connection)
                connection.target.remove_connection(connection)
                # Remover da cena
                self.scene.removeItem(connection)
                
            if self.editor_ref:
                self.editor_ref.properties.hide()
                
            logging.info(f"{len(selected)} conexões removidas")
            
        except Exception as e:
            logging.error(f"Erro ao remover conexões: {str(e)}")

    def on_selection_change(self):
        if self.scene.selectedItems():
            return  # Aborta se houver seleção
        """Atualiza UI quando seleção muda"""
        if not self.scene.selectedItems() and self.editor_ref:
            self.editor_ref.properties.hide()

    def wheelEvent(self, event):
        # Comportamento padrão para scroll vertical
        if not event.modifiers():
            super().wheelEvent(event)
            return
        
        # Zoom apenas com Ctrl pressionado
        if event.modifiers() & Qt.ControlModifier:
            zoom_factor = 1.25
            if event.angleDelta().y() > 0:
                self.scale(zoom_factor, zoom_factor)
            else:
                self.scale(1/zoom_factor, 1/zoom_factor)
            self.scene.update()

    def resizeEvent(self, event):
        self.setSceneRect(QRectF(self.viewport().rect()))  # Atualizar área visível
        super().resizeEvent(event)

class BPMNConnection(QGraphicsLineItem):
    def __init__(self, source, target):
        super().__init__()
        self.unique_id = uuid.uuid4().hex  # ← ID único para conexão
        self.source = source  # ← Inicialização obrigatória
        self.target = target  # ← Antes de qualquer uso

        # Garantir referências bidirecionais
        source.connections.append(self)
        target.connections.append(self)
        self.source.add_connection(self)
        self.target.add_connection(self)

        # Configurações de serialização
        self.setData(0, self.unique_id)  # Armazenar ID no item
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        
        # Configurações visuais
        self.setPen(QPen(Qt.darkGray, 2, Qt.SolidLine, Qt.RoundCap))  # Atualizado
        self.setZValue(-1)  # Ficar atrás dos elementos
        self.update_position()
        
        # DEBUG:
        print(f"[DEBUG] Conexão {self.unique_id} criada com:")  # ASCII seguro
        print(f"  Source: {self.source.unique_id if self.source else 'None'}")
        print(f"  Target: {self.target.unique_id if self.target else 'None'}")

    def __getstate__(self):
        return {
            'id': self.unique_id,
            'source_id': self.source.unique_id,  # Nome correto
            'target_id': self.target.unique_id   # ← Aqui estava o erro
        }

    def __setstate__(self, state):
        required_keys = {'id', 'source_id', 'target_id'}
        if not required_keys.issubset(state.keys()):
            raise ValueError(f"Estado inválido da conexão, faltam chaves: {required_keys - state.keys()}")
        
        self.unique_id = state['id']
        self._source_id = state['source_id']  # Armazena temporariamente
        self._target_id = state['target_id']

    def update_position(self):
        # Garantir pontos atualizados
        start_point = self.source.scenePos() + QPointF(50, 30)  # Centro do elemento origem
        end_point = self.target.scenePos() + QPointF(50, 30)    # Centro do elemento destino
        self.setLine(QLineF(start_point, end_point))

    def serialize(self):
        return {
            'connection_id': self.unique_id,
            'start_element_id': self.start_id,
            'end_element_id': self.end_id
        }

    def paint(self, painter, option, widget):
        if self.isSelected():
            painter.setPen(QPen(Qt.red, 2, Qt.DashLine))
        else:
            painter.setPen(QPen(Qt.darkGray, 2, Qt.SolidLine))
        painter.drawLine(self.line())

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
        self.palette = BPMNPalette(self.canvas)
        self.palette.editor_ref = self 
        self.canvas.editor_ref = self 
        self.properties = PropertiesPanel()
        self.current_file = None  # Adicionar atributo

        # Configurações de auto salvamento
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.autoSave)
        self.autosave_timer.start(300000)  # 5 minutos

        # 1. Criar todas as ações primeiro
        self.create_actions()
        
        # 2. Configurar interface
        self.init_ui()
        
        self.setWindowTitle("Editor BPMN")
        self.setGeometry(100, 100, 1200, 800)
        self.show()
        # Menu Arquivo
        file_menu = self.menuBar().addMenu("Arquivo")
        
        # Ação Salvar (definir apenas aqui)
        save_action = QAction(QIcon(), "Salvar", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        # Toolbar
        self.toolbar = self.addToolBar("Ferramentas")
        
        # Ação de Remoção (novo)
        delete_action = QAction(QIcon(), "Remover Elemento", self)
        delete_action.setShortcut(Qt.Key_Delete)  # Atalho: Tecla Delete
        delete_action.triggered.connect(self.delete_selected)
        self.toolbar.addAction(delete_action)

    def create_actions(self):
        self.new_action = QAction("&Novo", self)
        self.new_action.triggered.connect(self.new_file)  # Conectar ao método existente
        
        self.open_action = QAction("&Abrir...", self)
        self.open_action.triggered.connect(self.open_file)
        
        self.save_action = QAction("&Salvar", self)
        self.save_action.triggered.connect(self.save)
       
        # Ações de Zoom
        self.zoom_in_action = QAction("Zoom +", self)
        self.zoom_in_action.setShortcut("Ctrl++")
        self.zoom_in_action.triggered.connect(self.zoom_in)
        
        self.zoom_out_action = QAction("Zoom -", self)
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.zoom_out_action.triggered.connect(self.zoom_out)

    def init_ui(self):
        # Painel Lateral (Paleta de Elementos)
        palette = QWidget()
        palette.setFixedWidth(150)
        palette_layout = QVBoxLayout(palette)
        
        # Botões de Elementos BPMN
        element_types = ['start', 'task', 'gateway']
        for elem in element_types:
            btn = DragButton(elem, self)
            btn.setText(elem.capitalize())
            palette_layout.addWidget(btn)
        
        # Layout Principal

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.palette)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.properties)
        splitter.setSizes([200, 600, 200])  # Definir proporções iniciais
        self.setCentralWidget(splitter)

        # Toolbar Principal
        toolbar = self.addToolBar("Principal")
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.zoom_in_action)
        toolbar.addAction(self.zoom_out_action)
        
        self.create_actions()
        self.init_menus()
        
        print("Inicializando UI...")
        print("Número de widgets no splitter:", splitter.count())  # Deve ser 3
        print("Menu bar visível?", self.menuBar().isVisible())  # Deve ser True

        # Status Bar
        self.statusBar().showMessage("Pronto")

    def init_menus(self):
        # Menu Arquivo
        file_menu = self.menuBar().addMenu("&Arquivo")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        
        # Menu Ver
        view_menu = self.menuBar().addMenu("&Ver")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)

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
        # self.save_action.setShortcut("Ctrl+S")
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

    def autoSave(self):
        if self.current_file:
            try:
                self.save_model()
                self.statusBar().showMessage(f"Autosalvo em {datetime.now().strftime('%H:%M')}", 2000)
            except Exception as e:
                logging.error(f"Autosalvo falhou: {str(e)}")

    def setWindowModifiedFlag(self, modified):
        title = "Editor BPMN" + ("*" if modified else "")
        self.setWindowTitle(title)

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

    def new_file(self):
        self.canvas.scene.clear()
        self.statusBar().showMessage("Novo arquivo criado")

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Abrir Diagrama", "", "BPMN Files (*.bpmn)"
        )
        if filename:
            try:
                with open(filename, 'rb') as f:
                    data = pickle.load(f)
                    self.canvas.load_elements(data)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao abrir arquivo:\n{str(e)}")

    def save(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Salvar Diagrama", "", "BPMN Files (*.bpmn)"
        )
        if filename:
            data = {'elements': [e.__getstate__() for e in self.canvas.elements]}
            with open(filename, 'wb') as f:
                pickle.dump(data, f)

    def export_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Exportar Imagem", "", "PNG Files (*.png);;JPEG Files (*.jpg)", options=options)
        
        if file_name:
            # Implementar exportação da imagem
            self.statusBar().showMessage(f'Imagem exportada: {file_name}')

    def save_project(self):
        print("[DEBUG] Salvando projeto...")  # Verifique se esta linha aparece
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Salvar Projeto", "", "BPMN Files (*.bpmn)")
            if path:
                # Coletar dados de elementos e conexões
                elements_data = [elem.__getstate__() for elem in self.canvas.elements]
                connections = [item for item in self.canvas.scene.items() if isinstance(item, BPMNConnection)]
                connections_data = [conn.__getstate__() for conn in connections]
                
                data = {
                    'elements': elements_data,
                    'connections': connections_data
                }
                
                with open(path, 'wb') as f:
                    pickle.dump(data, f)

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar: {str(e)}")
            logging.error(f"Erro ao salvar: {str(e)}")

    def load_project(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir Projeto", "", "BPMN Files (*.bpmn)")
            if path:
                with open(path, 'rb') as f:
                    data = pickle.load(f)

                # Limpar cena atual
                self.canvas.scene.clear()
                self.canvas.elements = []
                
                # Passo 1: Recriar elementos
                elements_map = {}
                for elem_data in data['elements']:
                    element = self.canvas.add_element(
                        elem_data['type'], 
                        QPointF(elem_data['pos'][0], elem_data['pos'][1])
                    )
                    element.unique_id = elem_data['id']  # Garantir ID original
                    element.name = elem_data['name']
                    elements_map[elem_data['id']] = element
                
                # Passo 2: Reconectar
                for conn_data in data['connections']:
                    start = elements_map.get(conn_data['source_id'])
                    end = elements_map.get(conn_data['target_id'])
                    if start and end:
                        self.canvas.create_connection(start, end)
                    else:
                        logging.error(f"Conexão inválida: {conn_data}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao carregar: {str(e)}")
            logging.error("Erro durante o carregamento:", exc_info=True)

    def delete_element(self):
        selected = self.canvas.scene.selectedItems()
        for item in selected:
            if isinstance(item, BPMNElement):
                # Remover conexões associadas
                for conn in item.connections:
                    self.canvas.scene.removeItem(conn)
                self.canvas.scene.removeItem(item)
        self.canvas.scene.update()

    def save_model(self):
        # Limpar cena antes de coletar dados
        self.canvas.scene.clearSelection()
        
        # Coletar dados de forma segura
        data = {
            'elements': [pickle.dumps(item) for item in self.canvas.scene.items() 
                        if isinstance(item, BPMNElement)],
            'connections': [pickle.dumps(item) for item in self.canvas.scene.items()
                        if isinstance(item, BPMNConnection)]
        }
        
        with open(self.current_file, 'wb') as f:
            pickle.dump(data, f)

    def load_model(self):
        # Resetar estado completamente
        self.canvas.scene.clear()
        self.current_file = None
        
        with open(self.current_file, 'rb') as f:
            data = pickle.load(f)
        
        id_map = {}
        # Desserialização em 2 passos
        for item_type in ['elements', 'connections']:
            for item_data in data[item_type]:
                item = pickle.loads(item_data)
                if isinstance(item, BPMNElement):
                    id_map[item.unique_id] = item
                    self.canvas.scene.addItem(item)
                elif isinstance(item, BPMNConnection):
                    # Conexões serão reconstruídas posteriormente
                    pass

        # Primeira passada: apenas elementos
        for item_data in data['elements']:
            item = pickle.loads(item_data)
            id_map[item.unique_id] = item
            self.canvas.scene.addItem(item)
        
        # Reconectar elementos
        logging.info(f"Elementos carregados: {len(id_map)}")
        logging.info(f"Conexões a processar: {len(data['connections'])}")
        
        for idx, item_data in enumerate(data['connections']):
            conn = pickle.loads(item_data)
            logging.debug(f"Processando conexão {idx+1}/{len(data['connections'])}: {conn}")
            conn = pickle.loads(item_data)

            source_id = conn['source_id']  # Nome correto
            target_id = conn['target_id']
            
            source = id_map.get(source_id)
            target = id_map.get(target_id)
            
            if source and target:
                new_conn = BPMNConnection(source, target)
                new_conn.unique_id = conn['id']
                self.canvas.scene.addItem(new_conn)
                # Mantenha as referências nos elementos
                source.add_connection(new_conn)
                target.add_connection(new_conn)
            else:
                logging.error(f"Conexão {conn['id']} inválida: "
                            f"Source ({source_id}) ou Target ({target_id}) não encontrados")
                
    def salvarArquivo(self):
        if not self.current_file:
            self.current_file, _ = QFileDialog.getSaveFileName(
                self, "Salvar Arquivo", "", "BPMN Files (*.bpmn)")
        
        if self.current_file:
            try:
                self.save_model()  # ← Substituir código direto pelo método
                self.statusBar().showMessage(f"Modelo salvo em: {self.current_file}", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao salvar:\n{str(e)}")

    def abrirArquivo(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Abrir Arquivo", "", "BPMN Files (*.bpmn)")
        
        if filename:
            try:
                self.current_file = filename
                self.load_model()  # ← Usar método unificado
                self.statusBar().showMessage(f"Modelo carregado: {filename}", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao carregar:\n{str(e)}")

    def delete_selected(self):
        if hasattr(self, 'canvas'):
            self.canvas.delete_selected_elements()


# Adicione no final do arquivo:
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Estilo visual moderno
    window = BPMNEditor()
    window.resize(1200, 800)  # Tamanho inicial adequado
    window.show()
    sys.exit(app.exec_())

