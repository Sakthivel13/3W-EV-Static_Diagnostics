# -*- coding: utf-8 -*-
"""
Created on Fri Jun 20 09:13:01 2025

@author: Sri.Sakthivel
"""

import io
import sys
import os
import configparser
import socket
import threading
import time
import requests
from PyQt5.QtWidgets import (
    QApplication, QAbstractItemView, QTextEdit, QWidget, QLabel, QHBoxLayout, QVBoxLayout, 
    QProgressBar, QFrame, QLineEdit, QComboBox, QPushButton, QButtonGroup, QSizePolicy, 
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtGui import QFont, QColor, QPalette, QIntValidator
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal, QThread
import serial.tools.list_ports
import importlib
import pandas as pd
from datetime import datetime
import json
import serial
import usb.core
import usb.util

def resource_path(relative_path):
    """ Get absolute path to resource (for bundled executable) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_file_name_from_sku(sku_number, active_library):
    mapping_file_path = resource_path(r"D:\Python\TVS_NIRIX_V1.4\SKU_File_Mapping.xlsx")
    default_sku = "GE190510"
    try:
        df = pd.read_excel(mapping_file_path)
        df.columns = df.columns.str.strip()
        df["SKU No"] = df["SKU No"].astype(str).str.strip()
        df["File Name"] = df["File Name"].astype(str).str.strip()
        df["Library"] = df["Library"].astype(str).str.strip()
        lookup_sku = sku_number.strip() if sku_number else default_sku
        matched_row = df[(df["SKU No"] == lookup_sku) & (df["Library"] == active_library)]
        if not matched_row.empty:
            return matched_row.iloc[0]["File Name"], matched_row.iloc[0]["Library"]
        else:
            #print(f"SKU '{lookup_sku}' not found for library '{active_library}'. Checking for any library match.")
            matched_row = df[df["SKU No"] == lookup_sku]
            if not matched_row.empty:
                return None, matched_row.iloc[0]["Library"]
            #print(f"SKU '{lookup_sku}' not found in any library. Using default SKU.")
            fallback_row = df[(df["SKU No"] == default_sku) & (df["Library"] == active_library)]
            return (fallback_row.iloc[0]["File Name"], fallback_row.iloc[0]["Library"]) if not fallback_row.empty else (None, None)
    except Exception as e:
        print(f"Failed to read SKU mapping file: {e}")
        return None, None

class ScannerSignalEmitter(QObject):
    vin_scanned = pyqtSignal(str)

class SerialReaderThread(QThread):
    vin_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_port = None
        self.running = True
        self.max_retries = 3
        self.retry_delay = 1

    def run(self):
        retry_count = 0
        while retry_count < self.max_retries and self.running:
            try:
                #print(f"SerialReaderThread: Attempt {retry_count + 1}/{self.max_retries} to open port {self.port} at {self.baudrate} baud")
                self.serial_port = serial.Serial(
                    self.port,
                    self.baudrate,
                    timeout=1,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                )
               # print(f"SerialReaderThread: Successfully opened port {self.port}")
                while self.running:
                    if self.serial_port.in_waiting > 0:
                        vin = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                        if vin:
                            #print(f"SerialReaderThread: Scanned VIN: {vin}")
                            self.vin_received.emit(vin)
                            break
                    self.msleep(100)
                break
            except serial.SerialException as e:
                retry_count += 1
                error_msg = f"Failed to open port {self.port} on attempt {retry_count}: {str(e)}"
               # print(error_msg)
                self.error_occurred.emit(error_msg)
                if retry_count < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    self.error_occurred.emit(f"Serial port {self.port} failed after {self.max_retries} attempts")
            except Exception as e:
                retry_count += 1
                error_msg = f"Unexpected error reading from port {self.port}: {str(e)}"
               # print(error_msg)
                self.error_occurred.emit(error_msg)
                if retry_count < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    self.error_occurred.emit(f"Serial port {self.port} failed after {self.max_retries} attempts")
            finally:
                if self.serial_port and self.serial_port.is_open:
                   # print(f"SerialReaderThread: Closing port {self.port}")
                    self.serial_port.close()
                    self.serial_port = None

    def stop(self):
        self.running = False
        if self.serial_port and self.serial_port.is_open:
           # print(f"SerialReaderThread: Stopping and closing port {self.port}")
            self.serial_port.close()
            self.serial_port = None
        self.quit()
        self.wait()

class TestRow(QWidget):
    def __init__(self, test_data, active_library):
        super().__init__()
        layout = QHBoxLayout()
        layout.setSpacing(10)

        columns = ["S.No", "Test Sequence", "Parameter", "Value()", "LSL", "USL"] if active_library == "3W_Diagnostics" else ["S.No", "Test Sequence", "Parameter"]
        for key in columns:
            label = QLabel(str(test_data.get(key, "")))
            label.setStyleSheet("color: black;")
            label.setFont(QFont("Segoe UI", 10))
            layout.addWidget(label)

        self.actual_value_label = QLabel("Pending")
        self.result_label = QLabel("Pending")

        for widget in [self.actual_value_label, self.result_label]:
            widget.setStyleSheet("color: yellow;")
            widget.setFont(QFont("Segoe UI", 10))
            layout.addWidget(widget)

        self.setLayout(layout)
        self.setFixedHeight(40)
        self.setStyleSheet("background-color: #ffffff; border: 1px solid #444;")

    def update_result(self, actual_value, result):
        self.actual_value_label.setText(str(actual_value))
        self.result_label.setText("Pass" if result else "Fail")
        self.result_label.setStyleSheet("color: green;" if result else "color: red;")

def load_scanner_config(config_file=resource_path(r"D:\Python\TVS_NIRIX_V1.4\scanner.ini")):
    config = configparser.ConfigParser()
    config.read(config_file)
    if 'ScannerConfig' not in config:
        return 'AUTO', ['COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8'], 9600
    mode = config.get('ScannerConfig', 'connection_mode', fallback='AUTO').upper()
    ports = config.get('ScannerConfig', 'ports', fallback='COM2,COM3,COM4,COM5,COM6,COM7,COM8').split(',')
    baudrate = config.getint('ScannerConfig', 'baudrate', fallback=9600)
    return mode, ports, baudrate

def load_station_config():
    config = configparser.ConfigParser()
    config_data = {}
    try:
        ini_path = resource_path(r"D:\Python\TVS_NIRIX_V1.4\station.ini")
        if not os.path.exists(ini_path):
            raise FileNotFoundError(f"station.ini not found at {ini_path}")
        config.read(ini_path)
        if "SETTINGS" in config:
            config_data = dict(config["SETTINGS"])
        else:
            print("No [SETTINGS] section in station.ini")
    except Exception as e:
        print(f"Error reading station.ini: {e}")
    return config_data

class ApiSelector(QFrame):
    def __init__(self, api_ini_path=resource_path(r"D:\Python\TVS_NIRIX_V1.4\api.ini"), parent=None):
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
                #print(f"[ApiSelector] Error: api.ini not found at {self.api_ini_path}")
                self.parent().instruction_box.append(f"Error: api.ini not found at {self.api_ini_path}. Using default URL.")
                return default_url.rstrip("/") + f"/{vin}" if vin else default_url

            config.read(self.api_ini_path)
            if not config.sections():
                #print(f"[ApiSelector] Error: api.ini is empty or corrupted at {self.api_ini_path}")
                self.parent().instruction_box.append(f"Error: api.ini is empty or corrupted. Using default URL.")
                return default_url.rstrip("/") + f"/{vin}" if vin else default_url

            if not self.selected_api:
                #print("Selected API not set!")
                self.parent().instruction_box.append("Error: No API mode selected (PRD/EJO). Using default URL.")
                return default_url.rstrip("/") + f"/{vin}" if vin else default_url

            api_key = self.selected_api.upper()
            if "API" not in config or api_key not in config["API"]:
              #  print(f"Error: Section 'API' or key '{api_key}' not found in {self.api_ini_path}")
                self.parent().instruction_box.append(f"Error: Section 'API' or key '{api_key}' not found in api.ini. Using default URL.")
                return default_url.rstrip("/") + f"/{vin}" if vin else default_url

            base_url = config["API"][api_key]
            if not base_url:
               # print(f"Error: Empty URL for key '{api_key}' in {self.api_ini_path}")
                self.parent().instruction_box.append(f"Error: Empty URL for '{api_key}' in api.ini. Using default URL.")
                return default_url.rstrip("/") + f"/{vin}" if vin else default_url

            if vin:
                base_url = base_url.rstrip("/") + f"/{vin}"
           # print(f"Selected API URL: {base_url}")
            return base_url
        except Exception as e:
           # print(f"[ApiSelector] Error reading '{self.api_ini_path}': {e}")
            self.parent().instruction_box.append(f"Error reading api.ini: {e}. Using default URL.")
            return default_url.rstrip("/") + f"/{vin}" if vin else default_url

class EditableInfoBox(QFrame):
    def __init__(self, label_text: str):
        super().__init__()
        self.setFixedSize(350, 120)
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #444;
            }
            QLineEdit {
                background-color: #f0f0f0;
                color: black;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        label = QLabel(label_text)
        label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        label.setStyleSheet("color: black; background: transparent; border: none; font-size: 30px;")

        self.line_edit = QLineEdit()
        self.line_edit.setStyleSheet("""
            background-color: #f0f0f0;
            color: black;
            border: 1px solid #555;
            border-radius: 5px;
            padding: 4px;
            font-size: 25px;
        """)
        self.line_edit.setPlaceholderText("Enter Employee No")
        self.line_edit.setValidator(QIntValidator(0, 99999))
        layout.addWidget(label)
        layout.addWidget(self.line_edit)

    def get_text(self):
        return self.line_edit.text()

class InfoBox(QFrame):
    def __init__(self, label_text: str, value_text: str):
        super().__init__()
        self.setFixedSize(350, 120)
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #444;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        label = QLabel(label_text)
        label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        label.setStyleSheet("color: black; background: transparent; border: none; font-size: 30px;")

        value = QLabel(value_text)
        value.setFont(QFont("Segoe UI", 9))
        value.setStyleSheet("color: black; background: transparent; border: none; font-size: 30px;")

        layout.addWidget(label)
        layout.addWidget(value)

class CycleTimeBox(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedSize(400, 240)
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #444;
                font-size: 22px;
                color: black;
            }
            QLabel {
                background: transparent;
                color: black;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        self.label = QLabel("Cycle Time:")
        self.label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.label.setStyleSheet("color: black; background: transparent; border: none; font-size: 30px;")
        self.label.setAlignment(Qt.AlignLeft)

        self.timer_display = QLabel("0 sec")
        self.timer_display.setFont(QFont("Consolas", 28, QFont.Bold))
        self.timer_display.setStyleSheet("color: black; background: transparent; border: none; font-size: 45px;")
        self.timer_display.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.label)
        layout.addWidget(self.timer_display)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.seconds = 0

    def start_timer(self):
        self.seconds = 0
        self.timer_display.setText("0 sec")
        self.timer.start(1000)

    def stop_timer(self):
        self.timer.stop()

    def reset_timer(self):
        self.seconds = 0
        self.timer_display.setText("0 sec")

    def update_time(self):
        self.seconds += 1
        self.timer_display.setText(f"{self.seconds} sec")

class LabeledEntryBox(QFrame):
    def __init__(self, label_text, placeholder_text="", max_length=100):
        super().__init__()
        self.setFixedSize(700, 120)
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #444;
                font-size: 20px;
                color: black;
            }
            QLabel {
                background: transparent;
                color: black;
            }
            QLineEdit {
                font-size: 26px;
                padding: 6px;
                border: none;
                border-radius: 6px;
                background-color: #f0f0f0;
                color: black;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.label = QLabel(label_text)
        self.label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.label.setStyleSheet("color: black; background: transparent; border: none; font-size: 30px;")
        layout.addWidget(self.label)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText(placeholder_text)
        self.entry.setMaxLength(max_length)
        layout.addWidget(self.entry)

    def set_value(self, text):
        self.entry.setText(text)

    def get_value(self):
        return self.entry.text()

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
            #print(f"Active library updated to: {library}")

    def save_to_station_ini(self, library):
        config = configparser.ConfigParser()
        ini_path = resource_path(r"D:\Python\TVS_NIRIX_V1.4\station.ini")
        try:
            config.read(ini_path)
            if "SETTINGS" not in config:
                config["SETTINGS"] = {}
            config["SETTINGS"]["active_library"] = library
            with open(ini_path, 'w') as configfile:
                config.write(configfile)
           # print(f"Saved active_library '{library}' to {ini_path}")
        except Exception as e:
            print(f"Failed to save active_library to station.ini: {e}")

    def get_selected_library(self):
        return self.combo.currentText()

class MainWindow(QWidget):
    sku_fetched = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.cycle_time_box = CycleTimeBox()
        self.sku = None
        self.test_cycle_completed = False
        self.test_boxes = []
        self.sku_fetched.connect(self.on_sku_fetched)

        log_folder = resource_path(r"D:\Python\TVS_NIRIX_V1.4\test_results")
        try:
            log_cleanup_module = importlib.import_module("log_cleanup")
            log_cleanup_module.cleanup_old_logs(log_folder)
        except ImportError as e:
            print(f"Failed to import log_cleanup.py: {e}")
        except AttributeError as e:
            print(f"Failed to call cleanup_old_logs in log_cleanup.py: {e}")
        except Exception as e:
            print(f"Error executing log_cleanup.py: {e}")

        self.setWindowTitle("TVS NIRIX")
        self.setStyleSheet("background-color: white;")
        self.setWindowState(Qt.WindowMaximized)
        screen = QApplication.desktop().screenGeometry()
        self.setGeometry(0, 0, screen.width(), screen.height())
        self.setWindowFlags(self.windowFlags() & ~Qt.FramelessWindowHint)

        pc_name = socket.gethostname()
        config_data = load_station_config()
        operation_number = config_data.get("operation_no", "N/A")

        top_row = QHBoxLayout()
        top_row.setSpacing(20)
        top_row.setContentsMargins(20, 20, 20, 0)

        program_box = InfoBox("Controller", "3W_0725_V1.4")
        self.cycle_time_box = CycleTimeBox()
        pc_box = InfoBox("PC Name:", pc_name)
        op_box = InfoBox("Operation No:", operation_number)
        emp_box = EditableInfoBox("Emp No:")
        self.api_selector = ApiSelector(parent=self)

        top_row.addWidget(program_box)
        top_row.addWidget(pc_box)
        top_row.addWidget(op_box)
        top_row.addWidget(emp_box)
        top_row.addWidget(self.api_selector)
        top_row.addStretch(1)

        second_row = QHBoxLayout()
        second_row.setContentsMargins(20, 10, 20, 20)

        self.vin_box = LabeledEntryBox("Identifier Number:", "Eg: MD612345678912345", max_length=17)
        self.vin_input = self.vin_box.entry
        self.vin_input.installEventFilter(self)
        self.vin_input.returnPressed.connect(self.start_test_cases)

        self.second_sub_box = LabeledEntryBox("Part Number:", "SKU", max_length=10)

        side_vbox = QVBoxLayout()
        side_vbox.addWidget(self.vin_box)
        side_vbox.addWidget(self.second_sub_box)
        side_vbox.addStretch()

        station_config = load_station_config()
        active_library_default = station_config.get("active_library", "3W_Diagnostics")
        available_libraries = ["3W_Diagnostics", "TPMS", "IVCU"]

        self.active_library_selector = ActiveLibrarySelector(available_libraries, active_library_default)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                color: black;
                border: 1px solid #444;
                border-radius: 15px;
                text-align: center;
                height: 30px;
                font-size: 40px;
                width: 100%;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 15px;
            }
        """)

        side_active_process_bar_box = QVBoxLayout()
        side_active_process_bar_box.addWidget(self.active_library_selector)
        side_active_process_bar_box.addSpacing(40)
        side_active_process_bar_box.addWidget(self.progress_bar)
        side_active_process_bar_box.addStretch()

        second_row.addWidget(self.cycle_time_box)
        second_row.addLayout(side_vbox)
        second_row.addLayout(side_active_process_bar_box)
        second_row.addStretch()

        third_row = QHBoxLayout()
        third_row.setContentsMargins(20, 0, 20, 20)

        self.test_table = QTableWidget()
        self.test_table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                color: black;
                font-weight: bold;
                font-size: 25px;
                font-family: 'Segoe UI', sans-serif;
                border: 1px solid #444;
                border-radius: 12px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                color: black;
                font-weight: bold;
                font-size: 25px;
                padding: 6px;
                border: 1px solid #444;
            }
            QTableWidget::item {
                padding: 10px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #0078d7;
                color: black;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                border: 1px solid #444;
                background: #f0f0f0;
                margin: 0px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #d3d3d3;
                border: 1px solid #333;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: #f0f0f0;
                border: 1px solid #444;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: #d0d0d0;
            }
        """)
        self.test_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.test_table.verticalHeader().setVisible(False)
        self.test_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.test_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.test_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.test_table.setMinimumHeight(400)
        self.test_table.setMaximumHeight(800)

        instruction_label = QLabel("Instructions:")
        instruction_label.setStyleSheet("color: black; font-size: 25px; font-weight: bold; margin-bottom: 5px;")

        self.instruction_box = QTextEdit()
        self.instruction_box.setReadOnly(True)
        self.instruction_box.setPlaceholderText("Instructions will appear here...")
        self.instruction_box.setStyleSheet("""
            QTextEdit {
                background-color: #f0f0f0;
                color: black;
                font-size: 20px;
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        self.instruction_box.setMinimumWidth(300)

        result_label = QLabel("Result:")
        result_label.setStyleSheet("color: black; font-size: 25px; font-weight: bold; margin-bottom: 5px;")

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setPlaceholderText("Result will appear here...")
        self.result_box.setStyleSheet("""
            QTextEdit {
                background-color: #f0f0f0;
                color: black;
                font-size: 20px;
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        self.result_box.setMinimumWidth(300)

        instruction_result_layout = QVBoxLayout()
        instruction_result_layout.addWidget(instruction_label)
        instruction_result_layout.addWidget(self.instruction_box, stretch=1)
        instruction_result_layout.addWidget(result_label)
        instruction_result_layout.addWidget(self.result_box, stretch=1)
        instruction_result_layout.addStretch()

        third_row.addWidget(self.test_table, stretch=2)
        third_row.addSpacing(20)
        third_row.addLayout(instruction_result_layout, stretch=1)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_row)
        main_layout.addLayout(second_row)
        main_layout.addLayout(third_row, stretch=1)
        self.setLayout(main_layout)
        self.load_tests_from_sku("GE190510", self.active_library_selector.get_selected_library())

        self.scanner_signals = ScannerSignalEmitter()
        self.scanner_signals.vin_scanned.connect(self.handle_scanned_vin)

        connection_mode, ports, baudrate = load_scanner_config()
        self.connection_mode = connection_mode
        self.ports = ports
        self.baudrate = baudrate
        self.serial_reader_thread = None
        self.hid_thread = None
        self.scanner_mode = None
        self.detect_scanner_mode()
        self.prepare_for_next_cycle()

    def detect_scanner_mode(self):
        ports = serial.tools.list_ports.comports()
        available_ports = [p.device for p in ports]
     #   print(f"Available COM ports: {available_ports}")
        if any(port in available_ports for port in self.ports):
            self.scanner_mode = "CDC"
            print(f"Scanner detected in CDC mode on ports: {available_ports}")
            return
        devices = usb.core.find(find_all=True)
        for dev in devices:
            if dev.bDeviceClass == 3:
                self.scanner_mode = "HID"
                print("Scanner detected in HID mode")
                return
        print("No scanner detected in CDC or HID mode")
        self.scanner_mode = None

    def start_com_scanner(self):
        ports = serial.tools.list_ports.comports()
        available_ports = [p.device for p in ports]
        #print(f"Checking ports: {self.ports}, Available: {available_ports}")

        usb_serial_ports = []
        for port in ports:
            if port.device in self.ports and ("USB" in port.description or "CDC" in port.description):
                usb_serial_ports.append(port.device)

        if not usb_serial_ports:
           # print("No USB serial ports available")
            return

        max_retries = 3
        scanner_started = False

        for port in usb_serial_ports:
            for attempt in range(max_retries):
                try:
                    if self.serial_reader_thread:
                        #print(f"Stopping previous serial reader thread before trying {port}")
                        self.serial_reader_thread.stop()
                        self.serial_reader_thread.wait()

                    self.serial_reader_thread = SerialReaderThread(port, self.baudrate)
                    self.serial_reader_thread.vin_received.connect(self.handle_scanned_vin)
                    self.serial_reader_thread.start()

                    #print(f"CDC Scanner started on port {port} (attempt {attempt + 1})")
                    scanner_started = True
                    break

                except PermissionError as pe:
                    print(f"PermissionError on {port} (attempt {attempt + 1}): {pe}")
                except Exception as e:
                    print(f"Attempt {attempt + 1}/{max_retries} on {port} failed: {e}")

                time.sleep(1)

            if scanner_started:
                break

        if not scanner_started:
            print("All attempts failed on all USB serial ports.")

    def start_hid_scanner(self):
        def read_hid_input():
            try:
                vin = ""
                while True:
                    char = sys.stdin.read(1)
                    if char == '\r' or char == '\n':
                        if vin:
                           # print(f"HID Scanner: Scanned VIN: {vin}")
                            self.scanner_signals.vin_scanned.emit(vin)
                            break
                    elif char == '\b':
                        vin = vin[:-1]
                    elif char.isalnum():
                        vin += char
            except Exception as e:
                print(f"HID Scanner error: {e}")

        self.hid_thread = threading.Thread(target=read_hid_input, daemon=True)
        self.hid_thread.start()
        print("Started HID scanner")

    def handle_scanned_vin(self, vin):
        #print(f"handle_scanned_vin: Received VIN: {vin}")
        self.vin_input.setText(vin)
        self.vin_input.repaint()
        self.start_test_cases()
        if self.serial_reader_thread:
            #print("handle_scanned_vin: Stopping serial reader thread")
            self.serial_reader_thread.stop()
            self.serial_reader_thread = None
        if self.hid_thread:
            #print("handle_scanned_vin: Stopping HID reader thread")
            self.hid_thread = None

    def eventFilter(self, source, event):
        if source == self.vin_input and event.type() == event.FocusIn:
            self.detect_scanner_mode()
            if self.scanner_mode == "CDC":
                if self.serial_reader_thread:
                    #print("eventFilter: Stopping existing serial reader thread")
                    self.serial_reader_thread.stop()
                self.start_com_scanner()
            elif self.scanner_mode == "HID":
                if self.hid_thread:
                    #print("eventFilter: Stopping existing HID reader thread")
                    self.hid_thread = None
                self.start_hid_scanner()
        return super().eventFilter(source, event)

    def prepare_for_next_cycle(self):
        self.vin_input.clear()
        self.vin_input.setFocus()
        self.detect_scanner_mode()
        if self.scanner_mode == "CDC":
            self.start_com_scanner()
        elif self.scanner_mode == "HID":
            self.start_hid_scanner()
        else:
            print("No Scanner Detected")

    def reset_for_next_cycle(self):
        print("Resetting for next cycle...")
        self.current_test_index = 0
        self.test_results = []
        self.test_times = []
        self.final_status = "OK"
        self.vin_input.setText("")
        self.progress_bar.setValue(0)
        self.vin_input.clearFocus()
        self.vin_input.setFocus()
        self.second_sub_box.entry.setText("")
        self.instruction_box.clear()
        self.instruction_box.append("Scan VIN to start next test cycle...")
        self.result_box.clear()
        self.start_time = None
        self.cycle_time_box.stop_timer()
        self.cycle_time_box.reset_timer()
        for row in range(self.test_table.rowCount()):
            for col in range(self.test_table.columnCount()):
                item = self.test_table.item(row, col)
                if item:
                    item.setBackground(QColor("#ffffff"))
                    item.setForeground(QColor("black"))
        for row in range(self.test_table.rowCount()):
            self.test_table.setItem(row, self.test_table.columnCount() - 2, QTableWidgetItem(""))
            self.test_table.setItem(row, self.test_table.columnCount() - 1, QTableWidgetItem(""))
        self.test_cases = []
        self.current_test_index = 0
        self.sku = None
        self.json_response = None
        self.test_failed = False
        self.test_table.verticalScrollBar().setValue(0)
        importlib.invalidate_caches()
        active_library = self.active_library_selector.get_selected_library()
        for module_name in list(sys.modules.keys()):
            if module_name.startswith(active_library):
                del sys.modules[module_name]
                #print(f"Cleared module: {module_name}")
        if self.serial_reader_thread:
            print("reset_for_next_cycle: Stopping serial reader thread")
            self.serial_reader_thread.stop()
            self.serial_reader_thread = None
        if self.hid_thread:
            print("reset_for_next_cycle: Stopping HID reader thread")
            self.hid_thread = None
        try:
            import can
            can.rc['interface'] = 'pcan'
            can.rc['channel'] = 'PCAN_USBBUS1'
            bus = can.interface.Bus()
            bus.shutdown()
            print("CAN bus successfully shut down")
        except Exception as e:
            print(f"Failed to shut down CAN bus: {e}")
        self.prepare_for_next_cycle()

    def update_test_result_row(self, row_index, actual_value, result):
        active_library = self.active_library_selector.get_selected_library()
        actual_value_col = 6 if active_library == "3W_Diagnostics" else 3
        result_col = 7 if active_library == "3W_Diagnostics" else 4

        self.test_table.setItem(row_index, actual_value_col, QTableWidgetItem(str(actual_value)))
        result_item = QTableWidgetItem(str(result).upper())
        if str(result).upper() == "PASS":
            result_item.setForeground(QColor(0, 128, 0))
        elif str(result).upper() == "FAIL":
            result_item.setForeground(QColor(255, 0, 0))
        else:
            result_item.setForeground(QColor(0, 0, 0))
        result_item.setData(Qt.TextColorRole, result_item.foreground())
        self.test_table.setItem(row_index, result_col, result_item)

    def on_sku_changed(self, new_sku):
        active_library = self.active_library_selector.get_selected_library()
        self.load_tests_from_sku(new_sku, active_library)

    def load_tests_from_sku(self, sku_number, active_library):
        #print(f"Loading tests for SKU: {sku_number}, Library: {active_library}")
        test_file_name = f"{sku_number} - details.xlsx"
        full_path = resource_path(os.path.join("sku_files", test_file_name))

        if not os.path.isfile(full_path):
           # print(f"[ERROR] Test file not found: {full_path}")
            self.instruction_box.append(f"Test file for SKU '{sku_number}' not found.")
            self.test_table.setRowCount(0)
            return

        try:
            df = pd.read_excel(full_path, engine="openpyxl", keep_default_na=False)
        except Exception as e:
            #print(f"Failed to read test file: {e}")
            self.instruction_box.append(f"Failed to read test file: {e}")
            self.test_table.setRowCount(0)
            return

        self.test_table.setRowCount(0)

        if active_library == "3W_Diagnostics":
            self.test_table.setColumnCount(8)
            self.test_table.setHorizontalHeaderLabels([
                "S.No", "Test Sequence", "Parameter", "Value", "LSL", "USL", "Actual Value", "Result"
            ])
            self.test_table.setColumnWidth(0, 60)
            self.test_table.setColumnWidth(1, 250)
            self.test_table.setColumnWidth(2, 150)
            self.test_table.setColumnWidth(3, 150)
            self.test_table.setColumnWidth(4, 100)
            self.test_table.setColumnWidth(5, 100)
            self.test_table.setColumnWidth(6, 200)
            self.test_table.setColumnWidth(7, 200)
        else:  # TPMS
            self.test_table.setColumnCount(5)
            self.test_table.setHorizontalHeaderLabels([
                "S.No", "Test Sequence", "Parameter", "Actual Value", "Result"
            ])
            self.test_table.setColumnWidth(0, 60)
            self.test_table.setColumnWidth(1, 400)
            self.test_table.setColumnWidth(2, 250)
            self.test_table.setColumnWidth(3, 250)
            self.test_table.setColumnWidth(4, 200)

        for idx, row in df.iterrows():
            self.test_table.insertRow(idx)
            columns = ["S.No", "Test Sequence", "Parameter", "Value", "LSL", "USL"] if active_library == "3W_Diagnostics" else ["S.No", "Test Sequence", "Parameter"]
            for col_idx, key in enumerate(columns):
                self.test_table.setItem(idx, col_idx, QTableWidgetItem(str(row.get(key, ''))))

    def fetch_sku_from_api(self, vin, base_url):
        def api_task():
            url = base_url
            max_attempts = 3
            default_sku = "GE190510"
            selected_mode = self.api_selector.get_selected_api()
            mode_display = "Production (PRD)" if selected_mode == "PRD" else "Engineering Job Order (EJO)"
            active_library = self.active_library_selector.get_selected_library()
            for attempt in range(1, max_attempts + 1):
                try:
                    #print(f"Attempt {attempt}: Sending API request to {url}")
                    response = requests.get(url, timeout=5)
                    #print(f"API returned status code {response.status_code}")
                    if response.status_code == 200:
                        json_data = response.json()
                        self.json_response = json_data
                        modules = json_data.get("data", {}).get("modules", [])
                        sku_found = False
                        for module in modules:
                            configs = module.get("configs", [])
                            for config in configs:
                                if config.get("refname") == "VCU_SKU_WRITE":
                                    messages = config.get("messages", [])
                                    for msg in messages:
                                        if msg.get("refname") == "SKU_WRITE":
                                            sku = msg.get("txbytes")
                                            if sku:
                                               # print(f"[SKU fetched: {sku}]")
                                                # Validate SKU library against active library
                                                file_name, sku_library = get_file_name_from_sku(sku, active_library)
                                                if sku_library and sku_library != active_library:
                                                   # print(f"VIN {vin} SKU {sku} belongs to library {sku_library}, but active library is {active_library}")
                                                    self.instruction_box.append(
                                                        f'<span style="color:red;">Scanned VIN number is not in Selected Active Library ({active_library}).</span>'
                                                    )
                                                    self.vin_input.setText("")
                                                    self.vin_input.setFocus()
                                                    self.cycle_time_box.stop_timer()
                                                    self.cycle_time_box.reset_timer()
                                                    return
                                                if file_name:
                                                    self.sku = sku
                                                    self.sku_fetched.emit(sku)
                                                    return
                                                else:
                                                    #print(f"No valid file for SKU {sku} in any library")
                                                    self.instruction_box.append(
                                                        f'<span style="color:red;">No valid test file for SKU {sku}.</span>'
                                                    )
                                                    self.vin_input.setText("")
                                                    self.vin_input.setFocus()
                                                    self.cycle_time_box.stop_timer()
                                                    self.cycle_time_box.reset_timer()
                                                    return
                                            sku_found = True
                        if not sku_found:
                           # print(f"Scanned VIN number {vin} does not belong to the selected API mode: {mode_display}")
                            self.instruction_box.append(
                                f'<span style="color:red;">Scanned VIN number is not in Selected API Mode: ({mode_display}).</span>'
                            )
                            self.vin_input.setText("")
                            self.vin_input.setFocus()
                            self.cycle_time_box.stop_timer()
                            self.cycle_time_box.reset_timer()
                            return
                    elif response.status_code == 404:
                       # print(f"Scanned VIN number {vin} does not belong to the selected API mode: {mode_display}")
                        self.instruction_box.append(
                                f'<span style="color:red;">Scanned VIN number is not in Selected API Mode: ({mode_display}).</span>'
                        )
                        self.vin_input.setText("")
                        self.vin_input.setFocus()
                        self.cycle_time_box.stop_timer()
                        self.cycle_time_box.reset_timer()
                        return
                    else:
                        #print(f"API returned unexpected status: {response.status_code}")
                        self.instruction_box.append(f"API returned unexpected status: {response.status_code}")
                except requests.RequestException as e:
                   # print(f"API attempt {attempt} failed: {e}")
                    self.instruction_box.append(f"API attempt {attempt} failed: {e}")
                time.sleep(1)
           # print(f"API call failed after {max_attempts} attempts. Using default SKU: {default_sku}")
            self.instruction_box.append(f"API call failed after {max_attempts} attempts. Using default SKU: {default_sku}")
            file_name, sku_library = get_file_name_from_sku(default_sku, active_library)
            if sku_library and sku_library != active_library:
               # print(f"Default SKU {default_sku} belongs to library {sku_library}, but active library is {active_library}")
                self.instruction_box.append(
                    f'<span style="color:red;">Vin number is not the selected active library ({active_library}).</span>'
                )
                self.vin_input.setText("")
                self.vin_input.setFocus()
                self.cycle_time_box.stop_timer()
                self.cycle_time_box.reset_timer()
                return
            self.json_response = None
            self.sku = default_sku
            self.sku_fetched.emit(default_sku)
        threading.Thread(target=api_task, daemon=True).start()

    def parse_test_file(self, file_path):
        try:
            df = pd.read_excel(file_path, engine="openpyxl", keep_default_na=False)
            if "Test Sequence" not in df.columns:
                self.instruction_box.append("No test sequence")
                #print("[ERROR] 'Test Sequence' column missing in Excel.")
                return []
            test_cases = []
            for test_name in df["Test Sequence"].dropna():
                clean_name = str(test_name).strip().replace(" ", "_")
                test_cases.append((clean_name, clean_name))
            return test_cases
        except Exception as e:
            #print(f"[ERROR] Failed to parse test file '{file_path}': {e}")
            return []

    def on_sku_fetched(self, sku):
        active_library = self.active_library_selector.get_selected_library()
        self.second_sub_box.set_value(sku)
        self.on_sku_changed(sku)
        self.mac_ids = {}
        print(f"[DEBUG] SKU fetched: {sku} | Library: {active_library}")
        self.sku = sku
        test_file = resource_path(os.path.join("sku_files", f"{sku} - details.xlsx"))
        print(f"Test file path: {test_file}")
        if not os.path.exists(test_file):
            self.instruction_box.append(f"Test file for SKU '{sku}' not found.")
            self.cycle_time_box.stop_timer()
            self.cycle_time_box.reset_timer()
            return
        self.test_file_path = test_file
        if not active_library:
            self.instruction_box.append("Missing 'active_library' in station.ini")
            self.cycle_time_box.stop_timer()
            self.cycle_time_box.reset_timer()
            return
        self.active_library = active_library
        self.active_library_path = resource_path(active_library)
        if not os.path.isdir(self.active_library_path):
            self.instruction_box.append(f"Active library folder '{active_library}' not found.")
            self.cycle_time_box.stop_timer()
            self.cycle_time_box.reset_timer()
            return
        self.test_cases = self.parse_test_file(self.test_file_path)
        if not self.test_cases:
            self.instruction_box.append("No test cases found in the test file.")
            self.cycle_time_box.stop_timer()
            self.cycle_time_box.reset_timer()
            return
        self.current_test_index = 0
        self.test_results = []
        self.test_times = []
        self.cumulative_time = 0.0
        self.start_time = time.time()
        self.final_status = "OK"
        self.run_next_test()

    def start_test_cases(self):
        vin_number = self.vin_input.text().strip()
        self.instruction_box.setText('')
        if not (vin_number.startswith("MD6") and len(vin_number) == 17):
            self.instruction_box.append("Invalid VIN number. Please scan a valid VIN.")
            self.vin_input.setText("")
            self.cycle_time_box.stop_timer()
            self.cycle_time_box.reset_timer()
            return
        api_url = self.api_selector.get_selected_api_url(vin_number)
        self.url = api_url
        self.cycle_start_time = datetime.now()
        self.cycle_time_box.start_timer()
        self.fetch_sku_from_api(vin_number, api_url)

    def run_test(self, library_name, function_name, vin_number, api_url):
        log_capture = io.StringIO()
        sys.stdout = log_capture
        sys.stderr = log_capture
        output = None
        try:
            module_name = f"{library_name}.{function_name}"
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)
            test_function = getattr(sys.modules[module_name], function_name)
            if library_name == "TPMS":
                if function_name == "API_CALL":
                    output = test_function(vin_number, api_url)
                    if isinstance(output, tuple) and len(output) >= 3 and output[0]:
                        self.mac_ids['Front_Mac_ID'] = output[1]
                        self.mac_ids['Rear_Mac_ID'] = output[2]
                elif function_name == "WRITE_TPMS_FRONT":
                    output = test_function(self.mac_ids.get('Front_Mac_ID'))
                elif function_name == "WRITE_TPMS_REAR":
                    output = test_function(self.mac_ids.get('Rear_Mac_ID'))
                else:
                    output = test_function()
            else:
                if function_name in ["MCU_Phase_Offset", "MCU_Vehicle_ID", "API_CALL"]:
                    output = test_function(vin_number, api_url)
                else:
                    output = test_function()
        except Exception as e:
            print(f"Error in {library_name}.{function_name}: {e}")
            output = False
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            log_output = log_capture.getvalue()
            log_capture.close()
        self.test_results.append(log_output.strip())
        return output

    def run_next_test(self):
        if self.current_test_index < len(self.test_cases):
            test_label, function_name = self.test_cases[self.current_test_index]
            row = self.current_test_index
            max_retries = 3
            retry_count = 0
            timeout_seconds = 5
            global_retry_count = 0
            max_global_retries = 3

            while global_retry_count < max_global_retries:
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        self.instruction_box.clear()
                        self.instruction_box.append(f"Running {function_name}...")
                        active_library = self.active_library_selector.get_selected_library()
                        vin_number = self.vin_input.text().strip()
                        api_url = self.url

                        start_time = time.time()
                        result = self.run_test(active_library, function_name, vin_number, api_url)
                        test_duration = time.time() - start_time

                        if test_duration > timeout_seconds:
                            raise TimeoutError(f"Test {function_name} exceeded {timeout_seconds} seconds")

                        self.cumulative_time += test_duration
                        self.test_times.append((function_name, self.cumulative_time))

                        test_name = self.test_table.item(row, 1).text()
                        passed = False
                        actual_value = ""

                        if active_library == "3W_Diagnostics":
                            expected_value = self.test_table.item(row, 3).text() if self.test_table.item(row, 3) else ""
                            lsl = self.test_table.item(row, 4).text() if self.test_table.item(row, 4) else ""
                            usl = self.test_table.item(row, 5).text() if self.test_table.item(row, 5) else ""

                            if test_name in ["Battery_Version", "MCU_Version", "VCU_Version", "Cluster_Version", "Telematics_Version"]:
                                if isinstance(result, tuple) and len(result) == 2:
                                    success, version = result
                                    actual_value = version
                                    passed = success and (version == expected_value)
                                else:
                                    actual_value = "Error"
                                    passed = False
                            elif test_name in ["Battery_SOC", "Battery_Voltage"]:
                                if isinstance(result, tuple) and len(result) == 2:
                                    passed, actual_value = result
                                    try:
                                        actual_value_float = float(actual_value)
                                        lsl_float = float(lsl) if lsl and lsl != "N/A" else float('-inf')
                                        usl_float = float(usl) if usl and usl != "N/A" else float('inf')
                                        passed = passed and (lsl_float <= actual_value_float <= usl_float)
                                        if not passed and test_name == "Battery_SOC":
                                            self.instruction_box.clear()
                                            self.instruction_box.append(
                                                f"Battery_SOC failed: Actual value {actual_value} is outside limits (LSL: {lsl}, USL: {usl})"
                                            )
                                    except ValueError:
                                        actual_value = "Error"
                                        passed = False
                                        if test_name == "Battery_SOC":
                                            self.instruction_box.clear()
                                            self.instruction_box.append(
                                                f"Battery_SOC failed: Invalid value format (Actual: {actual_value}, LSL: {lsl}, USL: {usl})"
                                            )
                                else:
                                    actual_value = "Error"
                                    passed = False
                                    if test_name == "Battery_SOC":
                                        self.instruction_box.clear()
                                        self.instruction_box.append(f"Battery_SOC failed: Invalid result format")
                            elif test_name in ["MCU_Vehicle_ID", "MCU_Phase_Offset"]:
                                if isinstance(result, tuple) and len(result) == 3:
                                    passed, api_value, actual_value = result
                                    new_expected_value = str(api_value)
                                    self.test_table.setItem(row, 3, QTableWidgetItem(new_expected_value))
                                else:
                                    actual_value = "Error"
                                    passed = False
                            elif isinstance(result, bool):
                                actual_value = "True" if result else "False"
                                passed = result
                            elif isinstance(result, tuple):
                                success = result[0]
                                actual_value = str(result[1]) if len(result) > 1 else ""
                                passed = success and actual_value == expected_value
                            else:
                                actual_value = str(result)
                                passed = bool(result)
                        else:#TPMS
                            if test_name == "API_CALL":
                                if isinstance(result, tuple) and len(result) >= 3:
                                    passed, front_mac, rear_mac = result[:3]
                                    actual_value = f"TRUE"
                                else:
                                    actual_value = "Error"
                                    passed = False
                            elif test_name == "WRITE_TPMS_FRONT":
                                actual_value = self.mac_ids.get('Front_Mac_ID', 'N/A')
                                passed = bool(result)
                            elif test_name == "WRITE_TPMS_REAR":
                                actual_value = self.mac_ids.get('Rear_Mac_ID', 'N/A')
                                passed = bool(result)
                            else:
                                if isinstance(result, tuple) and len(result) == 2:
                                    passed, actual_value = result
                                elif isinstance(result, bool):
                                    actual_value = "True" if result else "False"
                                    passed = result
                                else:
                                    actual_value = str(result)
                                    passed = bool(result)

                        status = "PASSED" if passed else "FAILED"
                        color = "#008000" if passed else "red"
                        #print(f"[DEBUG] {test_name} result: {status}, Actual: {actual_value}")

                        self.update_test_result_row(row, actual_value, status)
                        self.test_table.scrollToItem(self.test_table.item(row, 0), QAbstractItemView.PositionAtCenter)
                        progress_percent = int(((self.current_test_index + 1) / len(self.test_cases)) * 100)
                        self.progress_bar.setValue(progress_percent)

                        self.result_box.setText(
                            f'<span style="color:{color}; font-weight:bold; font-size:24px;">{function_name} - {status}</span>')

                        self.instruction_box.clear()
                        if passed:
                            self.instruction_box.append(f"{function_name} passed on attempt {retry_count + 1}")
                            break
                        else:
                            if test_name != "Battery_SOC":
                                self.instruction_box.append(f"{function_name} failed on attempt {retry_count + 1}")
                            retry_count += 1
                            if retry_count < max_retries:
                                time.sleep(2)
                                continue
                            self.test_failed = True
                            self.final_status = "NOK"
                            self.progress_bar.setValue(100)
                            self.instruction_box.clear()
                            self.instruction_box.append(f"{function_name} failed after {max_retries} attempts. Process stopped.")
                            self.test_cycle_completed = True
                            print("Stopping cycle timer due to test failure")
                            self.cycle_time_box.stop_timer()
                            QTimer.singleShot(500, self.save_results_to_log)
                            self.send_api_status()
                            QTimer.singleShot(15000, lambda: self.reset_for_next_cycle())
                            return

                    except (Exception, TimeoutError) as e:
                        retry_count += 1
                        test_duration = time.time() - start_time
                        self.cumulative_time += test_duration
                        self.test_times.append((function_name, self.cumulative_time))
                        self.instruction_box.clear()
                        self.instruction_box.append(f"{function_name} failed on attempt {retry_count} due to: {e}")
                        print(f"Test {function_name} failed (Attempt {retry_count}/{max_retries}): {e}")
                        if retry_count < max_retries:
                            time.sleep(2)
                            continue
                        self.test_failed = True
                        self.final_status = "NOK"
                        self.update_test_result_row(row, "Timeout/Error", "FAILED")
                        self.progress_bar.setValue(100)
                        self.instruction_box.clear()
                        self.instruction_box.append(f"{function_name} failed after {max_retries} retries. Process stopped.")
                        self.test_cycle_completed = True
                        self.cycle_time_box.stop_timer()
                        QTimer.singleShot(500, self.save_results_to_log)
                        self.send_api_status()
                        QTimer.singleShot(15000, lambda: self.reset_for_next_cycle())
                        return

                if not passed and active_library == "TPMS":
                    global_retry_count += 1
                    if global_retry_count < max_global_retries:
                       # print(f"Global retry {global_retry_count + 1}/{max_global_retries} for TPMS test sequence")
                        self.current_test_index = 0
                        self.test_results = []
                        self.test_times = []
                        self.cumulative_time = 0.0
                        self.test_failed = False
                        self.final_status = "OK"
                        self.test_table.setRowCount(0)
                        self.load_tests_from_sku(self.sku, active_library)
                        continue
                    else:
                        print("Max global retries reached for TPMS test sequence")
                        break

                break

            QTimer.singleShot(1000, lambda: self._proceed_to_next_test())
        else:
            self.progress_bar.setValue(100)
            QTimer.singleShot(1000, lambda: print("1 second passed"))
            self.test_cycle_completed = True
            print("Stopping cycle timer due to all tests completed")
            self.cycle_time_box.stop_timer()
            self.result_box.setText(
                '<span style="color:green; font-weight:bold; font-size:24px;">All tests passed successfully!</span>'
            )
            self.instruction_box.clear()
            self.instruction_box.setText("System ready for next VIN number.")
            QTimer.singleShot(500, self.save_results_to_log)
            self.send_api_status()
            QTimer.singleShot(10000, lambda: self.reset_for_next_cycle())

    def _proceed_to_next_test(self):
        try:
            if hasattr(self, 'test_failed') and self.test_failed:
                return
            self.current_test_index += 1
            self.run_next_test()
        except Exception as e:
           # print(f"[Error] Proceed to next test failed: {e}")
            self.instruction_box.append(f'<span style="color:red;">Exception in _proceed_to_next_test: {e}</span>')

    def send_api_status(self):
        vin_number = self.vin_input.text().strip()
        active_library = self.active_library_selector.get_selected_library()
        self.API_URL = "http://10.121.2.107:3000/vehicles/processParams/updateProcessParams"

        if not vin_number:
            #print("VIN number is empty. Cannot send API status.")
            return

        headers = {'Content-Type': 'application/json'}
        payload = {
            "VIN": vin_number,
            "paramId": "CZ14106" if active_library == "3W_Diagnostics" else "CZ14104",
            "opnNo": "0024" if active_library == "3W_Diagnostics" else "0022",
            "identifier": vin_number,
            "result": self.final_status
        }

        try:
            print("Sending final result to API...")
            print("Request URL:", self.API_URL)
            print("Payload:", json.dumps(payload, indent=4))
            response = requests.post(self.API_URL, headers=headers, data=json.dumps(payload))
            print(f"API Response [{response.status_code}]: {response.text}")
        except Exception as e:
            print(f"Failed to send final result to API: {e}")

    def save_results_to_log(self):
        vin_number = self.vin_input.text().strip()
        timestamp_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_cycle_time = getattr(self, 'cycle_start_time', 'N/A').strftime("%Y-%m-%d %H:%M:%S") if hasattr(self, 'cycle_start_time') else 'N/A'
        total_cycle_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        url = getattr(self, 'url', 'No request sent')
        json_response = getattr(self, 'json_response', 'No response available')

        log_folder = r"D:\Python\TVS_NIRIX_V1.4\test_results"
        os.makedirs(log_folder, exist_ok=True)

        txt_filename = f"{vin_number}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.txt"
        txt_path = os.path.join(log_folder, txt_filename)

        try:
            with open(txt_path, 'a', encoding='utf-8') as file:
                file.write(f"VIN NUMBER      : {vin_number}\n")
                file.write(f"TEST STATUS     : {self.final_status}\n")
                file.write(f"DATE            : {timestamp_now}\n")
                file.write("API Request:\n")
                file.write(f"{url}\n")
                file.write("API Response:\n")
                file.write('\n')
                if isinstance(json_response, dict):
                    file.write(json.dumps(json_response, indent=4))
                else:
                    file.write(str(json_response))
                for idx, raw_log in enumerate(self.test_results):
                    for line in raw_log.strip().split('\n'):
                        file.write(f"{line}\n")
                    file.write(f"Cycle Time: {self.test_times[idx][1]:.2f} sec\n")
                    file.write('\n')
                file.write(f"START CYCLE TIME: {start_cycle_time}\n")
                file.write(f"TOTAL CYCLE TIME: {total_cycle_time}\n")
            print(f"Results appended to: {txt_path}")
        except Exception as e:
            print(f"Error saving log file: {e}")
            self.instruction_box.append(str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    light_palette = QPalette()
    light_palette.setColor(QPalette.Window, QColor(255, 255, 255))
    light_palette.setColor(QPalette.WindowText, Qt.black)
    light_palette.setColor(QPalette.Base, QColor(240, 240, 240))
    light_palette.setColor(QPalette.AlternateBase, QColor(230, 230, 230))
    light_palette.setColor(QPalette.ToolTipBase, Qt.black)
    light_palette.setColor(QPalette.ToolTipText, Qt.black)
    light_palette.setColor(QPalette.Text, Qt.black)
    light_palette.setColor(QPalette.Button, QColor(230, 230, 230))
    light_palette.setColor(QPalette.ButtonText, Qt.black)
    light_palette.setColor(QPalette.BrightText, Qt.red)
    light_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    light_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(light_palette)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())