from kivy.app import App
from kivy.uix.label import Label


class MemoryVaultApp(App):
    def build(self):
        return Label(text="Memory Vault")


if __name__ == "__main__":
    MemoryVaultApp().run()
