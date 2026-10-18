import time

import serial
from serial.tools import list_ports

import config
from logger import get_logger

log = get_logger("serial")

_ESP32_VIDS = {0x10C4, 0x1A86, 0x0403, 0x303A}

_SYNC0 = 0xAA
_SYNC1 = 0x55
_MAX_FRAME = 4096


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
                self._buffer.clear()
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
        self.conn.write((line + "\n").encode("ascii", errors="ignore"))

    def send_step(self, text: str) -> None:
        self.send_line(f"STEP:{text[:38]}")

    def send_rec_stop(self) -> None:
        self.send_line("REC:STOP")

    def send_status(self, status: str) -> None:
        log.debug("STATUS -> %s", status)
        self.send_line(f"STATUS:{status}")

    def _fill(self) -> None:
        waiting = self.conn.in_waiting if self.connected else 0
        if waiting:
            self._buffer.extend(self.conn.read(waiting))

    def poll(self) -> tuple[str, object] | None:
        """Return ("chunk", pcm_bytes) or ("line", text), or None if nothing complete yet.

        Audio arrives as frames: 0xAA 0x55 <len lo> <len hi> <PCM>.
        Everything else is newline-terminated ASCII text. A damaged frame can
        no longer swallow text lines like BUTTON:UP.
        """
        self._fill()
        buf = self._buffer
        while buf:
            if buf[0] == _SYNC0:
                if len(buf) < 4:
                    return None
                if buf[1] != _SYNC1:
                    del buf[0]
                    continue
                n = buf[2] | (buf[3] << 8)
                if n == 0 or n > _MAX_FRAME or n % 2:
                    del buf[:2]                      # bogus header, resync
                    continue
                if len(buf) < 4 + n:
                    return None                      # frame not complete yet
                data = bytes(buf[4:4 + n])
                del buf[:4 + n]
                return ("chunk", data)

            nl = buf.find(b"\n")
            sync = buf.find(bytes([_SYNC0]))
            if sync != -1 and (nl == -1 or sync < nl):
                del buf[:sync]                       # junk before a frame start
                continue
            if nl == -1:
                if len(buf) > 512:
                    buf.clear()                      # runaway junk
                return None
            raw = bytes(buf[:nl])
            del buf[:nl + 1]
            text = raw.decode("ascii", errors="replace").strip()
            if text:
                return ("line", text)
        return None

    def drain(self) -> None:
        if self.connected:
            self.conn.reset_input_buffer()
        self._buffer.clear()