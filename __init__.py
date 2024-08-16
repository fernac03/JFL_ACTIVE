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
from homeassistant.helpers import device_registry as dr


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
        self.eletrificador=False
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
        return ( ((1 << k) - 1)  &  (number >> (p-1) ) )
    def setPartitionStatus(self,part,status):
        if status =="00":
           return
        elif status =="01":
           if self._attr_state != STATE_ALARM_DISARMED:
              _LOGGER.warn('status  particao desarmado') 
              #self._attr_state = STATE_ALARM_DISARMED
              #self.alarm_sounding = False
              #self.fire_alarm = False
              #dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)  
        elif status == "02":
           if ((self._attr_state != STATE_ALARM_ARMED_AWAY) and (self._attr_state != STATE_ALARM_ARMED_HOME)) :
              _LOGGER.warn('status  particao armado')
              #self._attr_state = STATE_ALARM_
              #_LOGGER.warn(self._attr_state)
           # return
        elif status == "03":
           if self._attr_state != STATE_ALARM_ARMED_HOME:
              _LOGGER.warn('status  particao  Armado Home')
              #_LOGGER.warn(self._attr_state)
           #return
        elif status == "04":
           if self._attr_state != STATE_ALARM_DISARMED:
              _LOGGER.warn('status  particao  Disarmado')
           #return
        elif status =="81":
           if self._attr_state != STATE_ALARM_TRIGGERED:
              _LOGGER.warn('status  particao desarmado disparado')
           #return
        elif status =="82":
           if self._attr_state != STATE_ALARM_TRIGGERED:
              _LOGGER.warn('status  particao  Armado Away e disparado')
           #return
        elif status =="83":
           if self._attr_state != STATE_ALARM_TRIGGERED:
              _LOGGER.warn('status particao Armado Home  e disparado')
           #return
        elif status =="84":
           if self._attr_state != STATE_ALARM_TRIGGERED:
              _LOGGER.warn('status  particao desarmado e disparado')
           #return
        else:
           _LOGGER.warn('status particao desarmado')
        return           
    def setZoneStatus(self,zone,status):
        if status == 0:
             return
        elif status == 1:
             return
        elif status == 2:
             dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, zone)
             self.text = "Zona " + str(zone) + " Zona Disparada"
             dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
        elif status == 3:
             self.text = "Zona " + str(zone) + " Sensor sem Comunicacao"
        elif status == 4:
             self.text = "Zona " + str(zone) + " Zona Em curto"
        elif status == 5:
             self.text = "Zona " + str(zone) + " Tamper Aberto"
        elif status == 6:
             self.text = "Zona " + str(zone) + " Bateria Baixa"
        elif status == 7:
             dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, zone)
             self.text = "Zona " + str(zone) + " Zona Aberta"
             dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
        elif status == 8:
             dispatcher_send(self.hass, SIGNAL_ZONE_RESTORE, zone)
        return

    def run(self):
        """Open a connection to JFL Active."""
        device_registry = dr.async_get(self.hass)
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
             elapsed=time.time()
             with conn:
                 _LOGGER.warn("Connected by %s",addr)
                 self.text = "Connected"
                 t=time.time()
                 while True:
                     if (time.time() - elapsed) >180:
                        #_LOGGER.warn("inicio do loop conectado  tempo: %s", time.time() - elapsed )
                        #_LOGGER.warn("fim to tempo de conexao")
                        conn.close()
                        break
                     sequencial += 1  
                     if sequencial > 255:
                        sequencial=1
                      
                     if not queue1.empty():
                        val = queue1.get()
                        sent = conn.send(val)
                     if sequencial % 5 ==0:
                        message = b'\x7B\5\x02\x4D'
                        check = self.checksum(message)
                        message += check.to_bytes(1,'big')
                        conn.send(bytes(message))
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
                        _LOGGER.warn('timeout lendata 0')
                        conn.close()
                        break
                      else:
                        ##_LOGGER.info("dentro da conexao recebido %s" %(data))
                        ####evento
                        #_LOGGER.warn("tamanho do Pacote %s",len(data))
                        if len(data)==5:
                            message = b'\x7B\6\x01\x40\x01'
                            check = self.checksum(message)
                            message += check.to_bytes(1,'big')
                            elapsed=time.time()
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
                            elif 'A8' in f'{data[41]:0>2X}':
                               MODELO = 'Active 8W'
                            elif '4B' in f'{data[41]:0>2X}':
                               MODELO = 'M-300+'
                            elif '5D' in f'{data[41]:0>2X}':
                               MODELO = 'm-300 Flex'
                            self.CONF_MODELO = MODELO
                            MAC=data[29:41].decode("utf-8")
                            NS = data[4:14].decode('ascii')
                            dispatcher_send(self.hass, CONF_MODELO, MODELO)    
                            ####Status######
                            _LOGGER.warn("Modelo da central  %s", MODELO)
                            _LOGGER.warn("Problema da central  %s", f'{data[50]:0>2X}')
                            _LOGGER.warn("Total de particoes  %s", f'{data[51]:0>2X}')
                            _LOGGER.warn("###############  PART %s ", CONF_PARTITION)
                            if '01' in f'{data[51]:0>2X}':
                               self.CONF_PARTITION=False
                               self.CONF_PARTITION = False
                               dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                            else:
                               self.CONF_PARTITION=True
                               self.CONF_PARTITION = True
                               dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)  
                               
                            dispatcher_send(self.hass, CONF_PARTITION, CONF_PARTITION)    
                            #_LOGGER.warn("Conta  %s", f'{data[52]:0>2X}')
                            #_LOGGER.warn("Conta  %s", f'{data[53]:0>2X}')
                            #_LOGGER.warn("Eletrificador   %s", f'{data[54]:0>2X}')
                            if '00' in f'{data[54]:0>2X}':
                              self.eletrificador=False
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
                            else:
                              self.eletrificador=True
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
                            #_LOGGER.warn("pacote com 102 Eletrificador   %s", f'{data[54]:0>2X}')
                            for i in range(16):
                              Part=i+1
                              #_LOGGER.warn("###############  PART %s Status %s", Part,f'{data[85+i]:0>2X}')
                              self.setPartitionStatus(Part,f'{data[85+i]:0>2X}')  
                            
                            message = b'\x7B\7\x01\x21\x01\x01'
                            check = self.checksum(message)
                            message += check.to_bytes(1,'big')
                            #_LOGGER.warn('Send Accept')
                            conn.send(bytes(message))
                            ##envia pedido de Status
                            message = b'\x7b\5\x01\x4d'
                            check = self.checksum(message)
                            message += check.to_bytes(1,'big')
                            _LOGGER.warn('Envia pedido de Status')
                            elapsed=time.time()
                            conn.send(bytes(message))
                        if len(data) ==24:
                           evento = data[8:12].decode('ascii')
                           if evento == "3441" :
                              self.armed_away = False
                              self.armed_night = False
                              self.armed_home = True
                              self._attr_state = STATE_ALARM_ARMED_HOME
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
                           if evento == '3401' or evento == '3407' or evento =='3403' or evento =='3404' or evento =='3408' or evento=='3409' :
                              self.armed_away = False
                              self.armed_night = False
                              self.armed_home = True
                              self._attr_state = STATE_ALARM_ARMED_AWAY
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == '1401' or evento =='1407' or evento =='1403' or evento=='1409':
                              _LOGGER.warn("Evento  %s", evento)
                              self.armed_home =False
                              self.armed_away =False
                              self.armed_night =False
                              self.alarm_sounding = False
                              self.fire_alarm = False
                              self._attr_state = STATE_ALARM_DISARMED
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == '1130' and self.armed_home == True:
                              self.fire_alarm=True
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self) 
                           if evento == '1130' and self.armed_away == True:
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
                           if evento == '1407':
                              self.eletrificador=True
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
                           if evento == '3407:
                              self.eletrificador=False
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
                           LOGGER.warn("Eventos=%s", evento)
                           message = b'\x7b\x0a\x01\x24\x01'
                           message += bytes({data[17]})
                           message += bytes({data[18]})
                           message += bytes({data[19]})
                           message += bytes({data[20]})
                           check = self.checksum(message)
                           message += check.to_bytes(1,'big')
                           _LOGGER.warn('Send ACK ')
                           elapsed=time.time()
                           conn.send(bytes(message))
                        if len(data) >= 118:
                           #_LOGGER.warn("pacote 118")
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
                           _LOGGER.debug("PGM  %s", data[13])
                           ### status das particoes
                           for i in range(16):
                              Part=i+1
                              _LOGGER.debug("###############  PART %s Status %s", Part,f'{data[13+i]:0>2X}')
                              self.setPartitionStatus(Part,f'{data[13+i]:0>2X}')
                           ### Status eletrificador
                           #_LOGGER.warn("Eletrificador %s", f'{data[30]:0>2X}')
                           if '00' in f'{data[30]:0>2X}':
                              self.eletrificador=False
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
                           else:
                              _LOGGER.debug("pacote com 118 Eletrificador %s", f'{data[30]:0>2X}')
                              self.eletrificador=True
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
                           #### Status das zonas
                           zona=1
                           for i in range(50):
                               high, low = data[31+i] >>4, data[31+i] & 0x0F
                               for x in range(1,3):
                                  if x ==1:
                                     _LOGGER.debug("###############  Zona %s Status %s", zona,high)
                                     self.setZoneStatus(zona,high)
                                     zona += 1  
                                  else:
                                     _LOGGER.debug("###############  Zona %s Status %s", zona,low)
                                     self.setZoneStatus(zona,low)
                                     zona +=1
                           elapsed=time.time() 
                        if len(data) >120: 
                           _LOGGER.info("pacote maior que 118 %s" %(data))  
                        
                        #message = b'\x7B\5\x01\x4D'
                        #check = self.checksum(message)
                        #message += check.to_bytes(1,'big')
                        #if val==0:
                        #   conn.send(bytes(message)) 
                        if (time.time() - t) >35:
                           t=time.time()
                           message = b'\x7b\5\x01\x4d'
                           check = self.checksum(message)
                           message += check.to_bytes(1,'big')
                           conn.send(bytes(message))
                           _LOGGER.warn("Envia pedido de status  apos tempo")
              
             _LOGGER.warn("fim do loop while true")
