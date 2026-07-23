import time

import serial
from serial.tools import list_ports

import config
from logger import get_logger

log = get_logger("serial")

_ESP32_VIDS = {0x10C4, 0x1A86, 0x0403, 0x303A}


class SerialManager:
    def __init__(
        self,
        port: str = config.SERIAL_PORT,
        baudrate: int = config.SERIAL_BAUDRATE,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.conn: serial.Serial | None = None
        self._buffer = bytearray()

    def connect(self) -> bool:
        for candidate in self._candidates():
            try:
                self.conn = serial.Serial(
                    candidate, self.baudrate, timeout=config.SERIAL_TIMEOUT
                )
                time.sleep(2.0)
                self.conn.reset_input_buffer()
                self.port = candidate
                log.info("Connected to ESP32 on %s @ %d baud", candidate, self.baudrate)
                return True
            except serial.SerialException as exc:
                log.warning("Could not open %s: %s", candidate, exc)
        log.error("No ESP32 serial connection available.")
        return False

    def _candidates(self) -> list[str]:
        ports = [self.port]
        for info in list_ports.comports():
            if info.vid in _ESP32_VIDS and info.device not in ports:
                ports.append(info.device)
        return ports

    @property
    def connected(self) -> bool:
        return self.conn is not None and self.conn.is_open

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def send_line(self, line: str) -> None:
        if not self.connected:
            return
        self.conn.write((line + "\n").encode("ascii"))

    def send_status(self, status: str) -> None:
        log.debug("STATUS -> %s", status)
        self.send_line(f"STATUS:{status}")

    def poll(self) -> tuple[str, object] | None:
        line = self._read_line()
        if line is None:
            return None
        idx = line.rfind("CHUNK:")
        if idx != -1:
            try:
                size = int(line[idx + 6:])
            except ValueError:
                return None
            return ("chunk", self._read_exact(size))
        return ("line", line)

    def drain(self) -> None:
        if self.connected:
            self.conn.reset_input_buffer()
        self._buffer.clear()

    def _read_line(self, timeout: float = 0.0) -> str | None:
        deadline = time.time() + timeout
        while True:
            newline = self._buffer.find(b"\n")
            if newline != -1:
                raw = self._buffer[:newline]
                del self._buffer[: newline + 1]
                return raw.decode("ascii", errors="replace").strip()
            waiting = self.conn.in_waiting if self.connected else 0
            if waiting:
                self._buffer.extend(self.conn.read(waiting))
                continue
            if time.time() >= deadline:
                return None
            time.sleep(0.005)

    def _read_exact(self, n: int, timeout: float = 5.0) -> bytes:
        deadline = time.time() + timeout
        while len(self._buffer) < n and time.time() < deadline:
            waiting = self.conn.in_waiting
            if waiting:
                self._buffer.extend(self.conn.read(waiting))
            else:
                time.sleep(0.005)
        data = bytes(self._buffer[:n])
        del self._buffer[:n]
        return data

