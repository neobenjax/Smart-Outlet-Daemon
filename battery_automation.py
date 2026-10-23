import psutil
from pyHS100 import SmartPlug
import time
import os
import sys
import argparse

# --- Configuración y Versión ---
__version__ = "1.1.0"
PLUG_IP = "10.0.0.17"  # ¡IMPORTANTE! Reemplaza con la IP de tu HS100
UMBRAL_BAJO = 30  # Porcentaje de batería para encender
UMBRAL_ALTO = 60  # Porcentaje de batería para apagar (puedes poner 100 si quieres)
INTERVALO_VERIFICACION = 120  # Segundos entre cada verificación de batería (ej. 60 = 1 minuto)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "battery_automation.log") # Archivo para registrar acciones

def log_action(message):
    """Escribe un mensaje en el archivo de log."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} - {message}\n")
    if sys.stdout is not None:
        try:
            print(message)
        except Exception:
            pass

def get_battery_info():
    """Obtiene el porcentaje de batería y si está conectado a la corriente."""
    battery = psutil.sensors_battery()
    if battery:
        return battery.percent, battery.power_plugged
    return None, None

def get_plug_state(plug):
    """Obtiene el estado actual del enchufe (True si encendido, False si apagado)."""
    try:
        return plug.state == "ON"
    except Exception as e:
        log_action(f"Error al obtener el estado del enchufe: {e}")
        return None # Indicar que no se pudo obtener el estado

def turn_on_plug(plug):
    """Enciende el enchufe."""
    try:
        plug.turn_on()
        log_action("Enchufe encendido exitosamente.")
        return True
    except Exception as e:
        log_action(f"Error al encender el enchufe: {e}")
        return False

def turn_off_plug(plug):
    """Apaga el enchufe."""
    try:
        plug.turn_off()
        log_action("Enchufe apagado exitosamente.")
        return True
    except Exception as e:
        log_action(f"Error al apagar el enchufe: {e}")
        return False

def toggle_plug(plug):
    """Alterna el estado del enchufe (si está encendido lo apaga, y viceversa)."""
    state = get_plug_state(plug)
    if state is None:
        log_action("No se pudo determinar el estado actual para alternar el enchufe.")
        return False
    if state:
        log_action("El enchufe está encendido. Apagando...")
        return turn_off_plug(plug)
    else:
        log_action("El enchufe está apagado. Encendiendo...")
        return turn_on_plug(plug)

def show_status(plug):
    """Muestra el estado del enchufe y de la batería."""
    percent, plugged = get_battery_info()
    plug_state = get_plug_state(plug)
    plug_str = "ENCENDIDO (ON)" if plug_state is True else ("APAGADO (OFF)" if plug_state is False else "DESCONOCIDO")
    log_action(f"Estado actual -> Batería: {percent}%, Conectado a CA: {plugged}, Enchufe HS100: {plug_str}")

def main_automation():
    """Función principal de automatización."""
    log_action("Iniciando la automatización de la batería...")
    try:
        plug = SmartPlug(PLUG_IP)
        log_action(f"Conectado al enchufe TP-Link en {PLUG_IP}")
    except Exception as e:
        log_action(f"Error al inicializar el enchufe: {e}. Asegúrate de que la IP es correcta y el enchufe está en línea.")
        return # Salir si no se puede conectar al enchufe

    # Bucle principal de monitoreo
    while True:
        percent, plugged = get_battery_info()

        if percent is None:
            log_action("No se pudo obtener la información de la batería. Verificando de nuevo en un minuto.")
            time.sleep(INTERVALO_VERIFICACION)
            continue

        current_plug_state = get_plug_state(plug)

        if current_plug_state is None: # Si no se pudo obtener el estado del enchufe, intentar de nuevo
            time.sleep(INTERVALO_VERIFICACION)
            continue

        log_action(f"Batería: {percent}%, Conectado a CA: {plugged}, Enchufe HS100 Encendido: {current_plug_state}")

        # Lógica para encender el cargador
        if percent <= UMBRAL_BAJO and not plugged and not current_plug_state:
            log_action(f"Batería ({percent}%) por debajo del umbral de encendido ({UMBRAL_BAJO}%) y desconectado de CA. Encendiendo cargador...")
            turn_on_plug(plug)

        # Lógica para apagar el cargador
        elif percent >= UMBRAL_ALTO and plugged and current_plug_state:
            log_action(f"Batería ({percent}%) por encima del umbral de apagado ({UMBRAL_ALTO}%) y conectado a CA. Apagando cargador...")
            turn_off_plug(plug)

        # Si la batería está por encima del umbral bajo y ya está cargando, o por debajo del alto y no está cargando,
        # no hace falta hacer nada, solo esperar al siguiente ciclo.
        elif percent > UMBRAL_BAJO and percent < UMBRAL_ALTO and plugged and current_plug_state:
            log_action(f"Cargando. Batería: {percent}%. Esperando al umbral de apagado.")

        elif percent <= UMBRAL_ALTO and not plugged and current_plug_state:
            log_action(f"Laptop cargando pero desconectada de CA. Bateria: {percent}%")

        time.sleep(INTERVALO_VERIFICACION)

def main():
    parser = argparse.ArgumentParser(
        description="Automatización de batería y control manual del enchufe inteligente TP-Link HS100."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--on", action="store_true", help="Enciende el enchufe inmediatamente.")
    group.add_argument("--off", action="store_true", help="Apaga el enchufe inmediatamente.")
    group.add_argument("--toggle", action="store_true", help="Alterna el estado del enchufe (on/off).")
    group.add_argument("--status", action="store_true", help="Muestra el estado actual del enchufe y de la batería.")
    group.add_argument("--daemon", action="store_true", help="Inicia el monitoreo pasivo de batería (predeterminado).")

    args = parser.parse_args()

    if args.on or args.off or args.toggle or args.status:
        try:
            plug = SmartPlug(PLUG_IP)
        except Exception as e:
            log_action(f"Error al conectar con el enchufe en {PLUG_IP}: {e}")
            sys.exit(1)

        if args.on:
            success = turn_on_plug(plug)
            sys.exit(0 if success else 1)
        elif args.off:
            success = turn_off_plug(plug)
            sys.exit(0 if success else 1)
        elif args.toggle:
            success = toggle_plug(plug)
            sys.exit(0 if success else 1)
        elif args.status:
            show_status(plug)
            sys.exit(0)
    else:
        # Modo por defecto o explícito --daemon: bucle continuo de monitoreo
        main_automation()

if __name__ == "__main__":
    main()
