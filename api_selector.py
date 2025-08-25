# -*- coding: utf-8 -*-
"""
Created on Sat Jul 19 15:19:39 2025

@author: Sri.Sakthivel
"""

from PyQt5.QtWidgets import QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QButtonGroup
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import configparser
import os

class ApiSelector(QFrame):
    def __init__(self, api_ini_path, parent=None):
        super().__init__(parent)
        self.setFixedSize(350, 120)
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #444;
            }
            QPushButton:checked {
                background-color: #0078d7;
                border: 2px solid #0078d7;
            }
        """)
        self.api_ini_path = api_ini_path
        self.selected_api = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        label = QLabel("Select Mode")
        label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        label.setStyleSheet("color: black; background: transparent; border: none; font-size: 30px;")
        
        self.btn_prd = QPushButton("PRD")
        self.btn_ejo = QPushButton("EJO")

        self.btn_prd.setCheckable(True)
        self.btn_ejo.setCheckable(True)
        
        button_style = """
            QPushButton {
                background-color: #f0f0f0;
                color: black;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 4px;
                font-size: 25px;
            }
            QPushButton:checked {
                background-color: #0078d7;
                border: 1px solid #0078d7;
            }
        """
        self.btn_prd.setStyleSheet(button_style)
        self.btn_ejo.setStyleSheet(button_style)

        self.group = QButtonGroup()
        self.group.addButton(self.btn_prd)
        self.group.addButton(self.btn_ejo)

        self.btn_prd.setChecked(True)

        self.btn_prd.clicked.connect(lambda: self.select_api("PRD"))
        self.btn_ejo.clicked.connect(lambda: self.select_api("EJO"))

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addWidget(self.btn_prd)
        btn_layout.addWidget(self.btn_ejo)

        layout.addWidget(label)
        layout.addLayout(btn_layout)
        
        self.select_api("PRD")

    def select_api(self, name):
        self.selected_api = name.upper()
        
    def get_selected_api(self):
        return self.selected_api
        
    def get_selected_api_url(self, vin=""):
        config = configparser.ConfigParser()
        default_url = "http://10.121.2.107:3000/vehicles/flashFile/prd"
        try:
            if not os.path.exists(self.api_ini_path):
                self.parent().instruction_box.append(f"Error: api.ini not found at {self.api_ini_path}. Using default URL.")
                return default_url.rstrip("/") + f"/{vin}" if vin else default_url

            config.read(self.api_ini_path)
            if not config.sections():
                self.parent().instruction_box.append(f"Error: api.ini is empty or corrupted. Using default URL.")
                return default_url.rstrip("/") + f"/{vin}" if vin else default_url

            if not self.selected_api:
                self.parent().instruction_box.append("Error: No API mode selected (PRD/EJO). Using default URL.")
                return default_url.rstrip("/") + f"/{vin}" if vin else default_url

            api_key = self.selected_api.upper()
            if "API" not in config or api_key not in config["API"]:
                self.parent().instruction_box.append(f"Error: Section 'API' or key '{api_key}' not found in api.ini. Using default URL.")
                return default_url.rstrip("/") + f"/{vin}" if vin else default_url

            base_url = config["API"][api_key]
            if not base_url:
                self.parent().instruction_box.append(f"Error: Empty URL for '{api_key}' in api.ini. Using default URL.")
                return default_url.rstrip("/") + f"/{vin}" if vin else default_url

            if vin:
                base_url = base_url.rstrip("/") + f"/{vin}"
            return base_url
        except Exception as e:
            self.parent().instruction_box.append(f"Error reading api.ini: {e}. Using default URL.")
            return default_url.rstrip("/") + f"/{vin}" if vin else default_url