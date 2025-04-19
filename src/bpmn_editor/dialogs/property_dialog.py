from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox,
                            QComboBox, QHBoxLayout)

class PropertyDialog(QDialog):
    def __init__(self, element=None, parent=None):
        super().__init__(parent)
        self.element = element
        self.setWindowTitle("Editar Elemento")
        
        layout = QVBoxLayout()
        
        # Campo para Nome
        self.name_edit = QLineEdit()
        if element and hasattr(element, 'name'):
            self.name_edit.setText(element.name)
        layout.addWidget(QLabel("Nome:"))
        layout.addWidget(self.name_edit)
        
        # Campo para Descrição
        self.desc_edit = QLineEdit()
        if element and hasattr(element, 'description'):
            self.desc_edit.setText(element.description)
        layout.addWidget(QLabel("Descrição:"))
        layout.addWidget(self.desc_edit)
        
        # Seção de Ações
        layout.addWidget(QLabel("Ações:"))
        
        # Layout horizontal para ação e parâmetros
        action_layout = QHBoxLayout()
        
        # ComboBox para ações
        self.action_combo = QComboBox()
        self.action_combo.addItems([
            "Enviar Email",
            "Validar Dados",
            "Atualizar Sistema",
            "Gerar Relatório"
        ])
        if element and hasattr(element, 'actions'):
            current_action = element.actions.get('type')
            if current_action:
                index = self.action_combo.findText(current_action)
                if index >= 0:
                    self.action_combo.setCurrentIndex(index)
        action_layout.addWidget(self.action_combo)
        
        # Campo para parâmetros
        self.param_edit = QLineEdit()
        self.param_edit.setPlaceholderText("Parâmetros da ação")
        if element and hasattr(element, 'actions'):
            params = element.actions.get('params')
            if params:
                self.param_edit.setText(params)
        action_layout.addWidget(self.param_edit)
        
        layout.addLayout(action_layout)
        
        # Botões OK/Cancelar
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_properties(self):
        return {
            'name': self.name_edit.text(),
            'description': self.desc_edit.text(),
            'action': {
                'type': self.action_combo.currentText(),
                'params': self.param_edit.text()
            }
        }
        
    def accept(self):
        if self.element:
            props = self.get_properties()
            self.element.name = props['name']
            self.element.description = props['description']
            self.element.actions = props['action']
        super().accept()
