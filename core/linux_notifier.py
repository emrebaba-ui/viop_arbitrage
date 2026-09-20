import subprocess

class LinuxNotifier:
    def __init__(self):
        self.sound_path = '/usr/share/sounds/freedesktop/stereo/message.oga'

    def send(self, title: str, message: str):
        subprocess.Popen(
            ['notify-send', title, message, '-u', 'critical', '-i', 'dialog-warning'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        try:
            subprocess.Popen(['paplay', self.sound_path], 
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except Exception:
            pass