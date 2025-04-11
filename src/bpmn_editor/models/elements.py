import sys
from PyQt5.QtWidgets import (QGraphicsRectItem, QGraphicsLineItem, QGraphicsItem)
from PyQt5.QtGui import (QColor, QBrush, QPen, QPolygonF, QPainterPath, )
from PyQt5.QtCore import (Qt, QPointF, QRectF, QLineF)

import uuid 
import logging
logger = logging.getLogger(__name__)

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

