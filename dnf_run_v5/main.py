import sys
from PyQt5.QtWidgets import QApplication
from gui import GameAutomationWindow
sys.stdout.reconfigure(encoding='utf-8')

def main():
    app = QApplication(sys.argv)
    main_window = GameAutomationWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()