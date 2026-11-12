# src/bootwire/transport/uart.py
"""
Serial transport.

A transport is any object with these four methods; the client needs nothing
else, so tests use an in-memory one (bootwire.sim.LoopbackTransport).

  write(data)          send bytes
  read(timeout) -> b   wait up to `timeout` seconds, return what arrived (may be empty)
  reset_input()        throw away bytes received so far
  close()
"""

from __future__ import annotations

import serial


class UARTTransport:
    def __init__(self, port: str, baudrate: int = 115200):
        """
        :param port:     device name ("/dev/ttyACM0", "COM3") or any pyserial URL,
                         for example "socket://192.168.1.50:4001" for a TCP bridge
        :param baudrate: 8 data bits, no parity, 1 stop bit, no flow control
        """
        self.ser = serial.serial_for_url(port, baudrate=baudrate, timeout=0)

    def write(self, data: bytes) -> None:
        self.ser.write(data)
        self.ser.flush()

    def read(self, timeout: float) -> bytes:
        self.ser.timeout = max(timeout, 0)
        data = self.ser.read(1)
        if data:
            waiting = self.ser.in_waiting
            if waiting:
                data += self.ser.read(waiting)
        return data

    def reset_input(self) -> None:
        self.ser.reset_input_buffer()

    def close(self) -> None:
        self.ser.close()
