# uibuilder.py
import os, json, datetime, subprocess, trimesh
import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QPushButton, QWidget, QDialog,
    QHBoxLayout, QLabel, QLineEdit, QComboBox, QScrollArea, QWidget, QGridLayout
)
from PyQt5.QtGui import QDoubleValidator, QPixmap, QValidator
from viewer import OpenGLViewer #Import OpenGL Viewer from viewer.py

class CircuitBuilderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.homewindow = None
        self.selectedobjpath = None
        self.setWindowTitle("WorkspaceScreen") #Set window title

        self.initUI() #Call initUI to setup UI for window

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint) #Make window borderless
        self.showFullScreen() #Make window fullscreen

    def initUI(self):
        self.components = []
        self.stock_model_data = None
        #Header UI
        self.header = QWidget()
        #Header UI Variables
        self.dropdown = QComboBox()
        self.dropdown.addItems(["MENU", "ADD", "SAVE", "UPLOAD"])
        self.dropdown.currentTextChanged.connect(self.on_dropdown_changed)
        app_title_label = QLabel("CIRCUIT BUILDER")
        home_button = QPushButton("HOME")
        home_button.clicked.connect(self.go_home)
        close_button = QPushButton("CLOSE")
        close_button.clicked.connect(self.to_close)

        #Header UI Layout
        header_layout = QHBoxLayout(self.header)
        header_layout.addWidget(self.dropdown)
        header_layout.addWidget(app_title_label)
        header_layout.addStretch()
        header_layout.addWidget(home_button)
        header_layout.addWidget(close_button)

        #Disable & Hide Header Widget - initially
        self.header.hide()
        self.header.setEnabled(False)

        #Stock Dimensions UI
        self.stockdimensionsui = QWidget()
        #Stock Dimensions UI Variables
        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("ENTER LENGTH OF STOCK IN INCHES...")
        self.length_input.setValidator(QDoubleValidator(0.0, 10000.0, 2))
        self.length_input.textChanged.connect(self.update_stock_dims)
        self.width_input = QLineEdit()
        self.width_input.setPlaceholderText("ENTER WIDTH OF STOCK IN INCHES...")
        self.width_input.setValidator(QDoubleValidator(0.0, 10000.0, 2))
        self.width_input.textChanged.connect(self.update_stock_dims)
        self.height_input = QLineEdit()
        self.height_input.setPlaceholderText("ENTER HEIGHT OF STOCK IN INCHES...")
        self.height_input.setValidator(QDoubleValidator(0.0, 10000.0, 2))
        self.height_input.textChanged.connect(self.update_stock_dims)
        self.warningstockdimuitext = QLabel()
        self.warningstockdimuitext.setStyleSheet("color: red;")
        submit_button = QPushButton("SUBMIT")
        submit_button.clicked.connect(self.generate_stock)
        home_button = QPushButton("HOME")
        home_button.clicked.connect(self.go_home)

        #Stock Dimensions UI Layout
        dim_layout = QHBoxLayout(self.stockdimensionsui)
        dim_layout.addWidget(QLabel("Length (in):"))
        dim_layout.addWidget(self.length_input)
        dim_layout.addWidget(QLabel("Width (in):"))
        dim_layout.addWidget(self.width_input)
        dim_layout.addWidget(QLabel("Height (in):"))
        dim_layout.addWidget(self.height_input)
        dim_layout.addWidget(self.warningstockdimuitext)
        dim_layout.addWidget(submit_button)
        dim_layout.addWidget(home_button)

        #Save UI Variables/ UI Components
        self.closeproj = False
        self.savefile = False
        self.goback = False
        self.uploadfile = False
        self.saveUI = QWidget()
        self.savefile_inputfield = QLineEdit()
        self.savefile_inputfield.setPlaceholderText("ENTER FILENAME TO SAVE...")
        self.savewarningtext = QLabel()
        self.savewarningtext.setStyleSheet("color: red;")
        save_button = QPushButton("SAVE")
        save_button.clicked.connect(self.to_save)
        back_button = QPushButton("BACK")
        back_button.clicked.connect(self.go_back)

        #Save UI Layout
        save_layout = QHBoxLayout(self.saveUI)
        save_layout.addWidget(self.savefile_inputfield)
        save_layout.addWidget(self.savewarningtext)
        save_layout.addWidget(save_button)
        save_layout.addWidget(back_button)

        self.saveUI.hide()
        self.saveUI.setEnabled(False)

        self.working_dir = os.getcwd()
        self.save_folder = r"saves"
        self.save_folderpath = os.path.join(self.working_dir, self.save_folder)

        #Save Confirm UI
        self.saveconfirmtext = QLabel()
        self.saveconfirmtext.setStyleSheet("color: black;")
        self.saveconfirmtext.hide()
        self.saveconfirmtext.setEnabled(False)

        #Position Set UI
        self.position_ui = QWidget()
        self.currentposx = QLabel()
        self.currentposx.setStyleSheet("border: 2px solid black;")
        self.currentposy = QLabel()
        self.currentposy.setStyleSheet("border: 2px solid black;")
        self.posoffset_x_in = QLineEdit()
        self.posoffset_x_in.setPlaceholderText("Enter offset from current position in x axis")
        self.posoffset_y_in = QLineEdit()
        self.posoffset_y_in.setPlaceholderText("Enter offset from current position in y axis")
        self.posoffsetvaliditytext = QLabel()
        self.posoffsetvaliditytext.setStyleSheet("color: red;")
        self.last_validator_scales = (None,None)

        self.previewposbutton = QPushButton("Preview Position")
        self.previewposbutton.clicked.connect(self.apply_position_change)

        self.setposbutton = QPushButton("Set Position")
        self.setposbutton.clicked.connect(self.submitpos)

        pos_ui_layout = QHBoxLayout(self.position_ui)
        pos_ui_layout.addWidget(self.currentposx)
        pos_ui_layout.addWidget(self.currentposy)
        pos_ui_layout.addWidget(QLabel("X_offset (in): "))
        pos_ui_layout.addWidget(self.posoffset_x_in)
        pos_ui_layout.addWidget(QLabel("Y_offset (in): "))
        pos_ui_layout.addWidget(self.posoffset_y_in)
        pos_ui_layout.addWidget(self.posoffsetvaliditytext)
        pos_ui_layout.addWidget(self.previewposbutton)
        pos_ui_layout.addWidget(self.setposbutton)

        self.position_ui.hide()
        self.position_ui.setEnabled(False)

        #Confirm selection UI
        self.selectedtext = QLabel("Select objects before pressing M")
        self.selectedtext.setStyleSheet("color: red;")
        self.selectedtext.hide()
        self.selectedtext.setEnabled(False)

        #WorkSpace UI
        self.viewer = OpenGLViewer()

        #Full Window Layout
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(self.header, alignment = Qt.AlignTop)
        layout.addWidget(self.stockdimensionsui, alignment = Qt.AlignTop)
        layout.addWidget(self.saveUI, alignment = Qt.AlignTop)
        layout.addWidget(self.saveconfirmtext, alignment = Qt.AlignTop)
        layout.addWidget(self.position_ui, alignment = Qt.AlignTop)
        layout.addWidget(self.selectedtext, alignment = Qt.AlignTop)

        layout.addWidget(self.viewer, stretch = 1)

        #Full Window UI
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        #Load default stock (1in x 1in x 1in)
        self.viewer.stock_available(1.0, 1.0, 1.0)

    def loadprojfile(self,path):
        self.stockdimensionsui.hide() #hide stock dimensions UI
        self.stockdimensionsui.setEnabled(False) #disable stock dimensions UI
        self.header.show() #unhide header
        self.header.setEnabled(True) #make header interactable
        with open(path, "r") as f:
            data = json.load(f)

        for component in data['componentdata']:
            if component['modelName'] == "stock":
                self.viewer.stock_available(component['dimX'], component['dimY'], component['dimZ'])
                self.stock_model_data = component
            else:
                self.viewer.load_model(component['modelName'])
                for model in self.viewer.loadedmodels:
                    if model['name'] == component['modelName']:
                        transformed_meshes = []
                        for mesh in model['meshes']:
                            mesh.apply_translation([component['posX'], component['posY'], 0])
                            transformed_meshes.append(mesh)
                        model['meshes'] = transformed_meshes
                        model['position'] = [component['posX'], component['posY'], 1]
                        angle_radians = np.radians(component['rotZ'])
                        rotation_matrix = trimesh.transformations.rotation_matrix(
                            angle_radians,
                            direction={'x': [1,0,0], 'y':[0,1,0], 'z':[0,0,-1]}['z'],
                            point=model['position']
                        )
                        transformed_meshes = []
                        for mesh in model['meshes']:
                            mesh.apply_transform(rotation_matrix)
                            transformed_meshes.append(mesh)
                        model['meshes'] = transformed_meshes
                        model['rotation'] = [0,0,component['rotZ']]

        self.viewer.wiredata = data['wiresdata']
        for wire in data['wiresdata']:
            for nodedata in wire['wireNodesdata']:
                self.viewer.wirenodesdata.append(nodedata)

        self.viewer.stockdrawn = True
        self.viewer.update()

    def go_home(self): #On home button click
        from main import HomeWindow
        self.homewindow = HomeWindow()
        self.close()

    def to_close(self):
        self.closeproj = True
        self.header.hide()
        self.header.setEnabled(False)
        self.saveUI.show()
        self.saveUI.setEnabled(True)

    def to_save(self):
        self.savefile = True
        self.save_file()

    def go_back(self):
        self.goback = True
        self.save_file()

    def save_file(self):
        f3ds_folder = r"assets\f3ds"
        full_f3d_folder = os.path.join(self.working_dir, f3ds_folder)
        os.makedirs(self.save_folderpath, exist_ok=True)

        save_data = {'componentdata': [], 'wiresdata': []}

        if not self.goback and self.savefile:
            self.components.clear()
            self.savefile = False
            if (self.savefile_inputfield.text() == ""):
                self.savewarningtext.setText("ENTER FILENAME")
            else:
                currentdatetime = datetime.datetime.now().strftime("%m-%d-%Y-%H%M%S")
                savefilename = self.savefile_inputfield.text() + f"-{currentdatetime}.json"
                savefilepath = os.path.join(self.save_folderpath, savefilename)
                self.savewarningtext.setText("")
                self.components.append(self.stock_model_data)
                for model in self.viewer.loadedmodels:
                    f3dpath = os.path.splitext(os.path.basename(model['name']))[0] + ".f3d"
                    fullf3dpath = os.path.join(full_f3d_folder, f3dpath)
                    self.components.append({'modelName': model['name'], 'f3dName': fullf3dpath,
                                                'posX':model['position'][0], 'posY':model['position'][1],
                                                'dimX': 0, 'dimY': 0, 'dimZ': 0,
                                                'rotX': model['rotation'][0], 'rotY': model['rotation'][1], 'rotZ': model['rotation'][2]})


                save_data['componentdata'] = self.components
                save_data['wiresdata'] = self.viewer.wiredata

                with open(savefilepath, "w") as f:
                    json.dump(save_data, f, indent=4)

                self.saveUI.hide()
                self.saveUI.setEnabled(False)
                self.header.hide()
                self.header.setEnabled(False)
                self.saveconfirmtext.show()
                self.saveconfirmtext.setEnabled(True)
                self.saveconfirmtext.setText(f"SAVED TO: {savefilepath}")
                QTimer.singleShot(2000, self.delay)

        elif self.goback:
            self.saveUI.hide()
            self.saveUI.setEnabled(False)
            self.header.show()
            self.header.setEnabled(True)
            self.goback = False
            self.savefile = False
            self.closeproj = False
            self.savewarningtext.setText("")
            if self.dropdown.findText("MENU") != -1:
                    self.dropdown.setCurrentIndex(self.dropdown.findText("MENU"))


    def delay(self):
        self.saveconfirmtext.setText("")
        self.saveconfirmtext.hide()
        self.saveconfirmtext.setEnabled(False)

        if self.uploadfile:
            fusion_path = r"C:\Users\dwara\AppData\Local\Autodesk\webdeploy\production\6a0c9611291d45bb9226980209917c3d\FusionLauncher.exe"
            if os.path.exists(fusion_path):
                subprocess.Popen([fusion_path])
            else:
                print("Fusion doesn't exist in path")
            self.uploadfile = False

        if self.closeproj:
            self.closeproj = False
            self.go_home()

        if self.dropdown.findText("MENU") != -1:
            self.dropdown.setCurrentIndex(self.dropdown.findText("MENU"))

    def on_dropdown_changed(self,text): #On dropdown option selected
        if text == "ADD":
            self.load_component()
        elif text == "SAVE":
            self.header.hide()
            self.header.setEnabled(False)
            self.position_ui.hide()
            self.position_ui.setEnabled(False)
            self.saveUI.show()
            self.saveUI.setEnabled(True)
        elif text == "UPLOAD":
            self.uploadfile = True
            self.header.hide()
            self.header.setEnabled(False)
            self.position_ui.hide()
            self.position_ui.setEnabled(False)
            self.saveUI.show()
            self.saveUI.setEnabled(True)
        elif text == "MENU":
            self.saveUI.hide()
            self.saveUI.setEnabled(False)
            self.position_ui.hide()
            self.position_ui.setEnabled(False)
            self.header.show()
            self.header.setEnabled(True)

    def update_stock_dims(self): #On inputfield/stock dimensions values changed
        self.warningstockdimuitext.setText("")
        try:
            length = float(self.length_input.text())
        except ValueError:
            length = 1.0

        try:
            width = float(self.width_input.text())
        except ValueError:
            width = 1.0

        try:
            height = float(self.height_input.text())
        except ValueError:
            height = 1.0

        self.viewer.stock_available(length, width, height)

    def generate_stock(self): #On submit button clicked to submit stock dimensions
        if(self.length_input.text() != "" and self.width_input.text() != "" and self.height_input.text() != ""): #check if all dimensions entered
            self.stockdimensionsui.hide() #hide stock dimensions UI
            self.stockdimensionsui.setEnabled(False) #disable stock dimensions UI
            self.header.show() #unhide header
            self.header.setEnabled(True) #make header interactable
            #Add stock to components data
            if not any(component.get('modelName') == "stock" for component in self.components):
                self.components.append({'modelName': "stock", 'f3dName': "stock.f3d",
                                            'posX': -float(self.length_input.text())/2, 'posY': -float(self.width_input.text())/2,
                                            'dimX': float(self.length_input.text()), 'dimY': float(self.width_input.text()), 'dimZ': float(self.height_input.text()),
                                            'rotX': 0.0, 'rotY': 0.0, 'rotZ': 0.0})
            self.stock_model_data = self.components[0]
            self.viewer.stockdrawn = True
            self.update_offset_validators()
        else:
           self.warningstockdimuitext.setText("ENTER ALL DIMENSIONS")

    def load_component(self): #load component
        menu = Selection(self)
        if menu.exec_() == QDialog.Accepted:
            print(self.selectedobjpath)
            self.viewer.load_model(self.selectedobjpath)
            if self.dropdown.findText("MENU") != -1:
                self.dropdown.setCurrentIndex(self.dropdown.findText("MENU"))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_M and self.viewer.stockdrawn:
            self.header.hide()
            self.header.setEnabled(False)
            self.saveUI.hide()
            self.saveUI.setEnabled(False)
            position = self.get_selected_position()
            if position == None:
                self.position_ui.hide()
                self.position_ui.setEnabled(False)
                self.selectedtext.show()
                self.selectedtext.setEnabled(True)
                QTimer.singleShot(1000, self.submitpos)
            else:
                self.selectedtext.hide()
                self.selectedtext.setEnabled(False)
                self.position_ui.show()
                self.position_ui.setEnabled(True)

    def get_selected_position(self):
        if self.viewer.selected_model_indices:
            xpos = self.viewer.loadedmodels[self.viewer.selected_model_indices[-1]]['position'][0]
            ypos = self.viewer.loadedmodels[self.viewer.selected_model_indices[-1]]['position'][1]
            self.currentposx.setText(f"Current X Position: {str(xpos)}")
            self.currentposy.setText(f"Current Y Position: {str(ypos)}")
            return [xpos,ypos]
        elif self.viewer.selected_node_indices:
            xpos = self.viewer.wirenodesdata[self.viewer.selected_node_indices[-1]]['posX']
            ypos = self.viewer.wirenodesdata[self.viewer.selected_node_indices[-1]]['posY']
            self.currentposx.setText(f"Current X Position: {str(xpos)}")
            self.currentposy.setText(f"Current Y Position: {str(ypos)}")
            return [xpos,ypos]
        return None

    def update_offset_validators(self):
        self.posoffset_x_in.setValidator(QDoubleValidator(-self.stock_model_data['dimX'], self.stock_model_data['dimX'], 2))
        self.posoffset_y_in.setValidator(QDoubleValidator(-self.stock_model_data['dimY'], self.stock_model_data['dimY'], 2))

    def apply_position_change(self):
        if self.posoffset_x_in.validator().validate(self.posoffset_x_in.text(), 0)[0] != QValidator.Acceptable or self.posoffset_y_in.validator().validate(self.posoffset_y_in.text(), 0)[0] != QValidator.Acceptable:
            self.posoffsetvaliditytext.setText("Enter valid offset")
        else:
            self.posoffsetvaliditytext.setText("")
            try:
                xoff = float(self.posoffset_x_in.text())
                yoff = -float(self.posoffset_y_in.text())
            except:
                xoff = 0.0
                yoff = 0.0
                self.posoffsetvaliditytext.setText("Offset parse error")

            self.viewer.selected_position(xoff,yoff)
            self.get_selected_position()

    def submitpos(self):
        self.selectedtext.hide()
        self.selectedtext.setEnabled(False)
        self.position_ui.hide()
        self.position_ui.setEnabled(False)
        self.saveUI.hide()
        self.saveUI.setEnabled(False)
        self.position_ui.hide()
        self.position_ui.setEnabled(False)
        self.header.show()
        self.header.setEnabled(True)
        if self.viewer.selected_model_indices: #and not self.viewer.multiselect:
            self.viewer.selected_model_indices.clear()
            self.viewer.update()
        if self.viewer.selected_node_indices: # and not self.viewer.multiselect:
            self.viewer.selected_node_indices.clear()
            self.viewer.update()

class Selection(QDialog): #Load component menu - shows sall available components for selection
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle("Select Component")
        self.resize(600,600)

        #Define layout
        layout = QVBoxLayout(self)
        #Instantiate scrollarea widget
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        #define content and content layout
        scroll_content = QWidget()
        scroll_layout = QGridLayout(scroll_content)

        #Folder path to access all models(.objs), icons(.png), f3ds(.f3d) of the components
        model_folder = r"assets\models"
        icon_folder = r"assets\icons"

        #get current working directory
        working_dir = os.getcwd()

        current_row = 0
        current_column = 0
        max_columns = 3
        #Loop through each file in model_folder
        for filename in os.listdir(model_folder):
            if filename.lower().endswith(".obj"): #If file extension = .obj
                objfilepath = os.path.join(working_dir, model_folder)
                objfilepath = os.path.join(objfilepath, filename) #Obtain full obj file path
                btn = QPushButton() #Define a button
                btn.setFixedWidth(180)
                btn.setFixedHeight(180)
                btn.setStyleSheet("text-align: left; padding: 5px;")
                btn.clicked.connect(lambda _, c=os.path.splitext(filename)[0], f=objfilepath: self.component_clicked(c, f)) #call component_clicked on button click

                #Define button layout
                button_layout = QVBoxLayout()
                #Get icon path of current .obj file
                iconpath = os.path.join(working_dir, icon_folder)
                iconpath = os.path.join(iconpath, f"{os.path.splitext(filename)[0]}.png")
                #Load icon
                pixmap = QPixmap(iconpath)
                if not pixmap.isNull():
                    icon_scale_size = (120,120)
                    pixmap = pixmap.scaled(icon_scale_size[0], icon_scale_size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                #Set icon to label
                image_label = QLabel()
                image_label.setPixmap(pixmap)
                image_label.setFixedSize(icon_scale_size[0], icon_scale_size[1])
                image_label.setAlignment(Qt.AlignCenter)
                #Set name of component to name_label
                name_label = QLabel(os.path.splitext(filename)[0])
                name_label.setStyleSheet("font-size: 14px;")
                #Add labels to button_layout
                button_layout.addWidget(image_label, alignment=Qt.AlignCenter)
                button_layout.addStretch()
                button_layout.addWidget(name_label, alignment=Qt.AlignHCenter | Qt.AlignBottom)
                #Set button's layout to button_layout
                btn.setLayout(button_layout)

                scroll_layout.addWidget(btn, current_row, current_column) #Add button to scroll_layout/layout of content in current grid position
                #Update grid position
                current_column += 1
                if current_column >= max_columns:
                    current_column = 0
                    current_row += 1

        scroll_content.setLayout(scroll_layout) #set content widget's layout to scroll_layout
        scroll.setWidget(scroll_content) #Add content to scroll area

        layout.addWidget(scroll) #Add scroll area to main layout

    def component_clicked(self, component, objfilepath): #On component button clicked
        print(f"Selected component: {component}")
        self.parent().selectedobjpath = objfilepath
        self.accept()