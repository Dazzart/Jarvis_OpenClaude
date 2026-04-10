# 👏 Jarvis - Double Clap Home Automation

Aplaude 2 veces y Jarvis te da la bienvenida, pone música y abre tus apps.

## ¿Qué hace?
1. Detecta 2 aplausos por el micrófono
2. Una voz dice **"Bienvenido a casa, señor Michael"**
3. Abre YouTube con tu canción
4. Abre **Claude** y **Cursor** lado a lado

## Instalación

```bash
pip install sounddevice numpy pyttsx3
```

## Uso

```bash
python bienvenido_jarvis.py
```

> Si no detecta los aplausos, ajusta `THRESHOLD` en el script (sube el valor si hay ruido, bájalo si no detecta).

## Requisitos
- Windows
- Python 3.9+
- Micrófono
