"""Support for JFL Active20 devices."""
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
    """Set up JFL Active20 config flow."""
    undo_listener = entry.add_update_listener(_update_listener)

    ad_connection = entry.data

    def stop_alarmdecoder(event):
        """Handle the shutdown of JFL Active20."""
        if not hass.data.get(DOMAIN):
            return
        _LOGGER.debug("Shutting down JFL Active20")
        hass.data[DOMAIN][entry.entry_id][DATA_RESTART] = False
        _LOGGER.debug("Shutting down JFL Active20")
        
    async def open_connection():
        """Open a connection to JFL Active20."""
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
    """Unload a JFL Active20 entry."""
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
    _LOGGER.debug("JFL Active20 options updated: %s", entry.as_dict()["options"])
    await hass.config_entries.async_reload(entry.entry_id)


class JFLWatcher(threading.Thread):
    """Event listener thread to process NX584 events."""

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

    def bitExtracted(self, number, k, p):
        return ( ((1 << k) - 1)  &  (number >> (p-1) ) );

    def run(self):
        """Open a connection to JFL Active20."""
        _LOGGER.warn("Starting JFL Integration")
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
        self.battery_low = True
        self.check_zone = False
        self.chime_on = True
        self.CONF_PARTITION = False
        self.entry_delay_off = False
        self.programming_mode = False
        self.ready = True
        self.zone_bypassed = False
        device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with device as s:
           self.text = "Not Connected"
           dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)
           s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
           s.bind((self.host, self.port))
           s.listen()
           #s.setblocking(False)
           while True:  
             conn, addr = s.accept()
             with conn:
                 _LOGGER.warn("Connected by %s",addr)
                 self.text = "Connected"
                 t=time.time()
                 while True:
                     elapsed = 0
                     if not queue1.empty():
                        val = queue1.get()
                        sent = conn.send(val)
                     conn.settimeout(2)
                     try:
                       data = conn.recv(35)
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
                        if len(data) == 30 and '36'  in f'{data[0]:0>2X}':
                           if self.CONF_PARTITION:
                              if self.bitExtracted(data[7], 1, 2) == 1:
                                 _LOGGER.warn("com particao Part A Armada Stay")
                                 self._attr_state = STATE_ALARM_ARMED_HOME
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
                              else:
                                 _LOGGER.warn("com particao Part A Desarmada")
                                 self._attr_state = STATE_ALARM_DISARMED
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
                              if self.bitExtracted(data[7], 1, 3) == 1:
                                 _LOGGER.info("Part B Armada")
                                 #self._attr_state = STATE_ALARM_ARMED_AWAY
                                 #dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
                              else:
                                 _LOGGER.info("Part B Desarmada")
                                 #self._attr_state = STATE_ALARM_DISARMED
                                 #dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
                              if self.bitExtracted(data[7], 1, 4) == 1:
                                 _LOGGER.info("Part B Armada")
                                 #self._attr_state = STATE_ALARM_ARMED_AWAY
                                 #dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
                              else:
                                 _LOGGER.info("Part B Desarmada")
                                 #self._attr_state = STATE_ALARM_DISARMED
                                 #dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
                              
                           else:
                               if self.bitExtracted(data[7], 1, 1) == 1:
                                 #_LOGGER.warn("Central Armada")
                                 #_LOGGER.warn(STATE_ALARM_ARMED_HOME)
                                 self.armed_home = True
                                 self._attr_state = STATE_ALARM_ARMED_HOME
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
                               else:
                                 #_LOGGER.warn("Central Desarmada")
                                 self.armed_home = False
                                 self.armed_away = False
                                 self._attr_state = STATE_ALARM_DISARMED
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)       
                           for i in range(1,9):
                              if self.bitExtracted(data[1], 1, i) == 1:
                                 dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, i)
                                 self.text = "Zona " + str(i) + " Aberta"
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
                              else:
                                 dispatcher_send(self.hass, SIGNAL_ZONE_RESTORE, i)
                             
                              _LOGGER.info ("zona %s status %s (0-Fechada , 1 Aberta)", i ,self.bitExtracted(data[1], 1, i))
                              _LOGGER.info ("zona %s Habilitada %s (0-nao , 1 sim)", i ,self.bitExtracted(data[26], 1, i))
                           for i in range(10,17):
                              if self.bitExtracted(data[2], 1, i) == 1:
                                dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, i)
                                self.text = "Zona " + str(i) + " Aberta"
                                dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
                              else:
                                dispatcher_send(self.hass, SIGNAL_ZONE_RESTORE, i)

                              _LOGGER.info ("zona %s status %s (0-Fechada , 1 Aberta)", i ,self.bitExtracted(data[2], 1, i))
                              _LOGGER.info ("zona %s Habilitadas %s (0-nao , 1 sim)", i ,self.bitExtracted(data[27], 1, i))
                           for i in range(18,21):
                              if self.bitExtracted(data[3], 1, i) == 1:
                                 dispatcher_send(self.hass, SIGNAL_ZONE_FAULT, i)
                                 self.text = "Zona " + str(i) + " Aberta"
                                 dispatcher_send(self.hass,SIGNAL_PANEL_MESSAGE, self)    
                              else:
                                 dispatcher_send(self.hass, SIGNAL_ZONE_RESTORE, i)

                              _LOGGER.info ("zona %s status %s (0-Fechada , 1 Aberta)", i ,self.bitExtracted(data[3], 1, i))
                              _LOGGER.info ("zona %s Habilitada %s (0-nao , 1 sim)", i ,self.bitExtracted(data[28], 1, i))
                           
                           

                           if self.bitExtracted(data[7], 1, 5) == 1:
                              _LOGGER.info("PGM 1 Acionada")
                           else:
                              _LOGGER.info("PGM 1 Off")
                           if self.bitExtracted(data[7], 1, 6) == 1:
                              _LOGGER.info("PGM 2 acionada")
                           else:
                              _LOGGER.warn("PGM 2 off")
                           if self.bitExtracted(data[7], 1, 7) == 1:
                              _LOGGER.warn("PGM 3 acionada")
                           else:
                              _LOGGER.warn("PGM 3 off")
                           if self.bitExtracted(data[7], 1, 8) == 1:
                              _LOGGER.warn("PGM 4 Acionada")
                           else:
                              _LOGGER.info("PGM 4 Off")
                           #_LOGGER.warn("prob1  %s", f'{data[8]:0>2X}')
                           #_LOGGER.warn("prob2  %s", f'{data[9]:0>2X}')
                           #_LOGGER.warn("PERM1  %s", f'{data[10]:0>2X}')
                           #_LOGGER.warn("Permisssao zonas  %s", f'{data[11]:0>2X}')
                           if data[14] <= 0x96:
                              self.text = "Bateria Baixa"
                              self.battery_low = True
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if data[14] >= 0xBE:
                              self.text = "Bateria Normal"
                              self.battery_low = True
                              #_LOGGER.warn("texto %s", self.text)
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           #_LOGGER.warn("Nivel gprs  %s", f'{data[15]:0>2X}')
                           #_LOGGER.warn("data hora  %s", f'{data[16]:0>2X}')
                           #_LOGGER.warn("conta part a  %s", f'{data[22]:0>2X}')
                           #_LOGGER.warn("conta part b  %s", f'{data[24]:0>2X}')
                           #_LOGGER.warn("zonas Habilitadas  %s", f'{data[26]:0>2X}')

                        if chr(data[0]) == '!':
                           #_LOGGER.warn("Tipo Central  %s", f'{data[27]:0>2X}')
                           if 'A0' in f'{data[27]:0>2X}':
                              MODELO = 'Active-32 Duo'
                           elif 'A1' in f'{data[27]:0>2X}':
                              MODELO = 'Active 20 Ultra/GPRS'
                           elif 'A2' in f'{data[27]:0>2X}':
                              MODELO = 'Active 8 Ultra'
                           elif 'A3' in f'{data[27]:0>2X}':
                              MODELO = 'Active 20 Ethernet'
                           elif '06' in f'{data[27]:0>2X}':
                             MODELO = 'Active 20 Ethernet'
                           elif '05' in f'{data[27]:0>2X}':
                              MODELO = 'Active 20 Ultra'
                           elif '04' in f'{data[27]:0>2X}':
                              MODELO = 'Active 20 GPRS'
                           elif '00' in f'{data[27]:0>2X}':
                              MODELO = 'Active 20 GPRS'
                           self.CONF_MODELO = MODELO
                           dispatcher_send(self.hass, CONF_MODELO, MODELO)    
                           conn.send('+'.encode('ascii'))
                        elif chr(data[0]) == '@':
                              if time.time()-t>20:
                                 t=time.time()
                                 conn.send(b'\xb3\x36\x18\x00\x00\x00\x00\x9d')
                              else:                    
                                conn.send('@1'.encode('ascii'))
                        elif chr(data[0]) == '$':
                           evento = data[5:9].decode('ascii')
                           self.alarm_event_occurred = evento
                           if evento == 3401 or evento ==3407 or evento ==3403 or evento ==3404 or evento ==3408 or evento==3409 or evento==3441:
                              self.armed_away =False
                              self.armed_night =False
                              self.armed_home =True
                              self._attr_state = STATE_ALARM_ARMED_HOME
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                              _LOGGER.warn("Evento  %s", evento)
                           if evento == 1401 or evento ==1407 or evento ==1403 or evento==1409:
                              _LOGGER.warn("Evento  %s", evento)
                              self.armed_home =False
                              self.armed_away =False
                              self.armed_night =False
                              self._attr_state = STATE_ALARM_DISARMED
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == 1130 and self.armed_home == True:
                              self.fire_alarm=True
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == 3130:
                              self.fire_alarm=False
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == 1134 and self.armed_home == True:
                              self.fire_alarm=True
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == 3134:
                              self.fire_alarm=False
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == 1137 and self.armed_home == True:
                              self.fire_alarm=True
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if evento == 3137:
                              self.fire_alarm=False
                              dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           _LOGGER.warn("Evento  %s", evento)
                           if self.bitExtracted(data[15],1,6) ==1:
                             _LOGGER.info("Sistema Particionado %s",self.bitExtracted(data[15], 1, 6))
                             self.CONF_PARTITION = True
                             dispatcher_send(self.hass,CONF_PARTITION, True)    
                           else:
                             _LOGGER.info("Sistema sem Paticao %s",self.bitExtracted(data[15], 1, 6))
                             self.CONF_PARTITION = True
                             dispatcher_send(self.hass,CONF_PARTITION, True)
                           if self.CONF_PARTITION:
                              if self.bitExtracted(data[15],1,1) ==1:
                                 _LOGGER.info("Particao A Armada %s",self.bitExtracted(data[15], 1, 1))
                                # self._attr_state = STATE_ALARM_ARMED_HOME
                                 #self.armed_home = True
                              else:
                                 #self._attr_state = STATE_ALARM_DISARMED
                                 #self.armed_home = False
                                 _LOGGER.info("Particao A Desarmada %s",self.bitExtracted(data[15], 1, 1))
                              if self.bitExtracted(data[15],1,2) ==1:
                                 _LOGGER.info("Particao B Armada %s",self.bitExtracted(data[15], 1, 2))
                              else:
                                 #self._attr_state = STATE_ALARM_DISARMED
                                 _LOGGER.info("Particao B Desarmada %s",self.bitExtracted(data[15], 1, 2))
                           else:
                              if self.bitExtracted(data[15],1,1) ==1:
                                 #self._attr_state = STATE_ALARM_ARMED_HOME
                                 ##self.armed_away = False
                                 #self.armed_night = False
                                 ##self.armed_home = True
                                 #dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self) 
                                 _LOGGER.warn("Evento  %s", evento)                                 
                              else:
                                 #self._attr_state = STATE_ALARM_DISARMED
                                 ##self.armed_home = False
                                 #self.armed_away = False
                                 #self.armed_night = False
                                 #dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                                 _LOGGER.warn("Evento  %s", evento)
                           if self.bitExtracted(data[15],1,3) ==1:
                             _LOGGER.info("Problema Detectado %s",self.bitExtracted(data[15], 1, 3))
                           else:
                             _LOGGER.info("Sistema OK %s",self.bitExtracted(data[15], 1, 3))
                           if self.bitExtracted(data[15],1,4) ==1:
                             _LOGGER.info("Sirene Principal Tocando %s",self.bitExtracted(data[15], 1, 4))
                             self.alarm_sounding = True
                             dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           else:
                             self.alarm_sounding = False
                             _LOGGER.info("Sirene off %s",self.bitExtracted(data[15], 1, 4))
                             dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           if self.bitExtracted(data[15],1,5) ==1:
                             _LOGGER.info("Sirene B Tocando %s",self.bitExtracted(data[15], 1, 5))
                             self.alarm_sounding = True
                             dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           else:
                             self.alarm_sounding = False
                             dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                             _LOGGER.info("Sirene B off %s",self.bitExtracted(data[15], 1, 5))
                           
 
                           dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
                           conn.send('@1'.encode('ascii'))
                        else:
                              conn.send('@1'.encode('ascii'))
                              self.armed_away = False
 
                      dispatcher_send(self.hass, SIGNAL_PANEL_MESSAGE, self)    
 
        
