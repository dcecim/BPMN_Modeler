import sys
from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QAction, QMenu, QGraphicsLineItem, 
                             QMessageBox, QShortcut)
from PyQt5.QtGui import (QPainter, QCursor, QPen,QKeySequence)
from PyQt5.QtCore import (Qt, QPoint, QPointF, QRectF, QLineF)

from ..models.grid import GridScene  # Dois pontos sobem um nível
from ..models.elements import BPMNElement, BPMNConnection

from weakref import ref
import logging
logger = logging.getLogger(__name__)

print(sys.path)  # Deve incluir o caminho do projeto

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

