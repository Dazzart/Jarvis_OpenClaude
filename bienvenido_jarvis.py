#!/usr/bin/env python3
"""
Double-clap welcome script for Señor Tatay.

Detects 2 claps → voz AI dice bienvenido → abre YouTube → Claude + Cursor lado a lado.

Dependencias:
    pip install sounddevice numpy pyttsx3

Uso:
    python bienvenido_tatay.py
"""

import os
import platform
import shutil
import sys
import time
import threading
import subprocess
import webbrowser

import numpy as np
import sounddevice as sd
import pyttsx3

# ──────────────────────────────────────────────────────────────────────────────
#  Configuración
# ──────────────────────────────────────────────────────────────────────────────
SAMPLE_RATE    = 44100
BLOCK_SIZE     = int(SAMPLE_RATE * 0.05)   # 50 ms por bloque
THRESHOLD      = 0.00035  # RMS mínimo para contar como aplauso  ← ajusta si falla
COOLDOWN       = 0.08   # segundos de pausa mínima entre aplausos
DOUBLE_WINDOW  = 3.5     # ventana de tiempo para el segundo aplauso
CALIBRATION_TIME = 3.0   # segundos para calibrar el nivel de ruido inicial
MIN_THRESHOLD   = 0.00008 # umbral mínimo seguro para micrófonos silenciosos

YOUTUBE_URL    = "https://www.youtube.com/watch?v=hEIexwwiKKU"
MENSAJE        = "Bienvenido a casa, señor Michael."
NEW_PROJECT    = os.path.join(os.path.expanduser("~"), "Desktop", "nuevo_proyecto") if sys.platform.startswith("win") else os.path.expanduser("~/Desktop/nuevo_proyecto")
IS_WINDOWS     = sys.platform.startswith("win")
IS_MAC         = sys.platform == "darwin"

# ──────────────────────────────────────────────────────────────────────────────
#  Estado global
# ──────────────────────────────────────────────────────────────────────────────
clap_times: list[float] = []
triggered = False
lock = threading.Lock()


# ──────────────────────────────────────────────────────────────────────────────
#  Detección de aplausos
# ──────────────────────────────────────────────────────────────────────────────
def audio_callback(indata, frames, time_info, status):
    global triggered, clap_times

    if triggered:
        return

    rms = float(np.sqrt(np.mean(indata ** 2)))
    now = time.time()

    peak = float(np.max(np.abs(indata)))
    if rms > THRESHOLD or peak > THRESHOLD * 4:
        with lock:
            # Ignora si estamos en el cooldown del aplauso anterior
            if clap_times and (now - clap_times[-1]) < COOLDOWN:
                return

            clap_times.append(now)
            # Limpia aplausos fuera de la ventana
            clap_times = [t for t in clap_times if now - t <= DOUBLE_WINDOW]

            count = len(clap_times)
            print(f"  👏  Aplauso {count}/2  (RMS={rms:.5f}, pico={peak:.5f})")

            if count >= 2:
                triggered = True
                clap_times = []
                threading.Thread(target=secuencia_bienvenida, daemon=True).start()


# ──────────────────────────────────────────────────────────────────────────────
#  Secuencia de bienvenida
# ──────────────────────────────────────────────────────────────────────────────
def secuencia_bienvenida():
    print("\n🚀  Iniciando secuencia de bienvenida…\n")

    hablar(MENSAJE)
    abrir_youtube()
    abrir_apps_lado_a_lado()

    print("\n✅  Secuencia completada.\n")


def hablar(texto: str):
    """TTS local con pyttsx3 (usa voces del sistema, sin API key)."""
    print(f"  🔊  Diciendo: «{texto}»")

    if IS_MAC:
        resultado = subprocess.run(
            ["say", "-v", "Monica", texto],
            capture_output=True
        )
        if resultado.returncode == 0:
            return  # éxito con Monica (voz española de macOS)

    # Fallback: pyttsx3
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")

    # Busca voz en español
    esp = [v for v in voices if "es" in v.id.lower() or "spanish" in v.name.lower()]
    if esp:
        engine.setProperty("voice", esp[0].id)
        print(f"     Voz seleccionada: {esp[0].name}")
    else:
        print("     Usando voz por defecto (no se encontró voz en español)")

    engine.setProperty("rate", 148)
    engine.say(texto)
    engine.runAndWait()


def abrir_youtube():
    print(f"  🎵  Abriendo YouTube…")
    webbrowser.open(YOUTUBE_URL)
    time.sleep(1.2)  # deja que el navegador cargue antes de seguir


def abrir_apps_lado_a_lado():
    sw, sh = obtener_resolucion_pantalla()
    mitad = sw // 2

    # Asegura que existe la carpeta del nuevo proyecto
    os.makedirs(NEW_PROJECT, exist_ok=True)

    # ── Abre Claude ──────────────────────────────────────────────────────────
    print("  🤖  Abriendo Claude…")
    if IS_WINDOWS:
        if not ejecutar_app_windows("Claude"):
            print("     No se encontró Claude en PATH, abriendo web...")
            webbrowser.open("https://claude.ai")
    else:
        subprocess.Popen(["open", "-a", "Claude"])
    time.sleep(1.8)

    # ── Abre Cursor con nuevo proyecto ───────────────────────────────────────
    print("  💻  Abriendo Cursor…")
    cursor_cmd = encontrar_cursor()
    if cursor_cmd:
        subprocess.Popen([cursor_cmd, NEW_PROJECT])
    elif IS_WINDOWS:
        print("     No se encontró Cursor en PATH, abriendo carpeta de proyecto")
        os.startfile(NEW_PROJECT)
    else:
        subprocess.Popen(["open", "-a", "Cursor", NEW_PROJECT])
    time.sleep(1.8)

    # ── Organiza ventanas solo en macOS ───────────────────────────────────────
    if IS_WINDOWS:
        print("  🪟  Organización de ventanas no soportada en Windows desde este script.")
        return

    print("  🪟  Organizando ventanas…")
    applescript = f"""
    tell application "System Events"
        try
            tell process "Claude"
                set frontmost to true
                set position of window 1 to {{0, 0}}
                set size of window 1 to {{{mitad}, {sh}}}
            end tell
        end try
        try
            tell process "Cursor"
                set frontmost to true
                set position of window 1 to {{{mitad}, 0}}
                set size of window 1 to {{{mitad}, {sh}}}
            end tell
        end try
    end tell
    """
    subprocess.run(["osascript", "-e", applescript], capture_output=True)


def ejecutar_app_windows(nombre: str) -> bool:
    """Intenta ejecutar una app por nombre o ruta en Windows."""
    exe = shutil.which(nombre) or shutil.which(f"{nombre}.exe")
    if exe:
        subprocess.Popen([exe])
        return True
    return False


# ──────────────────────────────────────────────────────────────────────────────
#  Utilidades
# ──────────────────────────────────────────────────────────────────────────────
def obtener_resolucion_pantalla() -> tuple[int, int]:
    if IS_WINDOWS:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except Exception:
            return 1920, 1080

    try:
        out = subprocess.run(
            ["osascript", "-e",
             "tell application \"Finder\" to get bounds of window of desktop"],
            capture_output=True, text=True
        ).stdout.strip()
        parts = [int(x.strip()) for x in out.split(",")]
        return parts[2], parts[3]
    except Exception:
        return 1920, 1080


def encontrar_cursor():
    """Devuelve la ruta del CLI de Cursor si está disponible."""
    if IS_WINDOWS:
        exe = shutil.which("cursor") or shutil.which("cursor.exe")
        return exe

    candidatos = [
        "/usr/local/bin/cursor",
        "/opt/homebrew/bin/cursor",
        os.path.expanduser("~/.cursor/bin/cursor"),
    ]
    for path in candidatos:
        if os.path.isfile(path):
            return path
    # Intenta por PATH
    result = subprocess.run(["which", "cursor"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def calibrar_umbral(dispositivo: int | None) -> float:
    if dispositivo is None:
        return THRESHOLD

    print("  🧪 Calibrando umbral de aplauso...")
    rms_values: list[float] = []

    def callback(indata, frames, time_info, status):
        rms_values.append(float(np.sqrt(np.mean(indata ** 2))))

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=1,
            dtype="float32",
            callback=callback,
            device=dispositivo,
        ):
            time.sleep(CALIBRATION_TIME)
    except Exception as exc:
        print(f"     Error de calibración: {exc}")
        return THRESHOLD

    if not rms_values:
        return THRESHOLD

    ruido_promedio = float(np.mean(rms_values))
    ruido_mediana = float(np.median(rms_values))
    ruido_90 = float(np.percentile(rms_values, 90))
    ruido_maximo = float(max(rms_values))
    nuevo_umbral = max(
        MIN_THRESHOLD,
        ruido_mediana * 20.0,
        ruido_90 * 2.5,
    )
    print(
        f"    ruido promedio={ruido_promedio:.6f}, ruido mediana={ruido_mediana:.6f}, "
        f"90%={ruido_90:.6f}, ruido máximo={ruido_maximo:.6f}, umbral={nuevo_umbral:.6f}"
    )
    return nuevo_umbral


def obtener_dispositivo_predeterminado() -> int | None:
    try:
        default_dev = sd.default.device
        if isinstance(default_dev, tuple):
            return default_dev[0]
        return default_dev
    except Exception:
        return None


def listar_dispositivos_entrada() -> None:
    print("  Dispositivos de entrada disponibles:")
    try:
        dispositivos = sd.query_devices()
    except Exception as exc:
        print(f"     No se pudo listar dispositivos: {exc}")
        return

    default_input = obtener_dispositivo_predeterminado()
    for idx, dev in enumerate(dispositivos):
        if dev.get("max_input_channels", 0) > 0:
            predeterminado = " (predeterminado)" if idx == default_input else ""
            print(f"    {idx}: {dev['name']} - {dev['max_input_channels']} canales{predeterminado}")


def seleccionar_dispositivo(argv: list[str]) -> int | None:
    if len(argv) < 2:
        return None
    try:
        dispositivo = int(argv[1])
        if dispositivo < 0:
            raise ValueError
        return dispositivo
    except ValueError:
        print(f"  Índice de dispositivo inválido: {argv[1]}.")
        print("  Usa: python bienvenido_jarvis.py <indice_de_dispositivo>")
        sys.exit(1)


def print_diagnostics():
    print("  Nota: el script necesita un micrófono activo. Si usas solo audífonos sin micrófono, no detectará el aplauso.")
    print("  Si tienes un micrófono válido, ejecuta con su índice: python bienvenido_jarvis.py 1")
    listar_dispositivos_entrada()


# ──────────────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    global triggered

    dispositivo_seleccionado = seleccionar_dispositivo(sys.argv)
    dispositivo_default = obtener_dispositivo_predeterminado()

    print("=" * 55)
    print("  🎤  Escuchando aplausos… (Ctrl+C para salir)")
    if dispositivo_seleccionado is not None:
        print(f"  Usando dispositivo de entrada: {dispositivo_seleccionado}")
    elif dispositivo_default is not None:
        print(f"  Usando dispositivo de entrada predeterminado: {dispositivo_default}")
    print("=" * 55)
    print_diagnostics()

    dispositivo_actual = dispositivo_seleccionado if dispositivo_seleccionado is not None else dispositivo_default
    calibrated_threshold = calibrar_umbral(dispositivo_actual)
    global THRESHOLD
    THRESHOLD = calibrated_threshold
    print(f"  Umbral calibrado: {THRESHOLD:.6f}")

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=1,
            dtype="float32",
            callback=audio_callback,
            device=dispositivo_seleccionado if dispositivo_seleccionado is not None else dispositivo_default,
        ):
            while True:
                time.sleep(0.1)
                if triggered:
                    # Espera a que la secuencia acabe y vuelve a escuchar
                    time.sleep(8)
                    triggered = False
                    print("\n👂  Escuchando de nuevo…\n")
    except KeyboardInterrupt:
        print("\n\nHasta luego! 👋")
        sys.exit(0)


if __name__ == "__main__":
    main()
