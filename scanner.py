import serial
import serial.tools.list_ports
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import usb.core
import usb.util
import sys
import time
import threading
import configparser

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
                self.serial_port = serial.Serial(
                    self.port,
                    self.baudrate,
                    timeout=1,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                )
                while self.running:
                    if self.serial_port.in_waiting > 0:
                        vin = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                        if vin:
                            self.vin_received.emit(vin)
                            break
                    self.msleep(100)
                break
            except serial.SerialException as e:
                retry_count += 1
                self.error_occurred.emit(f"Failed to open port {self.port} on attempt {retry_count}: {str(e)}")
                if retry_count < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    self.error_occurred.emit(f"Serial port {self.port} failed after {self.max_retries} attempts")
            except Exception as e:
                retry_count += 1
                self.error_occurred.emit(f"Unexpected error reading from port {self.port}: {str(e)}")
                if retry_count < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    self.error_occurred.emit(f"Serial port {self.port} failed after {self.max_retries} attempts")
            finally:
                if self.serial_port and self.serial_port.is_open:
                    self.serial_port.close()
                    self.serial_port = None

    def stop(self):
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.serial_port = None
        self.quit()
        self.wait()

def load_scanner_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    if 'ScannerConfig' not in config:
        return 'AUTO', ['COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8'], 9600
    mode = config.get('ScannerConfig', 'connection_mode', fallback='AUTO').upper()
    ports = config.get('ScannerConfig', 'ports', fallback='COM2,COM3,COM4,COM5,COM6,COM7,COM8').split(',')
    baudrate = config.getint('ScannerConfig', 'baudrate', fallback=9600)
    return mode, ports, baudrate

def detect_scanner_mode(ports):
    ports_list = serial.tools.list_ports.comports()
    available_ports = [p.device for p in ports_list]
    if any(port in available_ports for port in ports):
        return "CDC"
    devices = usb.core.find(find_all=True)
    for dev in devices:
        if dev.bDeviceClass == 3:
            return "HID"
    return None

def start_com_scanner(ports, baudrate, scanner_signals):
    available_ports = [p.device for p in serial.tools.list_ports.comports()]
    usb_serial_ports = [port for port in ports if port in available_ports and ("USB" in port or "CDC" in port)]
    if not usb_serial_ports:
        return
    max_retries = 3
    scanner_started = False
    for port in usb_serial_ports:
        for attempt in range(max_retries):
            try:
                serial_reader = SerialReaderThread(port, baudrate)
                serial_reader.vin_received.connect(scanner_signals.vin_scanned)
                serial_reader.start()
                scanner_started = True
                break
            except Exception as e:
                time.sleep(1)
            if scanner_started:
                break

def start_hid_scanner(scanner_signals):
    def read_hid_input():
        vin = ""
        while True:
            char = sys.stdin.read(1)
            if char == '\r' or char == '\n':
                if vin:
                    scanner_signals.vin_scanned.emit(vin)
                    break
            elif char == '\b':
                vin = vin[:-1]
            elif char.isalnum():
                vin += char
    thread = threading.Thread(target=read_hid_input, daemon=True)
    thread.start()