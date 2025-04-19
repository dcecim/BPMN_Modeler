import sys
from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QAction, QMenu, QGraphicsLineItem, 
                             QMessageBox, QShortcut, QSplitter)
from PyQt5.QtGui import (QPainter, QCursor, QPen,QKeySequence, QMouseEvent, QTransform)
from PyQt5.QtCore import (Qt, QEvent, QPoint, QPointF, QRectF, QLineF, QObject, pyqtSignal)

from ..models.grid import GridScene  # Dois pontos sobem um nível
from ..models.elements import BPMNElement, BPMNConnection
from ..dialogs.property_dialog import PropertyDialog

from weakref import ref
import logging
logger = logging.getLogger(__name__)

print(sys.path)  # Deve incluir o caminho do projeto

from PyQt5.QtCore import QObject, pyqtSignal

class CanvasSignals(QObject):
    """Sinais customizados do canvas"""
    selectionChanged = pyqtSignal(list)  # Sinal para mudança de seleção
    # Se necessário, adicionarei outros sinais (ex: elementAdded, connectionCreated)

class BPMNCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Criar uma nova instância de GridScene
        self.scene = GridScene()
        self.setScene(self.scene)
        
        # Configurações
        self.setRenderHint(QPainter.Antialiasing)
        
        # Adicionar o atributo mode
        self.mode = "select"  # Valores possíveis: "select", "connection", "create"
        
        # Conectar o sinal de seleção alterada
        self.scene.selectionChanged.connect(self.on_selection_change)

        # Outras inicializações
        self.temp_connection = None
        self.connections = []
        
        self.signals = CanvasSignals() 
        self.viewport().setAcceptDrops(True)  # ← LINHA CRÍTICA ADICIONADA
 
        self.setAcceptDrops(True)
        self.elements = []
        self.setSceneRect(0, 0, 800, 600)   
        self.setMinimumSize(400, 300)      
        self.editor_ref = None  # Inicializar atributo

        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
    
        self.drag_start_position = QPoint()

        self.connection_source = None
        self.temp_connection = None  
        self.connection_line = None  
        self.selected_elements = []  # Nova lista de seleção

        self.setRubberBandSelectionMode(Qt.ContainsItemBoundingRect) 
        # self.setRubberBandSelectionMode(Qt.ContainsItemShape)

        self.setDragMode(QGraphicsView.ScrollHandDrag)  # Modo de arrastar com botão esquerdo
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.viewport().update()

        # Habilitar eventos de arrasto para scroll
        self.setInteractive(True)

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

        # 2. Configurações adicionais
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        # assert hasattr(self._scene, 'selectionChanged'), \
        #     "Cena deve implementar sinal selectionChanged"
        self.setup_connections()  

        print("Elementos na cena:", self.scene.items())  # Deve mostrar os elementos adicionados

    def update_connections(self):
        """Atualiza todas as conexões cruzadas"""
        # Obter todas as conexões da cena
        self.connections = [item for item in self.scene.items() if isinstance(item, BPMNConnection)]
        
        # Atualizar conexões cruzadas
        for connection in self.connections:
            # Encontrar todas as conexões que cruzam com a atual
            crossing = [c for c in self.connections 
                       if c != connection and 
                       c.line().intersects(connection.line())]
            connection.crossing_connections = crossing
            
            # Atualizar visual se houver cruzamentos
            if crossing:
                connection.update_position()

    def on_element_selected(self, element):
        dialog = PropertyDialog(element, self)  # 👈 Diálogo modal
        dialog.exec_()

    def setup_connections(self):
        """Conecta sinais de movimento dos elementos"""
        for element in self.elements:
            element.moved.connect(self.on_element_moved)  # ← Conexão do sinal

    def on_element_moved(self):
        """Atualiza todas as conexões do elemento movido"""
        sender_element = self.sender()  # Obtém o elemento que emitiu o sinal
        for connection in sender_element.connections:
            connection.update_path()
        # self.canvas.update_connections() 
        self.update_connections()  # ← Garantir atualização

    def add_element(self, element_type: str, pos: QPointF):
        valid_types = ['start', 'task', 'gateway']
        if element_type not in valid_types:
            raise ValueError(f"Tipo inválido: {element_type}")
        
        element = BPMNElement(element_type, pos)
        if self.editor_ref:
            element.set_editor_reference(self.editor_ref)
        element.setPos(pos)
        self.scene.addItem(element)
        self.elements.append(element)
        return element
    def add_element(self, element_type: str, pos: QPointF):
        valid_types = ['start', 'task', 'gateway']
        if element_type not in valid_types:
            raise ValueError(f"Tipo inválido: {element_type}")
        
        element = BPMNElement(element_type, pos)
        if self.editor_ref:
            element.set_editor_reference(self.editor_ref)
        element.setPos(pos)
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
        # if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-bpmn-element"):
            element_type = bytes(event.mimeData().data("application/x-bpmn-element")).decode()
            pos = self.mapToScene(event.pos())
            self.add_element(element_type, pos)
            event.acceptProposedAction()

    def create_connection(self, source, target):
        """Cria uma conexão entre dois elementos BPMN"""
        try:
            # Validação crítica
            if not source or not target or source == target:
                return None
                
            # Verificar se já existe uma conexão entre os elementos
            if not hasattr(source, 'connections'):
                source.connections = []
            if not hasattr(target, 'connections'):
                target.connections = []
                
            for conn in source.connections:
                if conn.source == source and conn.target == target:
                    return None
                
            # Criar e configurar a conexão
            connection = BPMNConnection(source, target)
            self.scene.addItem(connection)
            connection.setZValue(-1)  # Conexões ficam abaixo dos elementos
            
            # Atualizar visual
            connection.update_position()
            connection.update_path()
            
            # Atualizar conexões cruzadas
            self.connections = [item for item in self.scene.items() if isinstance(item, BPMNConnection)]
            self.update_connections()
            
            return connection
            
        except Exception as e:
            logging.error(f"Erro ao criar conexão: {str(e)}")
            return None

    def mousePressEvent(self, event):
        if self.mode == "select":
            super().mousePressEvent(event)
            return

        if self.mode == "connection" and event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            item = self.scene.itemAt(scene_pos, self.transform())
            
            if isinstance(item, BPMNElement):
                if not self.connection_source:
                    # Iniciar nova conexão
                    self.connection_source = item
                    source_center = item.sceneBoundingRect().center()
                    source_pos = item.mapToScene(source_center)
                    self.temp_connection = QGraphicsLineItem()
                    self.temp_connection.setPen(QPen(Qt.black, 2, Qt.DashLine))
                    self.temp_connection.setLine(QLineF(source_pos, scene_pos))
                    self.scene.addItem(self.temp_connection)
                    self.setCursor(Qt.CrossCursor)
                else:
                    # Finalizar conexão
                    if item != self.connection_source:
                        connection = self.create_connection(self.connection_source, item)
                        if connection:
                            self.connection_source.connections.append(connection)
                            item.connections.append(connection)
                            self.connections.append(connection)
                            self.update_connections()
                    
                    # Limpar estado
                    if self.temp_connection:
                        self.scene.removeItem(self.temp_connection)
                        self.temp_connection = None
                    self.connection_source = None
                    self.setCursor(Qt.ArrowCursor)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mode == "connection" and self.temp_connection and self.connection_source:
            scene_pos = self.mapToScene(event.pos())
            source_center = self.connection_source.sceneBoundingRect().center()
            source_pos = self.connection_source.mapToScene(source_center)
            self.temp_connection.setLine(QLineF(source_pos, scene_pos))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mode == "connection" and self.temp_connection and event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            item = self.scene.itemAt(scene_pos, self.transform())
            
            if isinstance(item, BPMNElement) and item != self.connection_source:
                connection = self.create_connection(self.connection_source, item)
                if connection:
                    self.connection_source.connections.append(connection)
                    item.connections.append(connection)
                    self.connections.append(connection)
                    self.update_connections()
            
            # Limpar estado
            if self.temp_connection:
                self.scene.removeItem(self.temp_connection)
                self.temp_connection = None
            self.connection_source = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def setMode(self, mode):
        self.mode = mode
        if mode == "select":
            self.setCursor(Qt.ArrowCursor)
            self.setDragMode(QGraphicsView.RubberBandDrag)
            self.setInteractive(True)  # Garante que os itens possam ser selecionados
            self.setRubberBandSelectionMode(Qt.IntersectsItemShape)  # Melhora a detecção de seleção
        elif mode == "connection":
            self.setCursor(Qt.CrossCursor)
            self.setDragMode(QGraphicsView.NoDrag)
            self.setInteractive(False)  # Desativa interação durante criação de conexão
        elif mode == "create":
            self.setCursor(Qt.PointingHandCursor)
            self.setDragMode(QGraphicsView.NoDrag)
            self.setInteractive(False)  # Desativa interação durante criação de elementos


    def auto_route_connections(self):
        """Evita sobreposições usando algoritmo de força direcional"""
        for connection in self.connections:
            if connection.has_crossings():
                connection.adjust_path_around_obstacles()

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

    def start_connection(self, element):
        self.connection_source = element
        self.connection_line = QGraphicsLineItem()  # ← Criação explícita
        self.scene().addItem(self.connection_line)  # ← Adição à cena

    def connection_mouse_move(self, event):
        if self.temp_connection:
            source_center = self.temp_connection.line().p1()
            end_pos = self.mapToScene(event.pos())
            self.temp_connection.setLine(QLineF(source_center, end_pos))
        super().mouseMoveEvent(event)

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

    # # def mousePressEvent(self, event):
    # #     # Limpar seleção apenas ao clicar em área vazia
    # #     if event.button() == Qt.LeftButton:
    # #         item = self.itemAt(event.pos())
    # #         if not item:  # Só limpa se clicar fora dos elementos
    # #             self.scene.clearSelection()
    # #         self.setDragMode(QGraphicsView.RubberBandDrag)  # Modo de seleção

    # #     if event.button() == Qt.RightButton:
    # #         self.setDragMode(QGraphicsView.ScrollHandDrag)
    # #         fake_event = QMouseEvent(
    # #             QEvent.MouseButtonPress, 
    # #             QPointF(event.pos()), 
    # #             Qt.LeftButton, 
    # #             Qt.LeftButton, 
    # #             Qt.NoModifier
    # #         )

    # #         # fake_event.setButton(Qt.LeftButton)  # Simular clique esquerdo
    # #         super().mousePressEvent(fake_event)
    # #     else:        
    # #         super().mousePressEvent(event)
    # def mousePressEvent(self, event):
    #     if self.mode == "connection":
    #         item = self.itemAt(event.scenePos(), QTransform())
    #         if isinstance(item, BPMNElement):
    #             # Cria uma conexão temporária apenas com o elemento inicial
    #             self.temp_connection = BPMNConnection(item)
    #             self.addItem(self.temp_connection)
    #     else:
    #         super().mousePressEvent(event)


    # def mouseMoveEvent(self, event):
    #     # Atualiza a conexão temporária enquanto o mouse se move
    #     if self.temp_connection:
    #         self.temp_connection.updatePath()
        
    #     super().mouseMoveEvent(event)

    # def mouseReleaseEvent(self, event):
    #     try:
    #         if event.button() == Qt.RightButton:
    #             self.setDragMode(QGraphicsView.RubberBandDrag)
                
    #             # Obter elementos BPMN selecionados
    #             selected_items = [item for item in self.scene.selectedItems() 
    #                             if isinstance(item, BPMNElement)]
                
    #             if len(selected_items) == 2:
    #                 source, target = selected_items
    #                 connection = self.create_connection(source, target)
    #                 if connection:
    #                     self.scene.update()
    #                     logging.info(f"Conexão criada entre {source.name} e {target.name}")
    #                 else:
    #                     QMessageBox.warning(self, "Aviso", 
    #                         "Não foi possível criar a conexão. Verifique se já existe uma conexão entre estes elementos.")
    #             elif len(selected_items) > 0:
    #                 QMessageBox.warning(self, "Aviso", 
    #                     "Selecione exatamente 2 elementos para conectar.")
            
    #         super().mouseReleaseEvent(event)
            
    #     except Exception as e:
    #         logging.error(f"Erro ao criar conexão: {str(e)}")
    #         QMessageBox.critical(self, "Erro", 
    #             "Ocorreu um erro ao tentar criar a conexão.")
    def validateConnection(self, start, end):
        if not (isinstance(start, BPMNElement) and isinstance(end, BPMNElement)):
            return False
        if start == end:
            return False
        return True

    # def mouseReleaseEvent(self, event):
    #     if self.temp_connection:
    #         item = self.itemAt(event.scenePos(), QTransform())
            
    #         if isinstance(item, BPMNElement):
    #             # Usa o método seguro para definir o elemento final
    #             self.temp_connection.setEndElement(item)
    #             # Adiciona à lista de conexões do canvas
    #             self.connections.append(self.temp_connection)
    #         else:
    #             # Remove conexões não finalizadas
    #             self.scene().removeItem(self.temp_connection)
            
    #         # Limpa a referência temporária
    #         self.temp_connection = None
        
    #     super().mouseReleaseEvent(event)

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

    def remove_connection(self, connection):
        """Remove uma conexão da cena e da lista"""
        self.scene().removeItem(connection)
        if connection in self.connections:
            self.connections.remove(connection)

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
            # Verificar se o editor tem o atributo properties antes de tentar acessá-lo
            editor = self.editor_ref() if isinstance(self.editor_ref, ref) else self.editor_ref
            if editor and hasattr(editor, 'properties'):
                editor.properties.hide()

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

    def setMode(self, mode):
        """
        Define o modo de operação do canvas
        
        Args:
            mode (str): O modo de operação ("select", "connection", "create")
        """
        self.mode = mode
        
        # Atualiza o cursor com base no modo
        if mode == "connection":
            self.setCursor(Qt.CrossCursor)
        elif mode == "select":
            self.setCursor(Qt.ArrowCursor)
        elif mode == "create":
            self.setCursor(Qt.PointingHandCursor)
