"""Motor bus hardware abstraction for Feetech STS3215 servos."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class MotorBus(Protocol):
    """Low-level motor communication interface."""

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    @property
    def is_connected(self) -> bool: ...
    def ping(self, motor_id: int) -> bool: ...
    def read_position(self, motor_id: int) -> int: ...
    def write_position(self, motor_id: int, position: int) -> None: ...
    def set_torque(self, motor_id: int, enabled: bool) -> None: ...
    def write_motor_id(self, current_id: int, new_id: int) -> None: ...


class FeetechBus:
    """Feetech STS3215 serial bus using pyserial.

    Protocol: half-duplex UART, packet format compatible with Feetech STS/SCS series.
    Packet: [0xFF, 0xFF, ID, Length, Instruction, Params..., Checksum]
    """

    HEADER = bytes([0xFF, 0xFF])
    INST_PING = 0x01
    INST_READ = 0x02
    INST_WRITE = 0x03

    # STS3215 register addresses
    REG_ID = 5
    REG_TORQUE_ENABLE = 40
    REG_GOAL_POSITION = 42
    REG_MOVING_SPEED = 46
    REG_PRESENT_POSITION = 56

    def __init__(self, port: str, baudrate: int = 1_000_000, timeout: float = 0.1) -> None:
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._serial: object | None = None

    def connect(self) -> None:
        import serial

        self._serial = serial.Serial(
            port=self._port,
            baudrate=self._baudrate,
            timeout=self._timeout,
        )

    def disconnect(self) -> None:
        if self._serial is not None:
            self._serial.close()  # type: ignore[union-attr]
            self._serial = None

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open  # type: ignore[union-attr]

    def ping(self, motor_id: int) -> bool:
        try:
            return self._send(motor_id, self.INST_PING) is not None
        except Exception:
            return False

    def read_position(self, motor_id: int) -> int:
        data = self._read_register(motor_id, self.REG_PRESENT_POSITION, 2)
        return int.from_bytes(data, "little")

    def write_position(self, motor_id: int, position: int) -> None:
        self._write_register(motor_id, self.REG_GOAL_POSITION, position.to_bytes(2, "little"))

    def set_torque(self, motor_id: int, enabled: bool) -> None:
        self._write_register(motor_id, self.REG_TORQUE_ENABLE, bytes([1 if enabled else 0]))

    def write_motor_id(self, current_id: int, new_id: int) -> None:
        self._write_register(current_id, self.REG_ID, bytes([new_id]))

    def _read_register(self, motor_id: int, address: int, length: int) -> bytes:
        params = bytes([address, length])
        data = self._send(motor_id, self.INST_READ, params)
        if data is None or len(data) < length:
            raise IOError(f"Failed to read register {address} from motor {motor_id}")
        return data[:length]

    def _write_register(self, motor_id: int, address: int, value: bytes) -> None:
        params = bytes([address]) + value
        self._send(motor_id, self.INST_WRITE, params)

    def _send(self, motor_id: int, instruction: int, params: bytes = b"") -> bytes | None:
        if not self.is_connected:
            raise ConnectionError("Bus not connected")

        length = len(params) + 2
        body = bytes([motor_id, length, instruction]) + params
        checksum = (~sum(body)) & 0xFF
        packet = self.HEADER + body + bytes([checksum])

        ser = self._serial  # type: ignore[union-attr]
        ser.reset_input_buffer()
        ser.write(packet)
        ser.flush()

        # Read response header
        header = ser.read(2)
        if header != self.HEADER:
            return None

        resp_meta = ser.read(2)
        if len(resp_meta) < 2:
            return None

        resp_length = resp_meta[1]
        remaining = ser.read(resp_length)
        if len(remaining) < resp_length:
            return None

        # remaining = [error_byte, data..., checksum]
        error = remaining[0]
        if error != 0:
            raise IOError(f"Motor {motor_id} returned error: {error:#04x}")

        return remaining[1:-1]


@dataclass
class MockBus:
    """In-memory motor bus for testing without hardware."""

    _connected: bool = False
    _positions: dict[int, int] = field(default_factory=dict)
    _torque: dict[int, bool] = field(default_factory=dict)
    _present_ids: set[int] = field(default_factory=lambda: {1, 2, 3, 4, 5, 6})

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _require_connected(self) -> None:
        if not self._connected:
            raise ConnectionError("Bus not connected")

    def ping(self, motor_id: int) -> bool:
        return self._connected and motor_id in self._present_ids

    def read_position(self, motor_id: int) -> int:
        self._require_connected()
        return self._positions.get(motor_id, 2048)

    def write_position(self, motor_id: int, position: int) -> None:
        self._require_connected()
        self._positions[motor_id] = max(0, min(4095, position))

    def set_torque(self, motor_id: int, enabled: bool) -> None:
        self._require_connected()
        self._torque[motor_id] = enabled

    def write_motor_id(self, current_id: int, new_id: int) -> None:
        self._require_connected()
        if current_id in self._present_ids:
            self._present_ids.discard(current_id)
            self._present_ids.add(new_id)
            if current_id in self._positions:
                self._positions[new_id] = self._positions.pop(current_id)
            if current_id in self._torque:
                self._torque[new_id] = self._torque.pop(current_id)
