# alarm_server.py	
import socket
import threading
import time
import logging
from .const import DOMAIN, MANUFACTURER,SIGNAL_PANEL_MESSAGE
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import device_registry as dr
from homeassistant.core import HomeAssistant,callback
from homeassistant.helpers.dispatcher import dispatcher_send
import asyncio
_LOGGER = logging.getLogger(__name__)
from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    STATE_UNKNOWN,
    DEVICE_CLASS_BATTERY,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
    STATE_UNAVAILABLE,
    STATE_PROBLEM,
)

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
def interpret_battery_level(battery_byte):
 if battery_byte == 0:
  return 0, "Sem bateria"
 elif 1 <= battery_byte <= 100:
  return battery_byte, f"Bateria de lítio {battery_byte}%"
 elif 101 <= battery_byte <= 210:
  voltage = 7.2 + (battery_byte - 101) * 0.0779  # 0.0779 = (15 - 7.2) / 109
  percentage = 0
  if voltage > 12.5:
      percentage = 100
  elif 12 <= voltage <= 12.5:
      percentage = 80
  elif 11.5 <= voltage < 12:
      percentage = 60
  elif 11 <= voltage < 11.5:
      percentage = 40
  elif 10.5 <= voltage < 11:
      percentage = 20
  else:
      percentage = 0  # Nível crítico
  return percentage, f"Bateria de chumbo {voltage:.2f}V ({percentage}%)"
 elif battery_byte == 255:
  return 100, "Carregando bateria"
 else:
  return None, "Valor reservado"


class AlarmServer:
    def __init__(self, hass, host, port,config_entry_id):
        self.hass = hass
        self.host = host
        self.port = port
        self.sock = None
        self._config_entry_id=config_entry_id
        self._unique_id = f"alarm_central_{host}:{port}"
        self.client = None
        self.running = False
        self._num_pgms=0
        self._pgms ={}
        self.eletrificador=0
        self.connected=False
        self._num_particoes=0
        self._num_zonas=0
        self._zonas = {}
        self._sensors = {}
        self.data = {}
        self.mac=None
        self.ns=None
        self.t=time.time()
        self._model="Active"
        self._sw_version="0.0"
        self.armed_away=False 
        self.armed_home=False
        self.fire_alarm=False
        self.armed_night = False
        self._attr_state = STATE_ALARM_DISARMED
        self.alarm_sounding = False
        self.alarm_event_occurred = False        
        self.status_alarme=False
        self.comando=False
        self._update_callbacks = set()
        self._data = {}  # Armazena os dados mais recentes
        _LOGGER.debug(f"AlarmServer initialized with unique_id: {self._unique_id}")
    
    def register_callback(self, callback_func):
        """Registra um callback para ser chamado quando houver uma atualização."""
        self._update_callbacks.add(callback_func)
    def remove_callback(self, callback_func):
        """Remove um callback registrado."""
        self._update_callbacks.discard(callback_func)
    @callback
    def _notify_updates(self):
        """Notifica todos os callbacks registrados sobre a atualização."""
        for callback_func in self._update_callbacks:
           self.hass.async_create_task(callback_func())
    @property
    def unique_id(self):
        if not hasattr(self, '_unique_id'):
            _LOGGER.error("_unique_id not initialized")
            return f"alarm_central_{self.host}:{self.port}"
        return self._unique_id
    @property
    def model(self):
        return self._model
    @property
    def sw_version(self):
        return self._sw_version
    @property
    def sensors(self):
        return self._sensors
    @property
    def zonas(self):
        return self._zonas
    @property
    def num_zonas(self):
        return self._num_zonas
    @property
    def pgms(self):
        return self._pgms
    @property
    def num_pgms(self):
        return self._num_pgms
    @property
    def num_particoes(self):
        return self._num_particoes
    def initialize_zonas(self):
        """Inicializa as zonas com base no número fornecido."""
        _LOGGER.warn(f'inicializando as zonas da central#################################################################')
        for i in range(self._num_zonas):
            zona_id = f"zona_{i+1}"
            self.zonas[zona_id] = {
                'name': f"Zona {i+1}",
                'state': False
            }
    def initialize_eletrificador(self):
        """Inicializa o eletrificador base no número fornecido."""
        _LOGGER.warn(f'inicializando eletrificador da central#################################################################')
        self.pgms["eletrificador"] = {
                'name': f"Eletrificador",
                'state': STATE_OFF,
                'type': "toggle",
                'switch_number': 99,
                'tipo': "ELETRIFICADOR"  
            }
    def initialize_sensors(self):
        """Inicializa as sensores com base no número fornecido."""
        _LOGGER.warn(f'inicializando os sensores dacentral#################################################################')
        self.sensors['bateria'] = {
                'name': f"Bateria",
                'state': None,
                'device_class': DEVICE_CLASS_BATTERY
            }
    def initialize_particoes(self):
        """Inicializa as particoes com base no número fornecido."""
        _LOGGER.warn(f'inicializando os sensores dacentral#################################################################')
        for i in range(self._num_particoes):
            particao_id = f"particao_{i+1}"
            self.sensors[particao_id] = {
                'name': f"Particao {i+1}",
                'state': STATE_ALARM_DISARMED,  
                'device_class': "ENUM"
            }
    def initialize_pgms(self):
        """Inicializa as pgms  com base no número fornecido."""
        _LOGGER.warn(f'inicializando as pgms da central#################################################################')
        for i in range(self._num_pgms):
            pgm_id = f"pgm_{i+1}"
            self.pgms[pgm_id] = {
                'name': f"Pgm {i+1}",
                'state': STATE_OFF,
                'type': "toggle",
                'switch_number': {i+1},
                'tipo': "PGM"  # Inicialmente, todas as pgms
            }
    def checksum(self,dados):
        checksum = 0
        for n in dados:
           checksum ^= n
        return checksum
    def setEletrificadorStatus(self,eletrificador_byte):
        if '00'  in f'{eletrificador_byte:0>2X}':
           ele_state=STATE_UNKNOWN
        elif '01' in f'{eletrificador_byte:0>2X}':
           
           ele_state=STATE_OFF
        elif '02' in f'{eletrificador_byte:0>2X}':
           ele_state=STATE_ON
        elif '03' in f'{eletrificador_byte:0>2X}':
           ele_state=STATE_ON
        elif '04' in f'{eletrificador_byte:0>2X}':
           ele_state=STATE_UNKNOWN
           dados_evento = {
              "estado": "Não Pronto",
              "dispositivo": "eletrificador",
              "timestamp": datetime.now().isoformat()
           }
           self.hass.bus.fire(evento_tipo, dados_evento)
        elif '81' in f'{eletrificador_byte:0>2X}':
           ele_state=STATE_OFF
           dados_evento = {
              "estado": STATE_ALARM_TRIGGERED,
              "dispositivo": "eletrificador",
              "timestamp": datetime.now().isoformat()
           }
           hass.bus.fire(evento_tipo, dados_evento)
        elif '82' in f'{eletrificador_byte:0>2X}':
           ele_state=STATE_ON
           dados_evento = {
              "estado": STATE_ALARM_TRIGGERED,
              "dispositivo": "eletrificador",
              "timestamp": datetime.now().isoformat()
           }
           hass.bus.fire(evento_tipo, dados_evento)
        elif '83' in f'{eletrificador_byte:0>2X}':
           ele_state=STATE_ON
           dados_evento = {
              "estado": STATE_ALARM_TRIGGERED,
              "dispositivo": "eletrificador",
              "timestamp": datetime.now().isoformat()
           }
           hass.bus.fire(evento_tipo, dados_evento)
        elif '84' in f'{eletrificador_byte:0>2X}':
           ele_state=STATE_OFF
           dados_evento = {
              "estado": STATE_ALARM_TRIGGERED,
              "dispositivo": "eletrificador",
              "timestamp": datetime.now().isoformat()
           }
           hass.bus.fire(evento_tipo, dados_evento)
        if self.eletrificador==0 and ele_state != STATE_UNKNOWN:
           self.eletrificador=1
           self.initialize_eletrificador()
           self.hass.bus.fire("alarm_central_updated")

        self.pgms["eletrificador"] = {
                'name': f"Eletrificador",
                'state': ele_state,
                'type':"toogle",
                'tipo':"switch",
                'switch_number':99
        }
    def setBatteryStatus(self, battery_byte):
      percentage, description = interpret_battery_level(battery_byte)
      self.sensors['bateria'] = {
                'name': f"Bateria",
                'state': percentage,
                'device_class': DEVICE_CLASS_BATTERY
            }
          
    def setPgmStatus(self,byte_value,posicao):
        binary = format(byte_value, '08b')  # Converte para string binária de 8 bits
        for i, bit in enumerate(binary):
            if posicao==2:
               pgm_number=16-i
            else:
               pgm_number=8-i
            #if pgm_number >self._num_pgms:
            #   break
            pgm_id = f'pgm_{pgm_number}'
            if pgm_id in self.pgms:        
              if int(bit) >0:             
                # _LOGGER.warn(f'#################################################pgm acionada {pgm_number}')
                 self.pgms[f'pgm_{pgm_number}']={"name":f'Pgm {pgm_number}',"type":"toogle","tipo": "PGM","state":STATE_ON,"switch_number": pgm_number}
              else:
                 self.pgms[f'pgm_{pgm_number}']={"name":f'Pgm {pgm_number}',"type":"toogle","tipo": "PGM","state":STATE_OFF,"switch_number": pgm_number}

    def setZoneStatus(self, zona, status):
        status_map = {
            0: "disabled",
            1: "inhibited",
            2: "triggered",
            3: "no_communication",
            4: "short_circuit",
            5: "tamper_open",
            6: "low_battery",
            7: "open",
            8: "closed"
        }
        
        zona_id=f'zona_{zona}'
        self.zonas[zona_id]={"state":status_map.get(status, STATE_UNKNOWN),"name":f'Zona {zona}'}
        if status in [2, 4, 5, 7]:  # triggered, short_circuit, tamper_open, open
           self.zonas[zona_id]={"state":STATE_ON,"name":f'Zona {zona}'}
        else:
            self.zonas[zona_id] = {"state":STATE_OFF,"name":f'Zona {zona}'}
        #_LOGGER.warn(f'total de zonaso  {self.zonas[zona_id]}')
        
    def start(self):
        max_retries = 5
        retry_delay = 5  # segundos
        for attempt in range(max_retries):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.bind((self.host, self.port))
                self.sock.listen(1)
                self.running = True
                
                threading.Thread(target=self.accept_connections, daemon=True).start()
                threading.Thread(target=self.send_keepalive, daemon=True).start()
                
                _LOGGER.info(f"AlarmServer started successfully on {self.host}:{self.port}")
                return
            except OSError as e:
                if e.errno == 98:  # Address already in use
                    _LOGGER.warning(f"Port {self.port} is already in use. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise

        _LOGGER.error(f"Failed to start AlarmServer after {max_retries} attempts")
        raise ConfigEntryNotReady("Failed to start AlarmServer due to port conflict")

    def accept_connections(self):
        while self.running:
            try:
                self.client, _ = self.sock.accept()
                threading.Thread(target=self.handle_client, daemon=True).start()
            except Exception as e:
                _LOGGER.error(f"Error accepting connection: {e}")
                break

    def handle_client(self):
        self.connected = True
        sequencial=1
        while self.running:
            self.t=time.time()
            sequencial += 1
            if sequencial > 255:
               sequencial=1
            if sequencial % 5 ==0:
               message = b'\x7B\5\x02\x4D'
               check = self.checksum(message)
               message += check.to_bytes(1,'big')
               self.client.send(bytes(message))
            self.client.settimeout(2)
            try:
               data = self.client.recv(1024)
            except socket.timeout as e:
               err = e.args[0]
               if err == 'timed out':
                 continue
               else:
                 break
            except socket.error as e:
                 break
            else:
              self.process_data(data)
            if (time.time() - self.t) >35:
                self.t= time.time()
                self.send_pedido_Status()
                _LOGGER.warn("Envia pedido de status  apos tempo")
    def process_central(self,data):
        #_LOGGER.warn("Tipo Central  %s", f'{data[41]:0>2X}')
        if 'A0' in f'{data[41]:0>2X}':
              MODELO = 'Active-32 Duo'
              self._num_pgms=4
              self.eletrificador=1
              self._num_particoes=4
              self._num_zonas=32
        elif 'A1' in f'{data[41]:0>2X}':
              MODELO = 'Active 20 Ultra/GPRS'
              self._num_pgms=4
              self.eletrificador=1
              self._num_particoes=2
              self._num_zonas=22
        elif 'A2' in f'{data[41]:0>2X}':
              MODELO = 'Active 8 Ultra'
              self._num_pgms=0
              self.eletrificador=0
              self._num_particoes=2
              self._num_zonas=12
        elif 'A3' in f'{data[41]:0>2X}':
              MODELO = 'Active 20 Ethernet'
              self._num_pgms=4
              self.eletrificador=1
              self._num_particoes=2
              self._num_zonas=22
        elif 'A4' in f'{data[41]:0>2X}':
              MODELO = 'Active 100 Bus'
              self._num_pgms=16
              self.eletrificador=1
              self._num_particoes=16
              self._num_zonas=99
        elif 'A5' in f'{data[41]:0>2X}':
              MODELO = 'Active 20 Bus'
              self._num_pgms=16
              self.eletrificador=1
              self._num_particoes=2
              self._num_zonas=32
        elif 'A6' in f'{data[41]:0>2X}':
              MODELO = 'Active Full 32'
              self._num_pgms=16
              self.eletrificador=0
              self._num_particoes=4
              self._num_zonas=32
        elif 'A7' in f'{data[41]:0>2X}':
              MODELO = 'Active 20'
              self._num_pgms=4
              self.eletrificador=1
              self._num_particoes=2
              self._num_zonas=32
        elif 'A8' in f'{data[41]:0>2X}':
              MODELO = 'Active 8W'
              self._num_pgms=4
              self.eletrificador=1
              self._num_particoes=2
              self._num_zonas=32
        elif '4B' in f'{data[41]:0>2X}':
              MODELO = 'M-300+'
              self._num_pgms=2
              self.eletrificador=0
              self._num_particoes=0
        elif '5D' in f'{data[41]:0>2X}':
              MODELO = 'm-300 Flex'
              self._num_pgms=2
              self.eletrificador=0
              self._num_particoes=0
        self._model = MODELO
        self.mac=data[29:41].decode("utf-8")
        self.ns = data[4:14].decode('ascii')
        vm=chr(data[42])
        vs=chr(data[43])
        vx=chr(data[44])
        self.particoes=ord(chr(data[51]))
        if '00' in f'{data[54]:0>2X}':
          self.eletrificador=0
        else:
          self.eletrificador=1
        if vx==0:
           if vs==0:
              self._sw_version=vm+".0"
           else:
             self._sw_version=vm+"."+vs
        else:
            self._sw_version=vm+"."+vs+"."+vs
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_or_create(
          config_entry_id=self._config_entry_id,
          identifiers={(DOMAIN, self._unique_id)},
          name="Central de Alarme",
          manufacturer=MANUFACTURER,
          model=self._model,
          sw_version=self.sw_version,
        )
        if device:
          print(f"Updated device {device.id} with model: {self._model}, SW version: {self._sw_version}")
          self.hass.bus.async_fire("device_updated",{
            "device_id": device.id,
            "updated_info": {self._sw_version}
          })
          self.initialize_zonas()
          self.initialize_pgms()
          self.initialize_sensors()
          self.initialize_particoes()
          self.initialize_eletrificador()
          self.hass.bus.fire("alarm_central_updated")
        else:
          print(f"Device not found in the registry.")

    def process_evento(self,evento):
       _LOGGER.warn(f'############################################################## EVENTO ###### {evento}')
       if evento =="1306":
          _LOGGER.warn("progamação da central alterada")
          self.send_pedido_Status()
       if evento == "3441" :
          self.armed_away = False
          self.status_alarm=STATE_ALARM_ARMED_HOME
          self._attr_state = STATE_ALARM_ARMED_HOME
          dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
       if evento =='1602':
          _LOGGER.warn(f'############################################################## Teste Periodico da Central ###### {evento}')
       if evento == '3401' or evento == '3407' or evento =='3403' or evento =='3404' or evento =='3408' or evento=='3409' :
          self.armed_away = True
          self.armed_night = False
          self.armed_home = False
          self.status_alarm=STATE_ALARM_ARMED_AWAY
          self._attr_state = STATE_ALARM_ARMED_AWAY
          if evento == '3407':
             self.eletrificador=True
          dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
       if evento == '1401' or evento =='1407' or evento =='1403' or evento=='1409':
          _LOGGER.warn("Evento  %s", evento)
          if evento == '1407':
            self.eletrificador=False
          else:
            self.armed_away =False
            self.armed_night =False
            self.alarm_sounding = False
            self.fire_alarm = False
            self._attr_state = STATE_ALARM_DISARMED
            self.status_alarm=STATE_ALARM_DISARMED
          dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
       if evento == '1130' and self.armed_home == True:
          self.fire_alarm=True
          self.status_alarm=STATE_ALARM_TRIGGERED
          dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
       if evento == '3130':
          self.fire_alarm=False
          self.status_alarm=STATE_ALARM_DISARMED
          dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
       if evento == '1134' and self.armed_home == True:
          self.fire_alarm=True
          self.status_alarm=STATE_ALARM_TRIGGERED
          dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
       if evento == '3134':
          self.fire_alarm=False
          self.status_alarm=STATE_ALARM_DISARMED
          dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
       if evento == '1137' and self.armed_home == True:
          self.fire_alarm=True
          self.status_alarm=STATE_ALARM_TRIGGERED
          dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
       if evento == '3137':
          self.fire_alarm=False
          self.status_alarm=STATE_ALARM_DISARMED
          dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)  
          #self.text="Eletrificador Armado"
       if evento == '1301':
          _LOGGER.warn(f'falta de energia {evento}')
       if evento == '3301':
          _LOGGER.warn(f'Retorno de energia {evento}')
       
    def process_data(self, data):
        # Implementar a lógica de processamento dos dados recebidos
        #_LOGGER.warn("tamanho do Pacote %s",len(data))
        if len(data)==5:
           message = b'\x7B\6\x01\x40\x01'
           check = self.checksum(message)
           message += check.to_bytes(1,'big')
           self.client.send(bytes(message))
           _LOGGER.warn("enviado ack da conexao %s",len(data))
        if len(data) ==24:
           evento = data[8:12].decode('ascii')
           self.process_evento(evento)
           message = b'\x7b\x0a\x01\x24\x01'
           message += bytes({data[17]})
           message += bytes({data[18]})
           message += bytes({data[19]})
           message += bytes({data[20]})
           check = self.checksum(message)
           message += check.to_bytes(1,'big')
           _LOGGER.warn('Send ACK ')
           self.client.send(bytes(message))
        if len(data)==102:
           self.process_central(data)
           message = b'\x7B\7\x01\x21\x01\x01'
           check = self.checksum(message)
           message += check.to_bytes(1,'big')
           #_LOGGER.warn('Send Accept')
           self.client.send(bytes(message))
           ##envia pedido de Status
           self.send_pedido_Status()
        if len(data) >=118:
           #_LOGGER.warn("pacote 118")
           zona = 1
           for i in range(50):
             high, low = data[31+i] >> 4, data[31+i] & 0x0F
             for x in range(1, 3):
                if x == 1:
                    self.setZoneStatus(zona, high)
                else:
                    self.setZoneStatus(zona, low)
                zona += 1
                if zona > self._num_zonas:
                    break
             if zona > self._num_zonas:
                break
           ##PGMS
           self.setBatteryStatus(data[12])
           self.setPgmStatus(data[13],1)
           self.setPgmStatus(data[87],2)
           ## ELEtrificador
           self.setEletrificadorStatus(data[30])
           #_LOGGER.warn("fim do pacote 118")
           self._notify_updates()
           self.send_pedido_Status()
    def send_pedido_Status(self):       
        if self.client:
           if self.comando:
              self.comand=false
           else:
              message = b'\x7b\5\x01\x4d'
              check = self.checksum(message)
              message += check.to_bytes(1,'big')
              self.client.send(bytes(message))
    def send_command(self,comando):
        _LOGGER.warn(comando)
        self.comand=True
        if comando=="disarm":
           if self.client:
              _LOGGER.warn("Enviando comando para desarmar")
        elif comando=="arm_away":
           if self.client:
              _LOGGER.warn("Enviando comando para armar away")
        elif comando=="arm_home":
           if self.client:
              _LOGGER.warn("Enviando comando para armar Home")
        elif comando=="arm_night":
           if self.client:
              _LOGGER.warn("Enviando comando para armar a noite")
        else:
           if self.client:
              _LOGGER.warn("Enviando comando para desarmar ")

               
    def send_keepalive(self):
        while self.running:
            if self.client:
               self.comand=True
               if (time.time() - self.t) >35:
                  self.t=time.time()
                  self.send_pedido_Status()
                  _LOGGER.warn("Envia pedido de status  apos tempo")
               else:
                 #_LOGGER.warn("enviando keepalive")
                 message = b'\x7B\6\x01\x40\x01'
                 check = self.checksum(message)
                 message += check.to_bytes(1,'big')
                 self.client.send(bytes(message))
            time.sleep(40)
    def turn_on_switch(self,pgm):
        if self.client:
           self.comand=True
           _LOGGER.warn(f'acionando pgm:{pgm}')
           message = b'\x7b\6\x01\x50\{pgm}'
           check = self.checksum(message)
           message += check.to_bytes(1,'big')
           self.client.send(bytes(message))
           
    def turn_off_switch(self,pgm):
        if self.client:
           self.comand=True
           _LOGGER.warn(f'acionando pgm:{pgm}')
           message = b'\x7b\6\x01\x51\{pgm}'
           check = self.checksum(message)
           message += check.to_bytes(1,'big')
           self.client.send(bytes(message))
           
      
    async def stop(self):
        self.running = False
        if self.client:
            self.client.close()
        if self.sock:
            self.sock.close()
    def get_all_sensor_states(self):
      return {sensor_id: {"state": sensor_info['state'],"name": sensor_info['name'],"device_class":sensor_info['device_class']} for sensor_id, sensor_info in self.sensors.items()} 
    def get_all_switch_states(self):
      return {switch_id: {"state": switch_info['state'],"name": switch_info['name'],"type":switch_info['type'],"tipo":switch_info['tipo'],"switch_number":switch_info["switch_number"]} for switch_id, switch_info in self.pgms.items()} 
    def get_all_binary_sensor_states(self):
      return {zone_id: {"state": zone_info['state'],"name": zone_info['name']} for zone_id, zone_info in self.zonas.items()} 
