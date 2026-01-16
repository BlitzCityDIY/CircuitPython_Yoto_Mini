"""
CR95HF NFC/RFID Transceiver Driver for CircuitPython
Based on CR95HF datasheet (DocID018669 Rev 12)

Supports ISO14443-A tag reading via UART interface

Hardware Requirements:
- UART: 57600 baud, 8N2 (2 stop bits critical!)
- SSI_0 and SSI_1 must be tied to GND for UART mode

Example usage:
    import board
    import busio
    import time
    from cr95hf import CR95HF
    
    uart = busio.UART(board.TX, board.RX, baudrate=57600, bits=8, stop=2)
    nfc = CR95HF(uart)
    
    if nfc.begin():
        while True:
            uid, sak = nfc.read_tag()
            if uid:
                print(f"UID: {uid.hex().upper()}")
                print(f"Type: {nfc.card_type(sak)}")
            time.sleep(0.2)
"""

import time

# Command Codes
CMD_IDN = 0x01
CMD_PROTOCOL = 0x02
CMD_SENDRECV = 0x04
CMD_ECHO = 0x55

# Response Codes
RSP_SUCCESS = 0x00
RSP_DATA = 0x80
RSP_TIMEOUT = 0x87

# Protocol Codes
PROTO_OFF = 0x00
PROTO_ISO14443A = 0x02

# ISO14443-A Commands
ISO14443A_REQA = 0x26
ISO14443A_WUPA = 0x52
ISO14443A_CT = 0x88
ISO14443A_SEL_CL1 = 0x93
ISO14443A_SEL_CL2 = 0x95
ISO14443A_NVB_ANTICOLL = 0x20
ISO14443A_NVB_SELECT = 0x70

# Transmit Flags
FLAG_SHORTFRAME = 0x07
FLAG_STD = 0x08
FLAG_STD_CRC = 0x28

# SAK Card Types
SAK_MIFARE_UL = 0x00
SAK_MIFARE_1K = 0x08
SAK_MIFARE_MINI = 0x09
SAK_MIFARE_4K = 0x18
SAK_MIFARE_PLUS_2K = 0x10
SAK_MIFARE_PLUS_4K = 0x11
SAK_MIFARE_PLUS = 0x20


class CR95HF:
    """CR95HF NFC/RFID driver for CircuitPython"""
    
    def __init__(self, uart, wake_pulse_ms=100):
        """
        Initialize CR95HF driver
        
        Args:
            uart: UART object (57600 baud, 8N2)
            wake_pulse_ms: Duration of wake-up pulse (default 100ms)
            
        Raises:
            CR95HFInitError: If initialization fails
        """
        self.uart = uart
        self._device_name = ""
        self._last_atqa = bytearray(2)
        
        # Initialize the device
        self._initialize(wake_pulse_ms)
    
    def _flush_rx(self):
        while self.uart.in_waiting:
            self.uart.read(self.uart.in_waiting)
    
    def _send_cmd(self, cmd, data=b''):
        frame = bytes([cmd, len(data)]) + data
        self._flush_rx()
        self.uart.write(frame)
    
    def _read_response(self, timeout_ms=100):
        start = time.monotonic()
        timeout_s = timeout_ms / 1000.0
        
        # Wait for result code
        while self.uart.in_waiting == 0:
            if time.monotonic() - start > timeout_s:
                raise TimeoutError("Timeout waiting for result code")
        result_code = self.uart.read(1)[0]
        
        # Wait for length
        while self.uart.in_waiting == 0:
            if time.monotonic() - start > timeout_s:
                raise TimeoutError("Timeout waiting for length byte")
        length = self.uart.read(1)[0]
        
        # Read data
        data = bytearray()
        while len(data) < length:
            available = self.uart.in_waiting
            if available > 0:
                chunk = self.uart.read(min(available, length - len(data)))
                data.extend(chunk)
            elif time.monotonic() - start > timeout_s:
                raise TimeoutError(f"Timeout reading data (got {len(data)}/{length} bytes)")
        
        return result_code, bytes(data)
    
    def echo_test(self):
        """
        Perform echo test
        
        Raises:
            CR95HFCommunicationError: If device doesn't respond correctly
        """
        self._flush_rx()
        self.uart.write(bytes([CMD_ECHO]))
        
        start = time.monotonic()
        while time.monotonic() - start < 0.1:
            if self.uart.in_waiting > 0:
                resp = self.uart.read(1)[0]
                if resp == CMD_ECHO:
                    return
                raise OSError(f"Echo test failed: expected 0x55, got 0x{resp:02X}")
        
        raise OSError("Echo test failed: no response from device")
    
    def _initialize(self, wake_pulse_ms=100):
        # Send wake-up pulses
        self._flush_rx()
        wake_bytes = bytes([0x00] * 20)
        start = time.monotonic()
        while time.monotonic() - start < wake_pulse_ms / 1000.0:
            self.uart.write(wake_bytes)
            time.sleep(0.001)
        
        # Wait for HFO stabilization
        time.sleep(0.015)
        self._flush_rx()
        
        # Echo test
        try:
            self.echo_test()
        except OSError as e:
            raise OSError(f"CR95HF initialization failed: {e}")
        
        # Get device ID
        self._send_cmd(CMD_IDN)
        try:
            code, data = self._read_response(100)
        except TimeoutError as e:
            raise OSError(f"Failed to read device ID: {e}")
        
        if code != RSP_SUCCESS or not data or len(data) < 13:
            raise OSError(f"Invalid IDN response: code=0x{code:02X}")
        
        # Extract device name
        device_bytes = data[:13]
        self._device_name = ""
        for b in device_bytes:
            if b == 0:
                break
            if 32 <= b <= 126:
                self._device_name += chr(b)
        
        # Select ISO14443-A protocol
        self._send_cmd(CMD_PROTOCOL, bytes([PROTO_ISO14443A, 0x00]))
        try:
            code, data = self._read_response(100)
        except TimeoutError as e:
            raise OSError(f"Failed to select protocol: {e}")
        
        if code != RSP_SUCCESS:
            raise OSError(f"Protocol selection failed: code=0x{code:02X}")
    
    def _sendrecv(self, rf_data, flags):
        cmd_data = rf_data + bytes([flags])
        self._send_cmd(CMD_SENDRECV, cmd_data)
        return self._read_response(50)
    
    def _reqa_wupa(self, cmd):
        code, data = self._sendrecv(bytes([cmd]), FLAG_SHORTFRAME)
        if code == RSP_DATA and data and len(data) >= 2:
            return data[0], data[1]
        return None, None
    
    def _anticoll_cl1(self):
        rf_data = bytes([ISO14443A_SEL_CL1, ISO14443A_NVB_ANTICOLL])
        code, data = self._sendrecv(rf_data, FLAG_STD)
        if code == RSP_DATA and data and len(data) >= 5:
            return data[:5]
        return None
    
    def _select_cl1(self, uid_bcc):
        rf_data = bytes([ISO14443A_SEL_CL1, ISO14443A_NVB_SELECT]) + uid_bcc
        code, data = self._sendrecv(rf_data, FLAG_STD_CRC)
        if code == RSP_DATA and data and len(data) >= 1:
            return data[0]
        return None
    
    def _anticoll_cl2(self):
        rf_data = bytes([ISO14443A_SEL_CL2, ISO14443A_NVB_ANTICOLL])
        code, data = self._sendrecv(rf_data, FLAG_STD)
        if code == RSP_DATA and data and len(data) >= 5:
            return data[:5]
        return None
    
    def _select_cl2(self, uid_bcc):
        rf_data = bytes([ISO14443A_SEL_CL2, ISO14443A_NVB_SELECT]) + uid_bcc
        code, data = self._sendrecv(rf_data, FLAG_STD_CRC)
        if code == RSP_DATA and data and len(data) >= 1:
            return data[0]
        return None
    
    def read_tag(self):
        """
        ISO14443-A tag UID
        
        Returns:
            tuple: (uid_bytes, sak_byte) or (None, None) if no tag
        """
        # Wake up tag
        atqa1, atqa2 = self._reqa_wupa(ISO14443A_WUPA)
        if atqa1 is None:
            atqa1, atqa2 = self._reqa_wupa(ISO14443A_REQA)
        
        if atqa1 is None:
            return None, None
        
        self._last_atqa[0] = atqa1
        self._last_atqa[1] = atqa2
        
        # Anticollision CL1
        cl1 = self._anticoll_cl1()
        if cl1 is None:
            return None, None
        
        # Select CL1
        sak1 = self._select_cl1(cl1)
        if sak1 is None:
            return None, None
        
        # Check for cascade tag
        if cl1[0] != ISO14443A_CT:
            # 4-byte UID
            return bytes(cl1[:4]), sak1
        
        # 7-byte UID
        uid = bytearray(cl1[1:4])
        
        # Anticollision CL2
        cl2 = self._anticoll_cl2()
        if cl2 is None:
            return None, None
        
        # Select CL2
        sak2 = self._select_cl2(cl2)
        if sak2 is None:
            return None, None
        
        uid.extend(cl2[:4])
        return bytes(uid), sak2
    
    def card_type(self, sak):
        """
        Card type from SAK byte
        
        Args:
            sak: SAK byte value
            
        Returns:
            str: Card type description
        """
        card_types = {
            SAK_MIFARE_UL: "MIFARE Ultralight/NTAG",
            SAK_MIFARE_1K: "MIFARE Classic 1K",
            SAK_MIFARE_MINI: "MIFARE Mini",
            SAK_MIFARE_4K: "MIFARE Classic 4K",
            SAK_MIFARE_PLUS_2K: "MIFARE Plus 2K",
            SAK_MIFARE_PLUS_4K: "MIFARE Plus 4K",
            SAK_MIFARE_PLUS: "MIFARE Plus/DESFire",
            0x28: "JCOP/SmartMX",
            0x38: "MIFARE Classic 4K (emu)",
            0x88: "MIFARE Classic 1K (Infineon)",
            0x98: "MIFARE ProX",
        }
        return card_types.get(sak, f"Unknown (SAK=0x{sak:02X})")
    
    def field_off(self):
        """Turn off RF field"""
        self._send_cmd(CMD_PROTOCOL, bytes([PROTO_OFF, 0x00]))
        self._read_response(50)
    
    @property
    def device_name(self):
        """Device identification string (e.g. 'NFC FS2JAST4')"""
        return self._device_name
    
    @property
    def last_atqa(self):
        """Last ATQA response (2 bytes) from tag detection"""
        return bytes(self._last_atqa)
