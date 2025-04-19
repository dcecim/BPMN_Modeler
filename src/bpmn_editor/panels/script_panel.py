from PyQt5.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QLabel, QComboBox, 
                            QLineEdit, QPushButton, QHBoxLayout)
from PyQt5.QtCore import Qt, pyqtSignal
import json
import os

class ScriptPanel(QDockWidget):
    script_changed = pyqtSignal(dict)  # Sinal para notificar mudanças no roteiro
    
    def __init__(self):
        super().__init__("Roteiro BPMN")
        self.setFeatures(QDockWidget.DockWidgetFloatable | 
                        QDockWidget.DockWidgetMovable)
        self.script_actions = []
        self.setup_ui()
    
    def setup_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Combobox de Ações
        action_layout = QHBoxLayout()
        self.cb_actions = QComboBox()
        self.cb_actions.addItems([
            "Enviar Email",
            "Validar Dados",
            "Atualizar Sistema",
            "Gerar Relatório"
        ])
        
        # Campo de Parâmetros
        self.param_input = QLineEdit()
        self.param_input.setPlaceholderText("Parâmetros da ação")
        
        # Botão Adicionar
        add_btn = QPushButton("+")
        add_btn.clicked.connect(self.add_action)
        
        action_layout.addWidget(self.cb_actions)
        action_layout.addWidget(self.param_input)
        action_layout.addWidget(add_btn)
        
        layout.addWidget(QLabel("Ações do Roteiro:"))
        layout.addLayout(action_layout)
        
        # Lista de ações adicionadas
        self.actions_list = QVBoxLayout()
        layout.addLayout(self.actions_list)
        
        # Botões de Salvar
        save_layout = QHBoxLayout()
        save_json_btn = QPushButton("Salvar JSON")
        save_txt_btn = QPushButton("Salvar TXT")
        save_json_btn.clicked.connect(self.save_json)
        save_txt_btn.clicked.connect(self.save_txt)
        
        save_layout.addWidget(save_json_btn)
        save_layout.addWidget(save_txt_btn)
        layout.addLayout(save_layout)
        
        layout.addStretch()
        self.setWidget(container)
    
    def add_action(self):
        action = self.cb_actions.currentText()
        params = self.param_input.text()
        
        if not params:
            return
            
        action_data = {"action": action, "params": params}
        self.script_actions.append(action_data)
        
        # Criar widget para a ação
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        
        action_text = QLabel(f"{action} - {params}")
        remove_btn = QPushButton("X")
        remove_btn.clicked.connect(lambda: self.remove_action(action_widget, action_data))
        
        action_layout.addWidget(action_text)
        action_layout.addWidget(remove_btn)
        
        self.actions_list.addWidget(action_widget)
        self.param_input.clear()
        
    def remove_action(self, widget, action_data):
        self.script_actions.remove(action_data)
        widget.deleteLater()
        
    def save_json(self):
        if not self.script_actions:
            return
            
        script_dir = os.path.join(os.getcwd(), "ROTEIRO")
        os.makedirs(script_dir, exist_ok=True)
        
        with open(os.path.join(script_dir, "roteiro.json"), "w", encoding="utf-8") as f:
            json.dump({"actions": self.script_actions}, f, indent=2, ensure_ascii=False)
            
    def save_txt(self):
        if not self.script_actions:
            return
            
        script_dir = os.path.join(os.getcwd(), "ROTEIRO")
        os.makedirs(script_dir, exist_ok=True)
        
        with open(os.path.join(script_dir, "roteiro.txt"), "w", encoding="utf-8") as f:
            for action in self.script_actions:
                f.write(f"ação={action['action']}, valor={action['params']}\n")