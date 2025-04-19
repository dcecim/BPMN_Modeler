import sys
from PyQt5.QtWidgets import (QGraphicsRectItem, QGraphicsLineItem, QGraphicsItem, 
                             QGraphicsObject, QDialog, QGraphicsPathItem)
from PyQt5.QtGui import (QColor, QBrush, QPen, QPolygonF, QPainterPath, QPainter, QCursor)
from PyQt5.QtCore import (Qt, QPointF, QRectF, QLineF, pyqtSignal)

from ..dialogs.property_dialog import PropertyDialog

import uuid 
import logging
logger = logging.getLogger(__name__)

# from PyQt5.QtCore import QObject, pyqtSignal
class BPMNElement(QGraphicsObject):
    elementMoved = pyqtSignal()  # Sinal para notificar movimento

    def __init__(self, element_type: str, pos: QPointF):
        super().__init__()
        self.rect = QRectF(0, 0, 0, 0)
        self.actions = {}  # Dicionário para armazenar ações e seus parâmetros
        self.unique_id = uuid.uuid4().hex  # Gerar ID único
        self.setData(0, self.unique_id)   # Armazenar no item

        # Define o tamanho padrão do elemento baseado no tipo
        if element_type in ["task", "subprocess"]:
            width, height = 100, 80
        elif element_type in ["start_event", "end_event", "intermediate_event"]:
            width, height = 40, 40
        elif element_type in ["gateway"]:
            width, height = 50, 50
        else:
            width, height = 60, 60
            
        # Centraliza o retângulo na posição fornecida
        x = pos.x() - width/2
        y = pos.y() - height/2
        self.rect = QRectF(x, y, width, height)

        self.name = "Novo Elemento"
        self.description = ""
        self.setPos(pos)

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)

        self.element_type = element_type
        self.connections = []  # Lista de conexões
        
    def setPos(self, *args):
        super().setPos(*args)
        self.elementMoved.emit()  # Emitir o sinal quando a posição mudar

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # Atualizar conexões quando o elemento é movido
            for connection in self.connections:
                connection.update_position()
            self.elementMoved.emit()  # Emitir sinal de movimento
        return super().itemChange(change, value)

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
        if self.element_type == 'gateway':
            return QRectF(-10, -10, 120, 90)  # Área maior para o losango
        return self.rect
    
    def shape(self):
        path = QPainterPath()
        if self.element_type == 'start':
            path.addEllipse(self.rect)
        elif self.element_type == 'gateway':
            diamond = QPolygonF([
                QPointF(self.rect.center().x(), self.rect.top()),
                QPointF(self.rect.right(), self.rect.center().y()),
                QPointF(self.rect.center().x(), self.rect.bottom()),
                QPointF(self.rect.left(), self.rect.center().y())
            ])
            path.addPolygon(diamond)
        else:
            path.addRoundedRect(self.rect, 10, 10)
        return path

    def paint(self, painter: QPainter, option, widget=None):
        # Destacar seleção
        if self.isSelected():
            painter.setPen(QPen(Qt.yellow, 3))
        else:
            painter.setPen(QPen(Qt.black, 1))
    
        painter.setBrush(self.get_color())
        
        # Desenha pontos de conexão quando selecionado
        if self.isSelected():
            painter.setPen(QPen(Qt.blue, 2))
            for point in self.connectionPoints():
                painter.drawEllipse(point, 4, 4)
        
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

        # # Desenha elipse nos cruzamentos
        # for other in self.crossing_connections:
        #     intersection = self.path.intersected(other.path)
        #     if not intersection.isEmpty():
        #         rect = intersection.boundingRect()
        #         painter.drawEllipse(rect.center(), 3, 3)  # Raio ajustável

    # Adicionar na classe BPMNElement:
    def set_editor_reference(self, editor_ref):
        self.editor_ref = editor_ref

    # Modificar o método:
    def mouseDoubleClickEvent(self, event):
        # Abre diálogo de edição
        dialog = PropertyDialog()
        dialog.name_edit.setText(self.name)
        dialog.desc_edit.setText(self.description)
        
        # Configurar ação atual se existir
        if self.actions:
            action = list(self.actions.items())[0]  # Pega a primeira ação
            dialog.action_combo.setCurrentText(action[0])
            dialog.param_edit.setText(action[1])
        
        if dialog.exec_() == QDialog.Accepted:
            new_props = dialog.get_properties()
            self.name = new_props['name']
            self.description = new_props['description']
            
            # Atualizar ações
            action_data = new_props['action']
            if action_data['type']:
                self.actions = {action_data['type']: action_data['params']}
            
            self.update()  # Atualiza a exibição
            
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        # Forçar atualização em tempo real
        super().mouseMoveEvent(event)
        self.scene().update()

    def add_connection(self, connection):
        if connection not in self.connections:
            self.connections.append(connection)

    def remove_connection(self, connection):
        if connection in self.connections:
            self.connections.remove(connection)

    def connectionPoints(self):
        """Retorna os pontos de conexão do elemento"""
        rect = self.rect()
        center = rect.center()
        return [
            QPointF(center.x(), rect.top()),    # Topo
            QPointF(rect.right(), center.y()),  # Direita
            QPointF(center.x(), rect.bottom()), # Base
            QPointF(rect.left(), center.y())    # Esquerda
        ]
    
    def nearestConnectionPoint(self, point: QPointF):
        """Encontra o ponto de conexão mais próximo de uma coordenada"""
        scene_point = self.mapFromScene(point)
        points = self.connectionPoints()
        return min(points, key=lambda p: (p - scene_point).manhattanLength())

class BPMNConnection(QGraphicsPathItem):
    def __init__(self, start_element, end_element=None):
        super().__init__()
        self.unique_id = uuid.uuid4().hex
        self._start_element = start_element
        self._end_element = end_element
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        
        # Garantir que o elemento inicial tenha uma lista de conexões
        if self._start_element is not None:
            if not hasattr(self._start_element, 'connections'):
                self._start_element.connections = []
            if self not in self._start_element.connections:
                self._start_element.connections.append(self)
        
        # Só adiciona ao elemento final se ele existir
        if self._end_element is not None:
            if not hasattr(self._end_element, 'connections'):
                self._end_element.connections = []
            if self not in self._end_element.connections:
                self._end_element.connections.append(self)
        
        self.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        self.setZValue(-1)  # Conexões ficam abaixo dos elementos
        self.crossing_connections = []
        self.line_style = {
            'type': 'L',  # 'L' | 'straight' | 'curved'
            'crossing_style': 'ellipse',  # 'ellipse' | 'bridge'
            'color': QColor('#2c3e50'),
            'dash_pattern': []
        }
        self.unique_id = uuid.uuid4().hex  # ← ID único para conexão

        # Configurações de serialização
        self.setData(0, self.unique_id)  # Armazenar ID no item
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        
        # Configurações visuais
        self.setZValue(-1)  # Ficar atrás dos elementos
        self.setPen(QPen(Qt.darkGray, 2, Qt.SolidLine, Qt.RoundCap))  # Atualizado
        self.update_position()

        self._start.elementMoved.connect(self.updatePosition)
        self._end.elementMoved.connect(self.updatePosition)

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

    def start_element(self):
        return self._start_element

    def end_element(self):
        return self._end_element

    def updatePosition(self):
        # Atualiza a posição da linha baseado na posição dos elementos
        start_pos = self._start_element.pos()
        end_pos = self._end_element.pos()
        self.setLine(start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y())

    def update_position(self):
        if not self._start_element or not self._end_element:
            return
        
        # Encontra os pontos de conexão mais próximos
        start_pos = self._start_element.scenePos()
        end_pos = self._end_element.scenePos()
        
        # Calcula os pontos de conexão mais próximos
        start_point = self._start_element.nearestConnectionPoint(end_pos)
        end_point = self._end_element.nearestConnectionPoint(start_pos)
        
        # Converte para coordenadas da cena
        start_scene = self._start_element.mapToScene(start_point)
        end_scene = self._end_element.mapToScene(end_point)
        
        # Cria o caminho da conexão
        path = QPainterPath()
        path.moveTo(start_scene)
        
        # Calcula os pontos de controle para a curva
        dx = end_scene.x() - start_scene.x()
        dy = end_scene.y() - start_scene.y()
        ctrl1 = QPointF(start_scene.x() + dx * 0.5, start_scene.y())
        ctrl2 = QPointF(end_scene.x() - dx * 0.5, end_scene.y())
        
        # Desenha a curva Bezier
        path.cubicTo(ctrl1, ctrl2, end_scene)
        
        # Atualiza o caminho
        self.setPath(path)

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

        for other in self.crossing_connections:
            intersection = self.path().intersected(other.path())
            if not intersection.isEmpty():
                rect = intersection.boundingRect()
                painter.drawEllipse(rect.center(), 3, 3)

    def updatePath(self):
        path = QPainterPath()
        
        # Só desenha o caminho completo se ambos os elementos existirem
        if self._start_element is not None:
            # Ponto inicial sempre disponível
            start_point = self._start_element.scenePos()
            
            # Se temos um elemento final, usamos sua posição
            if self._end_element is not None:
                end_point = self._end_element.scenePos()
                
                # Cálculo dos pontos de conexão
                start_point = self._start_element.nearestConnectionPoint(end_point)
                end_point = self._end_element.nearestConnectionPoint(start_point)
            else:
                # Caso contrário, usamos a posição atual do cursor
                cursor_pos = QCursor.pos()
                view_pos = self.scene().views()[0].mapFromGlobal(cursor_pos)
                scene_pos = self.scene().views()[0].mapToScene(view_pos)
                end_point = scene_pos
                start_point = self._start_element.nearestConnectionPoint(end_point)
            
            # Criação da curva Bézier
            mid_x = (start_point.x() + end_point.x()) / 2
            mid_y = (start_point.y() + end_point.y()) / 2
            
            path.moveTo(start_point)
            path.cubicTo(
                QPointF(mid_x, start_point.y()),
                QPointF(mid_x, end_point.y()),
                end_point
            )
        
        self.setPath(path)
    
    def setEndElement(self, element):
        """Define o elemento final da conexão com segurança"""
        # Remove a conexão do elemento anterior, se existir
        if self._end_element is not None and hasattr(self._end_element, 'connections'):
            if self in self._end_element.connections:
                self._end_element.connections.remove(self)
        
        # Define o novo elemento final
        self._end_element = element
        
        # Adiciona a conexão ao novo elemento
        if self._end_element is not None:
            if not hasattr(self._end_element, 'connections'):
                self._end_element.connections = []
            self._end_element.connections.append(self)
        
        # Atualiza o caminho visual
        self.updatePath()

    def has_crossings(self):
        """Verifica intersecções com outras conexões"""
        scene = self.scene()
        if not scene:
            return False
            
        # Usa boundingRect() para melhor performance
        area = self.path().boundingRect()  
        items = scene.items(area, Qt.IntersectsItemShape)
        
        return any(
            isinstance(item, BPMNConnection) 
            and item != self  # Ignora a própria conexão
            and self.path().intersects(item.path())
            for item in items
        )
    

