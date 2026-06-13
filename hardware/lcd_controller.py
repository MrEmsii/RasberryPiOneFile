# hardware/lcd_controller.py
# Author: Emsii (refactored)
# CONSUMER — subskrybuje LCD_ON/LCD_OFF i wyświetla dane z AppState.
# Nie wie nic o IR, temperaturze, pogodzie — tylko odczytuje stan i wyświetla.

import time
import datetime
import logging
import threading
from typing import Optional

try:
    from gpiozero import CPUTemperature
    import psutil
    HW_AVAILABLE = True
except ImportError:
    HW_AVAILABLE = False

from core.events import bus, Event, EventType
from core.state import state

logger = logging.getLogger(__name__)


def _remove_accents(text: str) -> str:
    """Usuń polskie znaki — uproszczona wersja z Another.py."""
    strange = 'ŮôῡΒძěἊἦëĐᾇόἶἧзвŅῑἼźἓŉἐÿἈΌἢὶЁϋυŕŽŎŃğûλВὦėἜŤŨîᾪĝžἙâᾣÚκὔჯᾏᾢĠфĞὝŲŊŁČῐЙῤŌὭŏყἀхῦЧĎὍОуνἱῺèᾒῘᾘὨШūლἚύсÁóĒἍŷöὄЗὤἥბĔõὅῥŋБщἝξĢюᾫაπჟῸდΓÕűřἅгἰშΨńģὌΥÒᾬÏἴქὀῖὣᾙῶŠὟὁἵÖἕΕῨčᾈķЭτἻůᾕἫжΩᾶŇᾁἣჩαἄἹΖеУŹἃἠᾞåᾄГΠКíōĪὮϊὂᾱიżŦИὙἮὖÛĮἳφᾖἋΎΰῩŚἷРῈĲἁéὃσňİΙῠΚĸὛΪᾝᾯψÄᾭêὠÀღЫĩĈμΆᾌἨÑἑïოĵÃŒŸζჭᾼőΣŻçųøΤΑËņĭῙŘАдὗპŰἤცᾓήἯΐÎეὊὼΘЖᾜὢĚἩħĂыῳὧďТΗἺĬὰὡὬὫÇЩᾧñῢĻᾅÆßшδòÂчῌᾃΉᾑΦÍīМƒÜἒĴἿťᾴĶÊΊȘῃΟúχΔὋŴćŔῴῆЦЮΝΛῪŢὯнῬũãáἽĕᾗნᾳἆᾥйᾡὒსᾎĆрĀüСὕÅýფᾺῲšŵкἎἇὑЛვёἂΏθĘэᾋΧĉᾐĤὐὴιăąäὺÈФĺῇἘſგŜæῼῄĊἏØÉПяწДĿᾮἭĜХῂᾦωთĦлðὩზკίᾂᾆἪпἸиᾠώᾀŪāоÙἉἾρаđἌΞļÔβĖÝᾔĨНŀęᾤÓцЕĽŞὈÞუтΈέıàᾍἛśìŶŬȚĳῧῊᾟάεŖᾨᾉςΡმᾊᾸįᾚὥηᾛġÐὓłγľмþᾹἲἔбċῗჰხοἬŗŐἡὲῷῚΫŭᾩὸùᾷĹēრЯĄὉὪῒᾲΜᾰÌœĥტ'
    ascii_r  = 'UoyBdeAieDaoiiZVNiIzeneyAOiiEyyrZONgulVoeETUiOgzEaoUkyjAoGFGYUNLCiIrOOoqaKyCDOOUniOeiIIOSulEySAoEAyooZoibEoornBSEkGYOapzOdGOuraGisPngOYOOIikoioIoSYoiOeEYcAkEtIuiIZOaNaicaaIZEUZaiIaaGPKioIOioaizTIYIyUIifiAYyYSiREIaeosnIIyKkYIIOpAOeoAgYiCmAAINeiojAOYzcAoSZcuoTAEniIRADypUitiiIiIeOoTZIoEIhAYoodTIIIaoOOCSonyKaAsSdoACIaIiFIiMfUeJItaKEISiOuxDOWcRoiTYNLYTONRuaaIeinaaoIoysACRAuSyAypAoswKAayLvEaOtEEAXciHyiiaaayEFliEsgSaOiCAOEPYtDKOIGKiootHLdOzkiaaIPIIooaUaOUAIrAdAKlObEYiINleoOTEKSOTuTEeiaAEsiYUTiyIIaeROAsRmAAiIoiIgDylglMtAieBcihkoIrOieoIYuOouaKerYAOOiaMaIoht'
    try:
        from utils.text import remove_accents
        return remove_accents(text)
    except ImportError:
        return text


class LCDController:
    """
    Kontroler LCD 20x4.

    Subskrybuje LCD_ON → zaczyna wyświetlać.
    Subskrybuje LCD_OFF → gasi podświetlenie.

    Wyświetla sekwencję: Czas → Temperatura → Pogoda → Stats PC
    Dane pochodzi z AppState — nigdy z bezpośrednich wywołań sensorów.
    """

    def __init__(self):
        self._lcd = None
        self._display_thread: Optional[threading.Thread] = None
        self._stop_display = threading.Event()
        self._setup_hardware()
        self._register()

    def _setup_hardware(self) -> None:
        try:
            # API_LCD_I2C.py leży w folderze hardware/ obok tego pliku
            from hardware import API_LCD_I2C
            self._lcd = API_LCD_I2C.lcd()
            logger.info("LCD hardware initialized")
        except ImportError:
            try:
                # Fallback: plik leży w głównym katalogu projektu (oryginalna lokalizacja)
                import API_LCD_I2C
                self._lcd = API_LCD_I2C.lcd()
                logger.info("LCD hardware initialized (root path)")
            except ImportError:
                logger.warning("API_LCD_I2C not found — LCD disabled")
        except Exception:
            logger.exception("LCD hardware init failed")

    def _register(self) -> None:
        bus.subscribe(EventType.LCD_ON,  self._on_lcd_on)
        bus.subscribe(EventType.LCD_OFF, self._on_lcd_off)

    # ── Handlery zdarzeń ─────────────────────────────────

    def _on_lcd_on(self, event: Event) -> None:
        stop_at: datetime.datetime = event.payload.get("stop_at")
        if self._display_thread and self._display_thread.is_alive():
            logger.debug("LCD already running")
            return

        self._stop_display.clear()
        self._display_thread = threading.Thread(
            target=self._display_loop,
            args=(stop_at,),
            name="LCD-Display",
            daemon=True,
        )
        self._display_thread.start()
        logger.info(f"LCD ON until {stop_at}")

    def _on_lcd_off(self, event: Event) -> None:
        self._stop_display.set()
        if self._lcd:
            self._lcd.lcd_clear()
            self._lcd.backlight(0)
        logger.info("LCD OFF")

    # ── Pętla wyświetlania ───────────────────────────────

    def _display_loop(self, stop_at: Optional[datetime.datetime]) -> None:
        """
        Sekwencja stron LCD.
        i parzyte → czas
        i % 6 == 1 → temperatura
        i % 6 == 3 → pogoda
        i % 6 == 5 → statystyki PC
        """
        segment_wait = 3  # sekundy na segment

        if self._lcd:
            self._lcd.backlight(1)

        i = 0
        while not self._stop_display.is_set():
            if stop_at and datetime.datetime.now() >= stop_at:
                break

            try:
                if i % 2 == 0:
                    self._page_time(segment_wait)
                elif i % 6 == 1:
                    self._page_temperature(segment_wait)
                elif i % 6 == 3:
                    self._page_weather()
                elif i % 6 == 5:
                    self._page_pc_stats(segment_wait)

                i += 1
                if self._lcd:
                    self._lcd.lcd_clear()

            except Exception:
                logger.exception("LCD display error")
                time.sleep(1)

        if self._lcd:
            self._lcd.lcd_clear()
            self._lcd.backlight(0)

    # ── Strony LCD ───────────────────────────────────────

    def _page_time(self, wait: float) -> None:
        if not self._lcd:
            return
        self._lcd.lcd_display_string_pos(
            "Data: " + str(datetime.date.today()), 3, 2
        )
        steps = int(wait / 0.2)
        for _ in range(steps):
            if self._stop_display.is_set():
                break
            clock = datetime.datetime.now()
            self._lcd.lcd_display_string_pos(
                "Time: " + clock.strftime("%H:%M:%S"), 2, 2
            )
            time.sleep(0.2)

    def _page_temperature(self, wait: float) -> None:
        if not self._lcd:
            return
        temp = state.get_temperature()
        self._lcd.lcd_display_string_pos("Temperature:", 1, 4)

        room = f" Room = {temp.indoor}\u00dfC " if temp.indoor is not None else " Room = --\u00dfC "
        self._lcd.lcd_display_string_pos(room, 2, 4)

        outdoor = f" OutDoor = {temp.outdoor}\u00dfC " if temp.outdoor is not None else " OutDoor = --\u00dfC "
        self._lcd.lcd_display_string_pos(outdoor, 3, 1)

        steps = int(wait / 0.7)
        for _ in range(steps):
            if self._stop_display.is_set():
                break
            if HW_AVAILABLE:
                cpu_temp = str(CPUTemperature().temperature)[:4]
            else:
                cpu_temp = "--"
            self._lcd.lcd_display_string_pos(f" RaspPI = {cpu_temp}\u00dfC ", 4, 2)
            time.sleep(0.7)

    def _page_weather(self) -> None:
        if not self._lcd:
            return
        w = state.get_weather()

        city_display = _remove_accents(w.city)
        self._lcd.lcd_display_string_pos(city_display, 1, max(0, (20 - len(city_display)) // 2))
        self._lcd.lcd_display_string_pos(w.temp_outside, 3, max(0, (20 - len(w.temp_outside)) // 2))

        press_hum = f"{w.current_humidity} {w.current_pressure}"
        self._lcd.lcd_display_string_pos(press_hum, 4, max(0, (20 - len(press_hum)) // 2))

        # Scrollujący opis pogody
        info = " " * 10 + _remove_accents(w.info_weather) + " " * 10
        for i in range(max(0, len(info) - 20)):
            if self._stop_display.is_set():
                break
            self._lcd.lcd_display_string(info[i:i + 20], 2)
            time.sleep(0.4)

    def _page_pc_stats(self, wait: float) -> None:
        if not self._lcd or not HW_AVAILABLE:
            return
        net = state.get_network()

        self._lcd.lcd_display_string_pos("CPU   RAM   DISK", 1, 3)
        self._lcd.lcd_display_string_pos("0.0%   0.0%  0.0%", 2, 2)
        self._lcd.lcd_display_string_pos(net.ip_query, 3, max(0, (20 - len(net.ip_query)) // 2) - 1)
        self._lcd.lcd_display_string_pos(net.ip_home, 4, max(0, (20 - len(net.ip_home)) // 2) - 1)

        self._lcd.lcd_display_string_pos(f'{psutil.virtual_memory().percent}%', 2, 8)
        self._lcd.lcd_display_string_pos(f'{psutil.disk_usage("/").percent}%', 2, 15)

        steps = int(wait * 2)
        for _ in range(steps):
            if self._stop_display.is_set():
                break
            self._lcd.lcd_display_string_pos(f'{psutil.cpu_percent(interval=0.3)}%', 2, 2)
            time.sleep(0.4)