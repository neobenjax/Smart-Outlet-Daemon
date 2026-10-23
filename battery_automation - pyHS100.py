import psutil
from pyHS100 import SmartPlug
import time
import os

# --- Configuración ---
PLUG_IP = "10.0.0.17"  # ¡IMPORTANTE! Reemplaza con la IP de tu HS100
UMBRAL_BAJO = 30  # Porcentaje de batería para encender
UMBRAL_ALTO = 60  # Porcentaje de batería para apagar (puedes poner 100 si quieres)
INTERVALO_VERIFICACION = 120  # Segundos entre cada verificación de batería (ej. 60 = 1 minuto)
LOG_FILE = "battery_automation.log" # Archivo para registrar acciones

def log_action(message):
    """Escribe un mensaje en el archivo de log."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} - {message}\n")
    print(message) # También imprime en consola para depuración

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
            try:
                plug.turn_on()
                log_action("Cargador encendido.")
            except Exception as e:
                log_action(f"Error al encender el cargador: {e}")

        # Lógica para apagar el cargador
        elif percent >= UMBRAL_ALTO and plugged and current_plug_state:
            log_action(f"Batería ({percent}%) por encima del umbral de apagado ({UMBRAL_ALTO}%) y conectado a CA. Apagando cargador...")
            try:
                plug.turn_off()
                log_action("Cargador apagado.")
            except Exception as e:
                log_action(f"Error al apagar el cargador: {e}")

        # Si la batería está por encima del umbral bajo y ya está cargando, o por debajo del alto y no está cargando,
        # no hace falta hacer nada, solo esperar al siguiente ciclo.
        elif percent > UMBRAL_BAJO and percent < UMBRAL_ALTO and plugged and current_plug_state:
            log_action(f"Cargando. Batería: {percent}%. Esperando al umbral de apagado.")

        elif percent <= UMBRAL_ALTO and not plugged and current_plug_state:
            log_action(f"Laptop cargando pero desconectada de CA. Bateria: {percent}%")


        time.sleep(INTERVALO_VERIFICACION)

if __name__ == "__main__":
    main_automation()
