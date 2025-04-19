from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QSplitter,
                            QAction, QFileDialog, QMessageBox, QSplitter)
from PyQt5.QtGui import (QIcon)
from PyQt5.QtCore import (Qt, QPointF, QTimer)

from bpmn_editor.views.toolbar import DragButton, BPMNPalette

from .utils.exceptions import excepthook
from .models.elements import BPMNConnection, BPMNElement
from .views.canvas import BPMNCanvas
from .dialogs.property_dialog import PropertyDialog
from .panels.actions_panel import ActionsPanel
from .panels.script_panel import ScriptPanel

from functools import partial 
from weakref import ref
from datetime import datetime

import logging, json, pickle
import locale
import sys
from pathlib import Path

from datetime import datetime
import os
import logging
logger = logging.getLogger(__name__)

# Dentro de autoSave():
logger.info(f"Autosave realizado em {datetime.now().isoformat()}")

# Adiciona o diretório pai ao Python Path
sys.path.append(str(Path(__file__).parent.parent))

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')  # Forçar locale compatível
sys.stdout.reconfigure(encoding='utf-8')  # Configurar saída padrão

class BPMNEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.canvas = BPMNCanvas(self)
        self.actions_panel = ActionsPanel()
        self.script_panel = ScriptPanel()
        self.palette = BPMNPalette(self.canvas, self)
        self.canvas.editor_ref = self 
        self.current_file = None  # Adicionar atributo

        # Configurações de auto salvamento
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(300000)  # 5 minutos (em ms)
        self.autosave_timer.timeout.connect(self.autoSave)
        self.autosave_timer.start()  # Inicia o timer!
        self.statusBar().showMessage(f"Autosave: {datetime.now().strftime('%H:%M:%S')}", 5000)

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

        self.canvas.signals.selectionChanged.connect(self.on_selection_changed)

        self.splitter = QSplitter(Qt.Horizontal) 
        self.setCentralWidget(self.splitter) 

        self.splitter.addWidget(self.canvas)
        
        # Adiciona o painel de roteiro
        self.addDockWidget(Qt.RightDockWidgetArea, self.script_panel)

        self.property_dialog = PropertyDialog()  # Diálogo modal
        self.actions_panel = ActionsPanel()
        self.addDockWidget(Qt.LeftDockWidgetArea, self.actions_panel)

        self.splitter.setSizes([800, 200])  # Canvas (800px) + Painel (200px)
        self.splitter.setStretchFactor(0, 1)  # Canvas expande
        self.splitter.setStretchFactor(1, 1)  # Painel mantém proporção

        self.actions_panel.setStyleSheet("""
            QComboBox, QLineEdit {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QLabel {
                font-weight: bold;
                margin-top: 10px;
            }
        """)
        # Configurar a paleta existente
        self.addDockWidget(Qt.LeftDockWidgetArea, self.palette)
        self.palette.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Configurações críticas de drag-and-drop
        self.palette.setAcceptDrops(True)
        self.palette.setFocusPolicy(Qt.StrongFocus)
        self.palette.installEventFilter(self)

        print("Ações Panel visível?", self.actions_panel.isVisible())  # Deve ser True
        print("PropertyDialog:", hasattr(self, 'property_dialog'))     # Deve ser True

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

        self.toolbar = BPMNPalette(self.canvas)

        # Botões de Elementos BPMN
        elements = [
            ('Início/Fim', 'start', '#4CAF50'),  # Adicione a COR como terceiro elemento
            ('Tarefa', 'task', '#2196F3'),
            ('Gateway', 'gateway', '#FF9800')
        ]

        for text, elem_type, color in elements:  # Desempacote todos os 3 valores
            btn = DragButton(
                element_type=elem_type, 
                text='',
                icon=QIcon(''),
                color=color, 
                parent=self  # ← Parente obrigatório
            )
            btn.setText(text)
            self.palette.layout().addWidget(btn)
        
        # Layout Principal

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.palette)
        splitter.addWidget(self.canvas)
        # splitter.addWidget(self.properties)
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
        
        # Criar o canvas
        self.canvas = BPMNCanvas(self)
        
        print("Verificando toolbar...")
        if hasattr(self, 'toolbar'):
            print("self.toolbar existe:", self.toolbar)
            for button in self.toolbar.findChildren(DragButton):
                button.setCanvas(self.canvas)
        else:
            print("ERRO: self.toolbar não existe!")
            # Tentar encontrar a toolbar com outro nome
            for attr_name in dir(self):
                attr = getattr(self, attr_name)
                if isinstance(attr, QWidget) and attr_name != 'canvas':
                    print(f"Possível toolbar encontrada: {attr_name}")            

        # self.connection_button.clicked.connect(lambda: self.canvas.setMode("connection"))
        # self.select_button.clicked.connect(lambda: self.canvas.setMode("select"))
        # self.create_button.clicked.connect(lambda: self.canvas.setMode("create"))


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

    def on_selection_changed(self):
        selected = self.canvas.selectedItems()
        
        if len(selected) == 1 and isinstance(selected[0], BPMNElement):
            self.actions_panel.load_element(selected[0])
            self.splitter.handle(1).setEnabled(True)  # Permite redimensionar
            self.splitter.setSizes([300, 200])       # Mostra painel
        else:
            self.splitter.handle(1).setEnabled(False) # Bloqueia alça
            self.splitter.setSizes([300, 0])          # Esconde suavemente

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

    def autoSave(self):  # <-- ATENÇÃO À INDENTAÇÃO!
        try:
            if hasattr(self, 'current_file') and self.current_file:
                self.saveToFile(self.current_file)
            else:
                self.saveAs()  # Garanta que saveAs() existe!
            
            print(f"Autosave: {datetime.now().strftime('%H:%M:%S')}")  # Debug
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Autosave falhou:\n{str(e)}")

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
            item = selected[0]

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

    def setup_actions(self):
        # ... outras ações
        delete_action = QAction("Excluir Seleção", self)
        delete_action.triggered.connect(self.delete_selected)
        self.addAction(delete_action)

    def delete_selected(self):
        """Remove conexões e elementos selecionados"""
        for item in self.canvas.scene().selectedItems():
            if isinstance(item, BPMNConnection):
                self.canvas.remove_connection(item)
                logging.info(f"Conexão {item.id} removida")
            elif isinstance(item, BPMNElement):
                self.canvas.remove_element(item)
        
        self.canvas.scene().update()

# Adicione no final do arquivo:
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Estilo visual moderno
    window = BPMNEditor()
    window.resize(1200, 800)  # Tamanho inicial adequado
    window.show()
    sys.exit(app.exec_())

