"""JFL Alarm protocol handler."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from .const import JFL_MODELS, EVENT_CODES, ZONE_STATUS_MAP

_LOGGER = logging.getLogger(__name__)


class JFLProtocol:
    """Handle JFL alarm protocol communication."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize protocol handler."""
        self.host = host
        self.port = port
        self.server = None
        self.connected_clients = set()
        self.client_start_bytes = {}

        self._event_callback = None
        self._model_callback = None
        self._status_callback = None

        self.model_info = None
        self.current_zones = {}
        self.current_pgms = {}
        self.current_sensors = {}

    def set_event_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Set event callback."""
        self._event_callback = callback

    def set_model_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Set model info callback."""
        self._model_callback = callback

    def set_status_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Set status update callback."""
        self._status_callback = callback

    async def connect(self) -> None:
        """Start TCP server."""
        try:
            self.server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.port,
            )
            _LOGGER.info("JFL TCP server started on %s:%s", self.host, self.port)
        except Exception as err:
            _LOGGER.error("Failed to start TCP server: %s", err)
            raise

    async def disconnect(self) -> None:
        """Stop TCP server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            _LOGGER.info("JFL TCP server stopped")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle client connection."""
        client_addr = writer.get_extra_info("peername")
        self.connected_clients.add(writer)
        _LOGGER.info("Client connected: %s", client_addr)

        try:
            while True:
                data = await reader.read(1024)

                if not data:
                    break

                _LOGGER.debug(
                    "Received %s bytes from %s: %s",
                    len(data),
                    client_addr,
                    data.hex(),
                )
                await self._process_packet(data, writer)

        except asyncio.CancelledError:
            pass
        except ConnectionResetError as err:
            _LOGGER.warning("Client connection reset %s: %s", client_addr, err)
        except Exception as err:
            _LOGGER.error("Error handling client %s: %s", client_addr, err)
        finally:
            self.connected_clients.discard(writer)
            self.client_start_bytes.pop(writer, None)

            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

            _LOGGER.info("Client disconnected: %s", client_addr)

    async def _process_packet(
        self,
        data: bytes,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Process received packet."""
        packet_size = len(data)
        start_byte = data[0] if data else 0x7B
        self.client_start_bytes[writer] = start_byte

        response = None

        if packet_size == 5:
            response = self._create_response(
                [start_byte, 0x06, 0x01, 0x40, 0x01]
            )

        elif packet_size == 24:
            event_data = self._process_event_24(data)

            if event_data and self._event_callback:
                self._event_callback(event_data)

            response = self._create_response(
                [
                    start_byte,
                    0x0A,
                    0x01,
                    0x24,
                    0x01,
                    data[17],
                    data[18],
                    data[19],
                    data[20],
                ]
            )

        elif packet_size == 102:
            model_info = self._identify_model(data)

            if model_info and self._model_callback:
                self.model_info = model_info
                self._model_callback(model_info)

            response = self._create_response(
                [start_byte, 0x07, 0x01, 0x21, 0x01, 0x01]
            )

        elif packet_size >= 118:
            status_data = self._process_status_118(data)

            if status_data and self._status_callback:
                self._status_callback(status_data)

            response = self._create_response(
                [start_byte, 0x06, 0x01, 0x40, 0x01]
            )

        else:
            _LOGGER.warning(
                "Unknown packet size: %s bytes. Raw: %s",
                packet_size,
                data.hex(),
            )
            response = self._create_response(
                [start_byte, 0x06, 0x01, 0x40, 0x01]
            )

        if response:
            writer.write(response)
            await writer.drain()
            _LOGGER.debug("Response sent: %s", response.hex())

    def _create_response(self, message: list[int]) -> bytes:
        """Create response message with checksum."""
        checksum = 0

        for byte in message:
            checksum ^= byte

        return bytes(message + [checksum])

    def _identify_model(self, data: bytes) -> dict[str, Any] | None:
        """Identify JFL model from packet."""
        if len(data) < 42:
            return None

        model_byte = data[41]
        model_info = JFL_MODELS.get(model_byte)

        if model_info:
            return {
                "modelo": model_info["name"],
                "temEletrificador": model_info["eletrificador"],
                "numZonas": model_info["zonas"],
                "numPgms": model_info["pgms"],
                "numParticoes": model_info["particoes"],
                "modelByte": f"0x{model_byte:02X}",
            }

        return {
            "modelo": f"Unknown Model (0x{model_byte:02X})",
            "temEletrificador": False,
            "numZonas": 0,
            "numPgms": 0,
            "numParticoes": 0,
            "modelByte": f"0x{model_byte:02X}",
        }

    def _process_event_24(self, data: bytes) -> dict[str, Any] | None:
        """Process 24-byte event packet."""
        if len(data) < 12:
            return None

        event_code = data[8:12].decode("ascii", errors="ignore")
        zone = None

        if len(data) >= 16:
            zone = data[12:16].decode("ascii", errors="ignore").strip()

        event_info = EVENT_CODES.get(
            event_code,
            {
                "state": "UNKNOWN_EVENT",
                "description": f"Unknown event: {event_code}",
            },
        )

        result = {
            "event_code": event_code,
            "zone": zone,
            "state": event_info["state"],
            "description": event_info["description"],
            "armed_away": False,
            "armed_night": False,
            "armed_home": False,
            "alarm_sounding": False,
            "fire_alarm": False,
            "medical_alarm": False,
            "panic": False,
            "eletrificador": False,
        }

        state = event_info["state"]

        if state == "ARMED_STAY":
            result["armed_away"] = True
        elif state in ["ARMED_HOME"]:
            result["armed_home"] = True

            if event_code == "3407":
                result["eletrificador"] = True
        elif state == "FIRE":
            result["fire_alarm"] = True
        elif state == "EMERGENCY":
            result["medical_alarm"] = True
        elif state == "PANIC":
            result["panic"] = True
        elif state == "ALARM_SOUNDING":
            result["alarm_sounding"] = True

        return result

    def _process_status_118(self, data: bytes) -> dict[str, Any]:
        """Process 118-byte status packet."""
        result = {
            "zones": {},
            "pgms": {},
            "sensors": {},
        }

        if not self.model_info:
            return result

        num_zonas = self.model_info.get("numZonas", 0)
        num_pgms = self.model_info.get("numPgms", 0)

        if len(data) > 12:
            battery_byte = data[12]
            battery_info = self._interpret_battery_level(battery_byte)

            result["sensors"]["bateria"] = {
                "name": "Bateria",
                "state": battery_info["percentage"],
                "device_class": "battery",
                "description": battery_info["description"],
                "raw_value": battery_byte,
            }

        if len(data) > 13 and num_pgms > 0:
            self._process_pgm_status(data[13], 13, result["pgms"], num_pgms)

        if len(data) > 116 and num_pgms > 8:
            self._process_pgm_status(data[116], 116, result["pgms"], num_pgms)

        if len(data) > 81 and num_zonas > 0:
            zona = 1

            for i in range(50):
                if zona > num_zonas:
                    break

                byte_data = data[31 + i]
                high = (byte_data >> 4) & 0x0F
                low = byte_data & 0x0F

                if zona <= num_zonas:
                    result["zones"][f"zona_{zona}"] = self._get_zone_status(
                        zona,
                        high,
                    )
                    zona += 1

                if zona <= num_zonas:
                    result["zones"][f"zona_{zona}"] = self._get_zone_status(
                        zona,
                        low,
                    )
                    zona += 1

        return result

    def _interpret_battery_level(self, battery_byte: int) -> dict[str, Any]:
        """Interpret battery level from byte value."""
        if battery_byte >= 240:
            percentage, description = 100, "Bateria carregada"
        elif battery_byte >= 200:
            percentage, description = 80, "Bateria boa"
        elif battery_byte >= 150:
            percentage, description = 60, "Bateria média"
        elif battery_byte >= 100:
            percentage, description = 40, "Bateria baixa"
        elif battery_byte >= 50:
            percentage, description = 20, "Bateria muito baixa"
        else:
            percentage, description = 0, "Bateria crítica"

        return {"percentage": percentage, "description": description}

    def _process_pgm_status(
        self,
        byte_value: int,
        position: int,
        pgms_dict: dict,
        num_pgms: int,
    ) -> None:
        """Process PGM status from byte."""
        binary = f"{byte_value:08b}"

        for i in range(8):
            if position == 116:
                pgm_number = 9 + i
            else:
                pgm_number = 1 + i

            if pgm_number <= num_pgms:
                bit = int(binary[7 - i])
                pgm_id = f"pgm_{pgm_number}"

                pgms_dict[pgm_id] = {
                    "name": f"PGM {pgm_number}",
                    "state": "ON" if bit else "OFF",
                    "type": "toggle",
                    "pgm_number": pgm_number,
                }

    def _get_zone_status(
        self,
        zone_number: int,
        status_value: int,
    ) -> dict[str, Any]:
        """Get zone status from status value."""
        status_name = ZONE_STATUS_MAP.get(status_value, "unknown")
        is_open = status_value in [2, 4, 5, 7]

        return {
            "name": f"Zona {zone_number}",
            "state": "open" if is_open else "closed",
            "status": status_name,
            "zone_number": zone_number,
            "raw_status": status_value,
        }

    async def send_command(self, command: list[int]) -> None:
        """Send command to all connected clients."""
        if not self.connected_clients:
            _LOGGER.warning("No clients connected to send command")
            return

        for writer in list(self.connected_clients):
            try:
                start_byte = self.client_start_bytes.get(writer, 0x7B)
                message = self._create_response([start_byte] + command)

                writer.write(message)
                await writer.drain()

                _LOGGER.debug("Command sent to client: %s", message.hex())

            except Exception as err:
                _LOGGER.error("Failed to send command to client: %s", err)
                self.connected_clients.discard(writer)

    async def send_keep_alive(self) -> None:
        """Send keep alive to all connected clients."""
        await self.send_command([0x06, 0x01, 0x40, 0x01])

    async def send_get_state(self) -> None:
        """Send get state request to all connected clients."""
        await self.send_command([0x05, 0x01, 0x4D])