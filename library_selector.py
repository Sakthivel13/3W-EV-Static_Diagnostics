# -*- coding: utf-8 -*-
"""
Created on Sat Jul 19 15:18:03 2025

@author: Sri.Sakthivel
"""

from PyQt5.QtWidgets import QFrame, QLabel, QComboBox, QVBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import configparser
import os

class ActiveLibrarySelector(QFrame):
    def __init__(self, library_list, default_value=None):
        super().__init__()
        self.setFixedSize(700, 120)
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #444;
            }
            QLabel {
                color: black;
                font-size: 30px;
            }
            QComboBox {
                font-size: 26px;
                padding: 6px;
                border-radius: 6px;
                background-color: #f0f0f0;
                color: black;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #f0f0f0;
                selection-background-color: #0078d7;
                color: black;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.label = QLabel("Active Library")
        layout.addWidget(self.label)

        self.combo = QComboBox()
        self.combo.addItems(library_list)

        if default_value and default_value in library_list:
            self.combo.setCurrentText(default_value)
        else:
            self.combo.setCurrentIndex(0)

        layout.addWidget(self.combo)
        self.combo.currentTextChanged.connect(self.lock_selection)
        self.selection_locked = False

    def lock_selection(self, library):
        if not self.selection_locked:
            self.selection_locked = True
            self.save_to_station_ini(library)

    def save_to_station_ini(self, library):
        config = configparser.ConfigParser()
        ini_path = os.path.join(os.path.dirname(__file__), r"D:\Python\TVS NIRIX V1.4\station.ini")
        try:
            config.read(ini_path)
            if "SETTINGS" not in config:
                config["SETTINGS"] = {}
            config["SETTINGS"]["active_library"] = library
            with open(ini_path, 'w') as configfile:
                config.write(configfile)
        except Exception as e:
            print(f"Failed to save active_library to station.ini: {e}")

    def get_selected_library(self):
        return self.combo.currentText()