from PyQt5.QtWidgets import (QVBoxLayout, QWidget, QPushButton, QLineEdit, QTextEdit, 
                            QLabel)

import logging
logger = logging.getLogger(__name__)

class PropertiesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_element = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Campos básicos
        self.name_label = QLabel("Nome:")
        self.name_input = QLineEdit()
        self.desc_label = QLabel("Descrição:")
        self.desc_input = QTextEdit()
        
        # Seção de Ações
        self.action_label = QLabel("Ações:")
        action_layout = QHBoxLayout()
        
        self.action_combo = QComboBox()
        self.action_combo.addItems([
            "Enviar Email",
            "Validar Dados",
            "Atualizar Sistema",
            "Gerar Relatório"
        ])
        
        self.param_input = QLineEdit()
        self.param_input.setPlaceholderText("Parâmetros da ação")
        
        action_layout.addWidget(self.action_combo)
        action_layout.addWidget(self.param_input)
        
        # Adiciona widgets ao layout principal
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.desc_label)
        layout.addWidget(self.desc_input)
        layout.addWidget(self.action_label)
        layout.addLayout(action_layout)
        layout.addStretch()

        # Conexões
        self.name_input.textChanged.connect(self.update_element_name)
        self.desc_input.textChanged.connect(self.update_element_desc)
        self.action_combo.currentTextChanged.connect(self.update_element_action)
        self.param_input.textChanged.connect(self.update_element_params)

    def update_properties(self, element):
        self.current_element = element
        self.name_input.setText(element.name)
        self.desc_input.setPlainText(element.description)
        
        if hasattr(element, 'actions'):
            action_type = element.actions.get('type')
            if action_type:
                index = self.action_combo.findText(action_type)
                if index >= 0:
                    self.action_combo.setCurrentIndex(index)
            
            params = element.actions.get('params')
            if params:
                self.param_input.setText(params)

    def update_element_name(self, text):
        if self.current_element:
            self.current_element.name = text
            self.current_element.update()

    def update_element_desc(self):
        if self.current_element:
            self.current_element.description = self.desc_input.toPlainText()
    
    def update_element_action(self, action_type):
        if self.current_element:
            if not hasattr(self.current_element, 'actions'):
                self.current_element.actions = {}
            self.current_element.actions['type'] = action_type
            self.current_element.update()
    
    def update_element_params(self, params):
        if self.current_element:
            if not hasattr(self.current_element, 'actions'):
                self.current_element.actions = {}
            self.current_element.actions['params'] = params
            self.current_element.update()

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

