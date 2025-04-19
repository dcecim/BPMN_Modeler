from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QLineEdit, QHBoxLayout,
                             QDockWidget, QPushButton)
from PyQt5.QtCore import pyqtSignal

class ActionsPanel(QDockWidget):
    action_changed = pyqtSignal(dict)  # Sinal para notificar mudanças
    
    def __init__(self):
        super().__init__()
        if not self.layout():  # ← Verifica se já tem layout
            self.setLayout(QVBoxLayout())
        container = QWidget()
        self.layout = QVBoxLayout(container)  # ← Crie layout no container
        self.setWidget(container)  # ← Atribua o container ao dock
       
    def setup_ui(self):
        layout = QVBoxLayout()
        self.btn_start = QPushButton('Start/End', self)
        self.btn_start.element_type = "start"  # 👈 Identificador único
        self.btn_task = QPushButton("Tarefa", self)
        self.btn_task.element_type = "task"  # 👈 Identificador único
        self.btn_gateway = QPushButton("Gateway", self)
        self.btn_gateway.element_type = "gateway"  # 👈 Identificador único
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_task)
        layout.addWidget(self.btn_gateway)
        
        container = QWidget()
        container.setLayout(layout)
        self.setWidget(container)


        layout = QVBoxLayout()
        
        # Combobox de Ações
        self.cb_actions = QComboBox()
        self.cb_actions.addItems([
            "Enviar Email", 
            "Validar Dados",
            "Atualizar Sistema",
            "Gerar Relatório"
        ])
        self.cb_actions.currentIndexChanged.connect(self.on_action_changed)
        
        # Campo de Parâmetros
        self.param_input = QLineEdit()
        self.param_input.setPlaceholderText("Parâmetros (ex: template=relatorio.pdf)")
        self.param_input.textChanged.connect(self.on_param_changed)
        
        # Layout Horizontal
        action_row = QHBoxLayout()
        action_row.addWidget(self.cb_actions)
        action_row.addWidget(self.param_input)
        
        layout.addWidget(QLabel("Ações do Elemento:"))
        layout.addLayout(action_row)
        self.setLayout(layout)
        
    def on_action_changed(self, index):
        action = self.cb_actions.itemText(index)
        if self.current_element:
            self.current_element.actions[action] = self.param_input.text()
            
    def on_param_changed(self, text):
        if self.current_element and self.cb_actions.currentText():
            action = self.cb_actions.currentText()
            self.current_element.actions[action] = text
            
    def load_element(self, element):
        self.current_element = element
        self.cb_actions.clear()
        self.cb_actions.addItems(element.actions.keys())
        self.param_input.clear()
