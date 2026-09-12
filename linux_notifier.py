import subprocess

class LinuxNotifier:
    def __init__(self):
        self.sound_path = '/usr/share/sounds/freedesktop/stereo/message.oga'

    def send(self, title: str, message: str):
        # critical flag
        subprocess.run(['notify-send', title, message, '-u', 'critical', '-i', 'dialog-warning'])
        
        try:
            subprocess.run(['paplay', self.sound_path], stderr=subprocess.DEVNULL)
        except Exception:
            pass