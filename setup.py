from setuptools import setup, find_packages

setup(
    name="bpmn_editor",
    version="0.1.0",
    author="Divino Cecim da Silva",
    description="Editor BPMN com PyQt5",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[  # ← ÚNICA DECLARAÇÃO
        'PyQt5>=5.15.4',
        'setuptools>=62.0.0',
        'sqlalchemy>=2.0.40'
    ],
    python_requires='>=3.8',
)
