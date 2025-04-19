import pytest
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QApplication
from bpmn_editor.models.elements import BPMNElement, BPMNConnection

@pytest.fixture(scope="session")
def qapp():
    app = QApplication([])
    yield app
    app.quit()

def test_connection_creation(qapp):  # adicione o fixture qapp como parâmetro
    # Criando elementos com QPointF em vez de tuplas
    element1 = BPMNElement(element_type='task', pos=QPointF(0, 0))
    element2 = BPMNElement(element_type='task', pos=QPointF(100, 100))
    
    # Resto do teste...
    
    connection = BPMNConnection(element1, element2)
    assert connection.start_element() == element1
    assert connection.end_element() == element2
