# main.py - Responsible for launching the application
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit
from PyQt5.QtGui import QPixmap
import sys, os
from uibuilder import CircuitBuilderWindow #Import the circuit builder window from uibuilder.py

class HomeWindow(QWidget):
    def __init__(self):
        super().__init__()
        #Set up homescreen
        self.setWindowTitle("HomeScreen")
        mainlayout = QVBoxLayout() #Define layout of window

        #Define header layout
        header = QHBoxLayout()
        #Define logo labels
        epic_logo_label = QLabel()
        meche_logo_label = QLabel()
        #Load logos onto label
        epic_pixmap = QPixmap("assets/homescreen/epiclogo.png")
        meche_pixmap = QPixmap("assets/homescreen/mechelogo.png")

        epic_logo_label.setPixmap(epic_pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        meche_logo_label.setPixmap(meche_pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        #Set label for lab name
        title_label = QLabel("ADML - BUMES")
        title_label.setStyleSheet("font-size: 100px; font-weight: bold;")

        #Add the logos and the lab name to the header
        header.addWidget(epic_logo_label, alignment=Qt.AlignLeft)
        header.addWidget(title_label, alignment=Qt.AlignCenter)
        header.addWidget(meche_logo_label, alignment=Qt.AlignRight)

        #Add header to main layout of window and align to top
        mainlayout.addLayout(header)
        mainlayout.setAlignment(header, Qt.AlignTop)

        #Add app name label
        app_label = QLabel("CIRCUIT BUILDER")
        app_label.setStyleSheet("font-size: 100px; font-weight: bold;")

        #Add app name label to layout of window
        mainlayout.addWidget(app_label, alignment = Qt.AlignCenter)
        mainlayout.addSpacing(100) #Add spacing

        #Define button row layout
        button_row = QHBoxLayout()

        #Instantiate new button
        new_button = QPushButton("NEW")
        new_button.setFixedWidth(200) #Set width of button
        new_button.clicked.connect(lambda: self.open_builder(False)) #Call open_builder function w/o loading enabled on click

        #Instantiate load button
        load_button = QPushButton("LOAD")
        load_button.setFixedWidth(200) #Set width of button
        load_button.clicked.connect(lambda: self.open_builder(True)) #Call open_builder function with loading enabled on click

        #Instantiate close button
        close_button = QPushButton("CLOSE")
        close_button.setFixedWidth(200) #Set width of button
        close_button.clicked.connect(self.close) #Call close function on click

        button_row.addStretch() #Adds empty space before new button
        button_row.addWidget(new_button) #Add new button to button row layout
        button_row.addWidget(load_button) #Add load button to button row layout
        button_row.addWidget(close_button) #Add close button to button row layout
        button_row.addStretch() #Adds empty space after close button

        mainlayout.addLayout(button_row) #Add button_row layout to main layout of window

        #Add an inputfield for loading file/project
        self.loadfileinputfield = QLineEdit()
        self.loadfileinputfield.setStyleSheet("font-size: 20px; padding: 10px;") #Add style (font size, text colour, etc)
        self.loadfileinputfield.setPlaceholderText("Enter filename to load...")
        self.loadfileinputfield.setFixedWidth(610) #Set width

        self.loadfilewarningtext = QLabel()
        self.loadfilewarningtext.setStyleSheet("color: red;")

        bottomlayout = QVBoxLayout()
        bottomlayout.addWidget(self.loadfileinputfield, alignment= Qt.AlignCenter) #Add inputfield widget to mainlayout
        bottomlayout.addWidget(self.loadfilewarningtext, alignment= Qt.AlignCenter)

        mainlayout.addLayout(bottomlayout)
        mainlayout.setAlignment(bottomlayout, Qt.AlignTop)
        self.setLayout(mainlayout) #Set mainlayout as the window's layout

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint) #Make window borderless
        self.showFullScreen() #Make window fullscreen

        self.working_dir = os.getcwd()
        self.load_folder = r"saves"
        self.load_folderpath = os.path.join(self.working_dir, self.load_folder)

    def open_builder(self, load):
        if (load):
            if self.loadfileinputfield.text() == "":
                self.loadfilewarningtext.setText("ENTER FILENAME")
                return
            elif self.loadfileinputfield.text():
                filename = self.loadfileinputfield.text() + ".json"
                fullpath = os.path.join(self.load_folderpath, filename)

                if not os.path.exists(fullpath):
                    self.loadfilewarningtext.setText("FILE NOT FOUND")
                    return
                else:
                    self.loadfilewarningtext.setStyleSheet("color: black;")
                    self.loadfilewarningtext.setText(f"LOADING: {fullpath}")
                    QTimer.singleShot(2000, lambda: self.delay(fullpath))
        else:
            self.builder = CircuitBuilderWindow() #Instantiate an object to load circuit builder window i.e. the workspace/workarea
            self.builder.show() #Display the workspace window
            self.close() #Close homescreen window

    def delay(self, path):
        self.loadfilewarningtext.setStyleSheet("color: red;")
        self.loadfilewarningtext.setText("")
        self.builder = CircuitBuilderWindow() #Instantiate an object to load circuit builder window i.e. the workspace/workarea
        self.builder.show() #Display the workspace window
        self.builder.loadprojfile(path)
        self.close() #Close homescreen window

if __name__ == '__main__':
    app = QApplication(sys.argv) #Start application
    window = HomeWindow() #Instantiate object to set up home window
    window.show() #Show home window
    sys.exit(app.exec_()) #close app when instructed