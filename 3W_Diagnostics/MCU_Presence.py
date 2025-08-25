import can
from datetime import datetime

# MCU Presence CAN IDs (in hex)
MCU_CAN_IDS = [0xA0, 0xC8, 0x15, 0xB0, 0xAF, 0xAB, 0xB7, 0xCA, 0x668, 0xCB, 0xC7]

def setup_can_bus():
    try:
        # Try PCAN first
        bus = can.interface.Bus(interface='pcan', channel='PCAN_USBBUS1', bitrate=500000, fd=False)
        return bus
    except Exception as e:
        print(f"PCAN setup failed: {e}")
        
    try:
        # Try SocketCAN (for Linux)
        bus = can.interface.Bus(interface='socketcan', channel='can0', bitrate=500000)
        return bus
    except Exception as e:
        print(f"SocketCAN setup failed: {e}")
        
    print("No CAN interface found.")
    return None

def MCU_Presence():
    bus = setup_can_bus()
    if not bus:
        return False
    
    detected_ids = {}
    presence_detected = False

    try:
        start_time = datetime.now()

        while (datetime.now() - start_time).seconds < 1:
            msg = bus.recv(timeout=0.1)
            if msg and msg.arbitration_id in MCU_CAN_IDS:
                can_id = msg.arbitration_id
                presence_detected = True
                if can_id not in detected_ids:
                    detected_ids[can_id] = ' '.join(f"{byte:02X}" for byte in msg.data)
    except Exception as e:
        print(f"Error while reading CAN messages: {e}")
    finally:
        bus.shutdown()
        status = "Passed" if presence_detected else "Failed"
        print(f"Test Sequence: MCU_Presence")
        if presence_detected:
            for can_id, received_data in detected_ids.items():
                print(f"Tx_Can_id: {hex(can_id)}")
                print(f"Rx: {received_data}")
        else:
            print("Status: MCU not presented")
        print(f"Status: {status}")
        return presence_detected

if __name__ == "__MCU_Presence__":
    result = MCU_Presence()