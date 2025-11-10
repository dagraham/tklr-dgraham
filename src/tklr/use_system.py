import os
import sys
import platform
import subprocess
import contextlib
import io
from importlib import resources
from pathlib import Path


def open_with_default(path: Path) -> None:
    path = Path(path).expanduser().resolve()
    system = platform.system()
    # Redirect stderr to capture any “Exception ignored” warnings
    output = io.StringIO()
    with contextlib.redirect_stderr(output):
        try:
            if system == "Darwin":
                subprocess.Popen(
                    ["open", str(path)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif system == "Windows":
                os.startfile(str(path))
            else:
                subprocess.Popen(
                    ["xdg-open", str(path)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception as e:
            print(f"Error opening {path}: {e}", file=sys.stderr)

        res = output.getvalue()
        if res:
            print(f"caught by redirect_stderr:\n'{res}'", file=sys.stderr)


def play_alert_sound(filename: str) -> None:
    """
    Play a short alert sound from the packaged tklr/sounds resource.
    :param filename: e.g., 'ding.mp3'
    """
    try:
        with resources.path("tklr.sounds", filename) as sound_path:
            p = sound_path
    except FileNotFoundError:
        print(f"⚠️ Sound file not found: {filename}", file=sys.stderr)
        return

    system = platform.system()
    # For macOS, prefer afplay (fast, no UI)
    if system == "Darwin":
        os.system(f"afplay {str(p)} &")
    # On Windows, you might rely on default
    elif system == "Windows":
        open_with_default(p)
    else:
        # On Linux, you might try to use default or a command-line player
        # Here we fallback to default open
        open_with_default(p)
