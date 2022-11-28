"""Support for JFL Active devices."""
from datetime import timedelta
import logging
import socket
import select
import threading
import time
import fcntl, os
import errno

from bitarray import bitarray

from queue import Queue
from alarmdecoder.util import NoDeviceError

from homeassistant.config_entries import ConfigEntry

from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
    ATTR_CODE,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_AD,
    DATA_REMOVE_STOP_LISTENER,
    DATA_REMOVE_UPDATE_LISTENER,
    DATA_RESTART,
    DOMAIN,
    CONF_PARTITION,
    CONF_MODELO,
    SIGNAL_PANEL_MESSAGE,
    SIGNAL_REL_MESSAGE,
    SIGNAL_RFX_MESSAGE,
    SIGNAL_ZONE_FAULT,
    SIGNAL_ZONE_RESTORE,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]
queue1 = Queue()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up JFL Active config flow."""
    undo_listener = entry.add_update_listener(_update_listener)

    ad_connection = entry.data

    def stop_alarmdecoder(event):
        """Handle the shutdown of JFL Active."""
        if not hass.data.get(DOMAIN):
            return
        _LOGGER.debug("Shutting down JFL Active")
        hass.data[DOMAIN][entry.entry_id][DATA_RESTART] = False
        _LOGGER.debug("Shutting down JFL Active")
        
    async def open_connection():
        """Open a connection to JFL Active."""
        watcher = JFLWatcher(hass,ad_connection,queue1)
        watcher.start()

    remove_stop_listener = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP, stop_alarmdecoder
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_AD: queue1,
        DATA_REMOVE_UPDATE_LISTENER: undo_listener,
        DATA_REMOVE_STOP_LISTENER: remove_stop_listener,
        DATA_RESTART: False,
    }
    hass.async_create_task(open_connection())
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a JFL Active entry."""
    hass.data[DOMAIN][entry.entry_id][DATA_RESTART] = False

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if not unload_ok:
        return False

    hass.data[DOMAIN][entry.entry_id][DATA_REMOVE_UPDATE_LISTENER]()
    hass.data[DOMAIN][entry.entry_id][DATA_REMOVE_STOP_LISTENER]()
    """await hass.async_add_executor_job(hass.data[DOMAIN][entry.entry_id][DATA_AD].close)"""

    if hass.data[DOMAIN][entry.entry_id]:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return True


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("JFL Active options updated: %s", entry.as_dict()["options"])
    await hass.config_entries.async_reload(entry.entry_id)


class JFLWatcher(threading.Thread):
    """Event listener thread to process JFL events."""
    def checksum(self,dados):
        checksum = 0
        for n in dados:
           checksum ^= n
        return checksum


    def __init__(self,hass, ad_connection,queue1):
        """Initialize JFL watcher thread."""
        super().__init__()
        self.daemon = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN,'0008dc0017ca' )},
            manufacturer="JFL ",
            name="JFL ACrive",
        )
        self._attr_unique_id = '0008dc0017ca'
        self.host = ad_connection[CONF_HOST]
        self.port = ad_connection[CONF_PORT]
        self.hass = hass
        self.armed_away = False
        self.armed_night = False
        self._attr_state = STATE_ALARM_DISARMED
        self.alarm_sounding = False
        self.fire_alarm = False
        self.armed_home = False
        self.text = "Home Assistant"
        self.text = "Home Assistant"
        self.ac_power = True
        self.alarm_event_occurred = False
        self.backlight_on = True
        self.battery_low = False
        self.check_zone = False
        self.chime_on = True
        self.CONF_PARTITION = False
        self.entry_delay_off = False
        self.programming_mode = False
        self.ready = True
        self.zone_bypassed = False
    def bitExtracted(self, number, k, p):
        return ( ((1 << k) - 1)  &  (number >> (p-1) ) );
    def setZoneStatus(self,zone,status):
        if status == 0:
             ##dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, zone)
             self.text = "Zona " + str(zone) + " Zona Desabilitada"
             ##dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
        elif status == 1:
             #dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, zone)
             self.text = "Zona " + str(zone) + " Zona Inibida"
             #dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
        elif status == 2:
             dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, zone)
             self.text = "Zona " + str(zone) + " Zona Disparada"
             dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
        elif status == 3:
             #dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, zone)
             self.text = "Zona " + str(zone) + " Sensor sem Comunicacao"
             #dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
        elif status == 4:
             #dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, zone)
             self.text = "Zona " + str(zone) + " Zona Em curto"
             #dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
        elif status == 5:
             #dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, zone)
             self.text = "Zona " + str(zone) + " Tamper Aberto"
             #dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
        elif status == 6:
             #dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, zone)
             self.text = "Zona " + str(zone) + " Bateria Baixa"
             #dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
        elif status == 7:
             dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, zone)
             self.text = "Zona " + str(zone) + " Zona Aberta"
             dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
        elif status == 8:
             dispatcher_send(self.hass, SIGNAL_ZONE_RESTORE, zone)

    def run(self):
        """Open a connection to JFL Active."""
        _LOGGER.warn("Starting JFL Integration")
        device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self) 
        with device as s:
           self.text = "Not Connected"
           dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
           s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
           try:
              s.bind((self.host, self.port))
           except:
              return
           s.listen()
           #s.setblocking(False)
           while True:  
             conn, addr = s.accept()
             sequencial=1
             with conn:
                 _LOGGER.warn("Connected by %s",addr)
                 self.text = "Connected"
                 t=time.time()
                 while True:
                     sequencial += 1  
                     if sequencial > 256:
                        sequencual=1
                     elapsed = 0
                     if not queue1.empty():
                        val = queue1.get()
                        sent = conn.send(val)
                     conn.settimeout(2)
                     try:
                       data = conn.recv(255)
                     except socket.timeout as e:
                       err = e.args[0]
                       if err == 'timed out':
                         continue
                       else:
                         break
                     except socket.error as e:
                      break
                     else:
                      if len(data) == 0:
                        break
                      else:
                        _LOGGER.info("dentro da conexao recebido %s" %(data))
                        ####evento
                        if len(data) ==24:
                           evento = data[8:12].decode('ascii')
                           if evento == '3401' or evento == '3407' or evento =='3403' or evento =='3404' or evento =='3408' or evento=='3409' or evento=='3441':
                              self.armed_away =False
                              self.armed_night =False
                              self.armed_home =True
                              self._attr_state = STATE_ALARM_ARMED_HOME
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == '1401' or evento =='1407' or evento =='1403' or evento=='1409':
                              _LOGGER.warn("Evento  %s", evento)
                              self.armed_home =False
                              self.armed_away =False
                              self.armed_night =False
                              self._attr_state = STATE_ALARM_DISARMED
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == '1130' and self.armed_home == True:
                              self.fire_alarm=True
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == '3130':
                              self.fire_alarm=False
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == '1134' and self.armed_home == True:
                              self.fire_alarm=True
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == '3134':
                              self.fire_alarm=False
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == '1137' and self.armed_home == True:
                              self.fire_alarm=True
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == '3137':
                              self.fire_alarm=False
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           _LOGGER.warn("Eventos=%s", evento)
                        if len(data) == 118:
                           #_LOGGER.warn("Recebido informacoes de Status")
                           #_LOGGER.warn("dia  %s",  data[6])
                           #_LOGGER.warn("mes  %s", data[7])
                           #_LOGGER.warn("ano  %s", data[8])
                           #_LOGGER.warn("Hora  %s", data[9])
                           #_LOGGER.warn("Minuto  %s", data[10])
                           #_LOGGER.warn("Segundo  %s", data[11])
                           
                           if data[12]/14 > 12.5:
                              #_LOGGER.warn("Bateria  Normal")
                              self.text = "Bateria Normal"
                              self.battery_low = False
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if data[12]/14 < 11:
                              self.text = "Bateria Baixa"
                              #_LOGGER.warn("Bateria Baixa")
                              self.battery_low = True
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           #_LOGGER.warn("PGM  %s", data[13])
                           ### status das particoes
                           #for i in range(1,16):
                           #   _LOGGER.warn("###############  PART %s Status %s", i,data[13+i])
                           ### Status eletrificador
                           #_LOGGER.warn("Eletrificador %s",data[30])
                           #### Status das zonas
                           zona=1
                           for i in range(50):
                               high, low = data[31+i] >>4, data[31+i] & 0x0F
                               for x in range(1,3):
                                  if x ==1:
                                     #_LOGGER.warn("###############  Zona %s Status %s", zona,high)
                                     self.setZoneStatus(zona,high)
                                     zona += 1  
                                  else:
                                     #_LOGGER.warn("###############  Zona %s Status %s", zona,low)
                                     self.setZoneStatus(zona,low)
                                     zona +=1
                           

                                  
                        if chr(data[0]) == '{':
                           _LOGGER.warn("tamanho do Pacote %s",len(data))
                           if chr(data[3]) == '$':
                              if '00' in f'{data[21]:0>2X}':
                                 #_LOGGER.warn("com particao 01 nao configurada")
                                 self._attr_state = STATE_ALARM_DISARMED
                                 self.alarm_sounding = False
                                 self.fire_alarm = False
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '01' in f'{data[21]:0>2X}':
                                 #_LOGGER.warn("com particao 01 Desarmada pronta sem disparo")
                                 self.alarm_sounding = False
                                 self.fire_alarm = False
                                 self._attr_state = STATE_ALARM_DISARMED
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '02' in f'{data[21]:0>2X}':
                                 #_LOGGER.warn("com particao 01 Armada sem disparo")
                                 self.fire_alarm = False
                                 self.alarm_sounding = False
                                 self._attr_state = STATE_ALARM_ARMED_AWAY
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '03' in f'{data[21]:0>2X}':
                                 #_LOGGER.warn("com particao 01 Armada HOME sem disparo")
                                 self.alarm_sounding = False
                                 self.fire_alarm = False
                                 self._attr_state = STATE_ALARM_ARMED_HOME
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '04' in f'{data[21]:0>2X}':
                                 #_LOGGER.warn("com particao 01 Desarmada nao pronta e sem disparo")
                                 self._attr_state = STATE_ALARM_DISARMED
                                 self.alarm_sounding = False
                                 self.fire_alarm = False
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '81' in f'{data[21]:0>2X}':
                                 #_LOGGER.warn("Desarmada em disparo")
                                 self.alarm_sounding = True
                                 self.fire_alarm = True
                                 self._attr_state = STATE_ALARM_DISARMED
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '82' in f'{data[21]:0>2X}':
                                 #_LOGGER.warn("armada em disparo")
                                 self.alarm_sounding = True
                                 self.fire_alarm = True
                                 self._attr_state = STATE_ALARM_ARMED_AWAY
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '83' in f'{data[21]:0>2X}':
                                 #_LOGGER.warn("Armada Stay em disparo")
                                 self._attr_state = STATE_ALARM_ARMED_HOME
                                 self.alarm_sounding = True
                                 self.fire_alarm = True
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '84' in f'{data[21]:0>2X}':
                                 #_LOGGER.warn("Desarmada pronta e em disparo")
                                 self.alarm_sounding = True
                                 self.fire_alarm = True
                                 self._attr_state = STATE_ALARM_DISARMED
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              message = b'\x7b\x0a\x01\x24\x01'
                              message += bytes({data[17]})
                              message += bytes({data[18]})
                              message += bytes({data[19]})
                              message += bytes({data[20]})
                              check = self.checksum(message)
                              message += check.to_bytes(1,'big')
                              #_LOGGER.warn('Send akc ')
                              #_LOGGER.warn(message)
                              conn.send(bytes(message))

                           if len(data)==102:
                              #_LOGGER.warn("Tipo Central  %s", f'{data[41]:0>2X}')
                              if 'A0' in f'{data[41]:0>2X}':
                                 MODELO = 'Active-32 Duo'
                              elif 'A1' in f'{data[41]:0>2X}':
                                 MODELO = 'Active 20 Ultra/GPRS'
                              elif 'A2' in f'{data[41]:0>2X}':
                                 MODELO = 'Active 8 Ultra'
                              elif 'A3' in f'{data[41]:0>2X}':
                                 MODELO = 'Active 20 Ethernet'
                              elif 'A4' in f'{data[41]:0>2X}':
                                 MODELO = 'Active 100 Bus'
                              elif 'A5' in f'{data[41]:0>2X}':
                                 MODELO = 'Active 20 Bus'
                              elif 'A6' in f'{data[41]:0>2X}':
                                 MODELO = 'Active Full 32'
                              elif 'A7' in f'{data[41]:0>2X}':
                                 MODELO = 'Active 20'
                              self.CONF_MODELO = MODELO
                              ####Status######
                              #_LOGGER.warn("Problema da central  %s", f'{data[50]:0>2X}')
                              #_LOGGER.warn("Total de particoes  %s", f'{data[51]:0>2X}')
                              #_LOGGER.warn("Conta  %s", f'{data[52]:0>2X}')
                              #_LOGGER.warn("Conta  %s", f'{data[53]:0>2X}')
                              #_LOGGER.warn("Eletrificador   %s", f'{data[54]:0>2X}')
                              if '00' in f'{data[85]:0>2X}':
                                 #_LOGGER.warn("com particao 01 nao configurada")
                                 self._attr_state = STATE_ALARM_DISARMED
                                 self.alarm_sounding = False
                                 self.fire_alarm = False
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '01' in f'{data[85]:0>2X}':
                                 #_LOGGER.warn("com particao 01 Desarmada pronta sem disparo")
                                 self.alarm_sounding = False
                                 self.fire_alarm = False
                                 self._attr_state = STATE_ALARM_DISARMED
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '02' in f'{data[85]:0>2X}':
                                 #_LOGGER.warn("com particao 01 Armada sem disparo")
                                 self.fire_alarm = False
                                 self.alarm_sounding = False
                                 self._attr_state = STATE_ALARM_ARMED_AWAY
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '03' in f'{data[85]:0>2X}':
                                 #_LOGGER.warn("com particao 01 Armada HOME sem disparo")
                                 self.alarm_sounding = False
                                 self.fire_alarm = False
                                 self._attr_state = STATE_ALARM_ARMED_HOME
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '04' in f'{data[85]:0>2X}':
                                 #_LOGGER.warn("com particao 01 Desarmada nao pronta e sem disparo")
                                 self._attr_state = STATE_ALARM_DISARMED
                                 self.alarm_sounding = False
                                 self.fire_alarm = False
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '81' in f'{data[85]:0>2X}':
                                 #_LOGGER.warn("Desarmada em disparo")
                                 self.alarm_sounding = True
                                 self.fire_alarm = True
                                 self._attr_state = STATE_ALARM_DISARMED
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '82' in f'{data[85]:0>2X}':
                                 #_LOGGER.warn("armada em disparo")
                                 self.alarm_sounding = True
                                 self.fire_alarm = True
                                 self._attr_state = STATE_ALARM_ARMED_AWAY
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '83' in f'{data[85]:0>2X}':
                                 #_LOGGER.warn("Armada Stay em disparo")
                                 self._attr_state = STATE_ALARM_ARMED_HOME
                                 self.alarm_sounding = True
                                 self.fire_alarm = True
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
                              elif '84' in f'{data[85]:0>2X}':
                                 #_LOGGER.warn("Desarmada pronta e em disparo")
                                 self.alarm_sounding = True
                                 self.fire_alarm = True
                                 self._attr_state = STATE_ALARM_DISARMED
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  


                              #_LOGGER.warn("Estado da particao -01  %s", f'{data[85]:0>2X}')
                              #_LOGGER.warn("Estado da particao -02  %s", f'{data[86]:0>2X}')
                              #_LOGGER.warn("Estado da particao -03  %s", f'{data[87]:0>2X}')
                              #_LOGGER.warn("Estado da particao -04  %s", f'{data[88]:0>2X}')
                              #_LOGGER.warn("Estado da particao -05  %s", f'{data[89]:0>2X}')
                              #_LOGGER.warn("Estado da particao -06  %s", f'{data[90]:0>2X}')
                              #_LOGGER.warn("Estado da particao -07  %s", f'{data[91]:0>2X}')
                              #_LOGGER.warn("Estado da particao -08  %s", f'{data[92]:0>2X}')
                              #_LOGGER.warn("Estado da particao -09  %s", f'{data[93]:0>2X}')
                              #_LOGGER.warn("Estado da particao -10  %s", f'{data[94]:0>2X}')
                              #_LOGGER.warn("Estado da particao -11  %s", f'{data[95]:0>2X}')
                              #_LOGGER.warn("Estado da particao -12  %s", f'{data[96]:0>2X}')
                              #_LOGGER.warn("Estado da particao -13  %s", f'{data[97]:0>2X}')
                              #_LOGGER.warn("Estado da particao -14  %s", f'{data[98]:0>2X}')
                              #_LOGGER.warn("Estado da particao -07  %s", f'{data[99]:0>2X}')
                              #_LOGGER.warn("Estado da particao -08  %s", f'{data[100]:0>2X}')
                              dispatcher_send(self.hass, CONF_MODELO, MODELO)    
                              message = b'\x7B\7\x01\x21\x01\x01'
                              check = self.checksum(message)
                              message += check.to_bytes(1,'big')
                              #_LOGGER.warn('Send Accept')
                              conn.send(bytes(message))
                              ##envia pedido de Status
                              message = b'\x7b\5\x01\x4d'
                              check = self.checksum(message)
                              message += check.to_bytes(1,'big')
                              #_LOGGER.warn('Envia pedido de Status')
                              conn.send(bytes(message))
                           if len(data)==5:
                              message = b'\x7B\6\x01\x40\x01'
                              check = self.checksum(message)
                              message += check.to_bytes(1,'big')
                              #_LOGGER.warn('Send Keep')
                              #_LOGGER.warn(message)
                              conn.send(bytes(message))
                      if time.time()-t>20:
                         t=time.time()
                         message = b'\x7b\5\x01\x4d'
                         check = self.checksum(message)
                         message += check.to_bytes(1,'big')
                         conn.send(bytes(message))
                      dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
 
        
