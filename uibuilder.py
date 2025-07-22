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
        #Initialize data storage variables
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
        self.length_input.setValidator(QDoubleValidator(0.0, 10000.0, 4))
        self.length_input.textChanged.connect(self.update_stock_dims)
        self.width_input = QLineEdit()
        self.width_input.setPlaceholderText("ENTER WIDTH OF STOCK IN INCHES...")
        self.width_input.setValidator(QDoubleValidator(0.0, 10000.0, 4))
        self.width_input.textChanged.connect(self.update_stock_dims)
        self.height_input = QLineEdit()
        self.height_input.setPlaceholderText("ENTER HEIGHT OF STOCK IN INCHES...")
        self.height_input.setValidator(QDoubleValidator(0.0, 10000.0, 4))
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

        #Save UI Variables / UI Components
        #Initialize save folder
        self.working_dir = os.getcwd()
        self.save_folder = r"saves"
        self.save_folderpath = os.path.join(self.working_dir, self.save_folder)
        self.closeproj = False
        self.uploadfile = False
        self.saveUI = QWidget()
        self.savefile_inputfield = QLineEdit()
        self.savefile_inputfield.setPlaceholderText("ENTER FILENAME TO SAVE...")
        self.savewarningtext = QLabel()
        self.savewarningtext.setStyleSheet("color: red;")
        save_button = QPushButton("SAVE")
        save_button.clicked.connect(lambda:self.save_file(True)) #call savefile
        back_button = QPushButton("BACK")
        back_button.clicked.connect(lambda:self.save_file(False)) #call savefile
        #Save UI Layout
        save_layout = QHBoxLayout(self.saveUI)
        save_layout.addWidget(self.savefile_inputfield)
        save_layout.addWidget(self.savewarningtext)
        save_layout.addWidget(save_button)
        save_layout.addWidget(back_button)
        #Hide & Disable SaveUI widget
        self.saveUI.hide()
        self.saveUI.setEnabled(False)

        #Save Confirm UI
        self.saveconfirmtext = QLabel()
        self.saveconfirmtext.setStyleSheet("color: black;")
        #Hide and disable Save Confirm UI
        self.saveconfirmtext.hide()
        self.saveconfirmtext.setEnabled(False)

        #Set Position UI
        self.position_ui = QWidget()
        self.currentposx = QLabel()
        self.currentposx.setStyleSheet("border: 2px solid black;")
        self.currentposy = QLabel()
        self.currentposy.setStyleSheet("border: 2px solid black;")
        self.posoffset_x_in = QLineEdit()
        self.posoffset_x_in.setPlaceholderText("Enter destination position in x axis")
        self.posoffset_y_in = QLineEdit()
        self.posoffset_y_in.setPlaceholderText("Enter destination position in y axis")
        self.posoffsetvaliditytext = QLabel()
        self.posoffsetvaliditytext.setStyleSheet("color: red;")
        self.previewposbutton = QPushButton("Set Position")
        self.previewposbutton.clicked.connect(self.apply_position_change)
        self.setposbutton = QPushButton("Back")
        self.setposbutton.clicked.connect(self.submitpos)
        #Set Position UI Layout
        pos_ui_layout = QHBoxLayout(self.position_ui)
        pos_ui_layout.addWidget(self.currentposx)
        pos_ui_layout.addWidget(self.currentposy)
        pos_ui_layout.addWidget(QLabel("Destination_X (in): "))
        pos_ui_layout.addWidget(self.posoffset_x_in)
        pos_ui_layout.addWidget(QLabel("Destination_Y (in): "))
        pos_ui_layout.addWidget(self.posoffset_y_in)
        pos_ui_layout.addWidget(self.posoffsetvaliditytext)
        pos_ui_layout.addWidget(self.previewposbutton)
        pos_ui_layout.addWidget(self.setposbutton)
        #Disable and hide set position UI
        self.position_ui.hide()
        self.position_ui.setEnabled(False)

        #Confirm selection UI
        self.selectedtext = QLabel("Select objects before pressing M to move")
        self.selectedtext.setStyleSheet("color: red;")
        #Disable and hide confirm selection UI
        self.selectedtext.hide()
        self.selectedtext.setEnabled(False)

        #WorkSpace UI
        self.viewer = OpenGLViewer(self)

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
        with open(path, "r") as f: #Load and read file
            data = json.load(f)

        i = 0
        for component in data['componentdata']: #Go through each component
            if component['modelName'] == "stock": #If component is stock
                self.viewer.stock_available(component['dimX'], component['dimY'], component['dimZ']) #Call stock_available function with its dimensions
                self.stock_model_data = component #Save stock data locally
            else: #If not stock
                self.viewer.load_model(component['modelName']) #Load model using the .obj path stored in 'modelName'

                #Can optimize this
                for model in self.viewer.loadedmodels: #Go through each loaded model
                    if model['name'] == component['modelName'] and model['id'] == i:
                        #Translate model to match json
                        transformed_meshes = []
                        for mesh in model['meshes']:
                            mesh.apply_translation([round(component['posX'],4), round(component['posY'],4), 0])
                            transformed_meshes.append(mesh)
                        model['meshes'] = transformed_meshes
                        model['position'] = [round(component['posX'],4), round(component['posY'],4), 1]

                        #Rotate model to match json
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

                        terminals = model['permodel_terminals']
                        transformed_terminals = []
                        angle_radians = np.radians(component['rotZ'])
                        cos = np.cos(angle_radians)
                        sin = np.sin(angle_radians)
                        for x,y in terminals:
                            transformed_x = round(x * cos - y * sin + model['position'][0],4)
                            transformed_y = round(x * sin + y * cos + model['position'][1],4)
                            transformed_terminals.append((transformed_x,transformed_y))
                        model['permodel_terminals'] = transformed_terminals
                        break
                #Till here
                i += 1

        self.viewer.wiredata = data['wiresdata'] #Load wire data from the file
        for wire in data['wiresdata']: #For each wire
            for nodedata in wire['wireNodesdata']: #For each node in wire
                self.viewer.wirenodesdata.append(nodedata) #Add to wire node data for drawing

        self.viewer.stockdrawn = True #Stock is drawn
        self.update_offset_validators() #Update validators
        self.viewer.update() #Refresh the Viewer to show changes

    def update_stock_dims(self): #On inputfield/stock dimensions values changed
        self.warningstockdimuitext.setText("")
        try:#get length
            length = round(float(self.length_input.text()),4)
        except ValueError:
            length = 1.0

        try:#get width
            width = round(float(self.width_input.text()),4)
        except ValueError:
            width = 1.0

        try:#get height
            height = round(float(self.height_input.text()),4)
        except ValueError:
            height = 1.0

        self.viewer.stock_available(length, width, height) #draw stock

    def generate_stock(self): #On submit button clicked to submit stock dimensions
        if(self.length_input.text() != "" and self.width_input.text() != "" and self.height_input.text() != ""): #check if all dimensions entered
            self.stockdimensionsui.hide() #hide stock dimensions UI
            self.stockdimensionsui.setEnabled(False) #disable stock dimensions UI
            self.header.show() #unhide header
            self.header.setEnabled(True) #make header interactable
            #Add stock to components data
            if not any(component.get('modelName') == "stock" for component in self.components):
                self.components.append({'modelName': "stock", 'f3dName': "stock.f3d",
                                            'posX': round(-float(self.length_input.text())/2,4), 'posY': round(-float(self.width_input.text())/2,4),
                                            'dimX': round(float(self.length_input.text()),4), 'dimY': round(float(self.width_input.text()),4), 'dimZ': round(float(self.height_input.text()),4),
                                            'rotX': 0.0, 'rotY': 0.0, 'rotZ': 0.0})
            self.stock_model_data = self.components[0] #save stock data locally
            self.viewer.stockdrawn = True #set stock to drawn
            self.update_offset_validators() #update validators
        else:
           self.warningstockdimuitext.setText("ENTER ALL DIMENSIONS") #Notify user to enter all dimensions

    def update_offset_validators(self): #Update the validators
        self.posoffset_x_in.setValidator(QDoubleValidator(-self.stock_model_data['dimX'], self.stock_model_data['dimX'], 4)) #allows user to enter offset between -length to length of stock
        self.posoffset_y_in.setValidator(QDoubleValidator(-self.stock_model_data['dimY'], self.stock_model_data['dimY'], 4)) #allows user to enter offset between -width to width of stock

    def on_dropdown_changed(self,text): #On dropdown option selected
        if text == "ADD": #if option ADD selected
            self.load_component()
        elif text == "SAVE": #if option SAVE selected
            self.header.hide()
            self.header.setEnabled(False)
            self.position_ui.hide()
            self.position_ui.setEnabled(False)
            self.saveUI.show()
            self.saveUI.setEnabled(True)
        elif text == "UPLOAD": #if option UPLOAD selected
            self.uploadfile = True
            self.header.hide()
            self.header.setEnabled(False)
            self.position_ui.hide()
            self.position_ui.setEnabled(False)
            self.saveUI.show()
            self.saveUI.setEnabled(True)
        elif text == "MENU": #if option MENU selected
            self.saveUI.hide()
            self.saveUI.setEnabled(False)
            self.position_ui.hide()
            self.position_ui.setEnabled(False)
            self.header.show()
            self.header.setEnabled(True)

    def go_home(self): #On home button click
        from main import HomeWindow
        self.homewindow = HomeWindow()
        self.close()

    def to_close(self): #On close button click
        self.closeproj = True
        self.header.hide()
        self.header.setEnabled(False)
        self.saveUI.show()
        self.saveUI.setEnabled(True)

    def load_component(self): #loads component
        menu = Selection(self) #Opens dialog box to display all components present
        if menu.exec_() == QDialog.Accepted:#if the component has been selected
            print(self.selectedobjpath)
            self.viewer.load_model(self.selectedobjpath) #load model in path
            if self.dropdown.findText("MENU") != -1: #switch to MENU option
                self.dropdown.setCurrentIndex(self.dropdown.findText("MENU"))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_M and self.viewer.stockdrawn: #if M pressed and stock drawn
            self.header.hide()
            self.header.setEnabled(False)
            self.saveUI.hide()
            self.saveUI.setEnabled(False)
            position = self.get_selected_position() #get current position of the latest selected object/model
            if position == None: #if none - then nothing selected
                self.position_ui.hide()
                self.position_ui.setEnabled(False)
                self.selectedtext.show() #Warn user to select component
                self.selectedtext.setEnabled(True)
                QTimer.singleShot(1000, self.submitpos) #Return to default window
            else: #if position is not none - show position UI
                self.selectedtext.hide()
                self.selectedtext.setEnabled(False)
                self.position_ui.show()
                self.position_ui.setEnabled(True)

    def get_selected_position(self):
        if self.viewer.selected_model_indices: #if model seleceted
            #get current position
            xpos = self.viewer.loadedmodels[self.viewer.selected_model_indices[-1]]['position'][0]
            ypos = self.viewer.loadedmodels[self.viewer.selected_model_indices[-1]]['position'][1]
            #display current position to 4 decimal points
            self.currentposx.setText(f"Current X Position: {xpos:.4f}")
            self.currentposy.setText(f"Current Y Position: {ypos:.4f}")
            return [xpos,ypos]
        elif self.viewer.selected_node_indices: #if wire node selected
            #get current position
            xpos = self.viewer.wirenodesdata[self.viewer.selected_node_indices[-1]]['posX']
            ypos = self.viewer.wirenodesdata[self.viewer.selected_node_indices[-1]]['posY']
            #display current position to 4 decimal points
            self.currentposx.setText(f"Current X Position: {xpos:.4f}")
            self.currentposy.setText(f"Current Y Position: {ypos:.4f}")
            return [xpos,ypos]
        return None

    def apply_position_change(self):#sets position
        #check if entered value is valid
        if self.posoffset_x_in.validator().validate(self.posoffset_x_in.text(), 0)[0] != QValidator.Acceptable or self.posoffset_y_in.validator().validate(self.posoffset_y_in.text(), 0)[0] != QValidator.Acceptable:
            self.posoffsetvaliditytext.setText("Destination position is outside stock dimensions")
        else:
            self.posoffsetvaliditytext.setText("")
            currpos = self.get_selected_position()
            try:#get x and y offset
                xoff = round((float(self.posoffset_x_in.text()) - currpos[0]),4)
                yoff = round(-(float(self.posoffset_y_in.text()) - currpos[1]),4)
            except:#if error, set x and y offset to zero
                xoff = 0.0
                yoff = 0.0
                self.posoffsetvaliditytext.setText("Position parse error, try again")

            self.posoffset_x_in.clear()
            self.posoffset_y_in.clear()
            self.viewer.move_selected_to_position(xoff,yoff) #set position
            self.get_selected_position()#get the new position

    def submitpos(self):#return to default window
        self.posoffset_x_in.clear()
        self.posoffset_y_in.clear()
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

    def save_file(self, savefile): #On save or back button clicked
        if savefile: #If save button clicked
            f3ds_folder = r"assets\f3ds"
            full_f3d_folder = os.path.join(self.working_dir, f3ds_folder) #Get full fed path
            os.makedirs(self.save_folderpath, exist_ok=True) #Create a save directory if it doesnt exist
            save_data = {'componentdata': [], 'wiresdata': []} #Create empty directory for saving

            self.components.clear() #Clear component list to avoid previous save appending onto previous saves
            savefile = False #set save file to false
            if (self.savefile_inputfield.text() == ""): #Check if filename valid
                self.savewarningtext.setText("ENTER FILENAME")
            else: #If valid
                currentdatetime = datetime.datetime.now().strftime("%m-%d-%Y-%H%M%S") #get current date and time
                savefilename = self.savefile_inputfield.text() + f"-{currentdatetime}.json" #generate filename
                savefilepath = os.path.join(self.save_folderpath, savefilename) #concatenate to get file path
                self.savewarningtext.setText("") #set warning text to null
                self.components.append(self.stock_model_data) #add stock data
                for model in self.viewer.loadedmodels:#go through each loaded model
                    f3dpath = os.path.splitext(os.path.basename(model['name']))[0] + ".f3d"
                    fullf3dpath = os.path.join(full_f3d_folder, f3dpath) #get f3d path
                    #populate component list with dictionary as below
                    self.components.append({'modelName': model['name'], 'f3dName': fullf3dpath, #obj path, f3d path
                                                'posX':round(model['position'][0],4), 'posY':round(model['position'][1],4), #x,y position relative to origin
                                                'dimX': 0, 'dimY': 0, 'dimZ': 0, #dimensions
                                                'rotX': model['rotation'][0], 'rotY': model['rotation'][1], 'rotZ': model['rotation'][2]}) #rotation relative to center of model

                #load the data into save_data to save in .json file
                save_data['componentdata'] = self.components
                save_data['wiresdata'] = self.viewer.wiredata

                with open(savefilepath, "w") as f: #open .json file in file path generated previously
                    json.dump(save_data, f, indent=4) #save in json file

                self.saveUI.hide()
                self.saveUI.setEnabled(False)
                self.header.hide()
                self.header.setEnabled(False)
                #tell user the location of file/project
                self.saveconfirmtext.show()
                self.saveconfirmtext.setEnabled(True)
                self.saveconfirmtext.setText(f"SAVED TO: {savefilepath}")
                QTimer.singleShot(2000, self.delay) #call delay
        else:
            self.savefile_inputfield.clear()
            self.saveUI.hide()
            self.saveUI.setEnabled(False)
            self.header.show()
            self.header.setEnabled(True)
            self.closeproj = False
            self.savewarningtext.setText("")
            if self.dropdown.findText("MENU") != -1:
                    self.dropdown.setCurrentIndex(self.dropdown.findText("MENU"))

    def delay(self):
        #remove notification to user
        self.saveconfirmtext.setText("")
        self.saveconfirmtext.hide()
        self.saveconfirmtext.setEnabled(False)

        if self.dropdown.findText("MENU") != -1:#return to default screen
            self.dropdown.setCurrentIndex(self.dropdown.findText("MENU"))

        if self.uploadfile: #if upload pressed
            fusion_path = r"C:\Users\dwara\AppData\Local\Autodesk\webdeploy\production\6a0c9611291d45bb9226980209917c3d\FusionLauncher.exe"
            if os.path.exists(fusion_path): #if fusion 360 exists
                subprocess.Popen([fusion_path]) #launch fusion 360
            else:
                print("Fusion doesn't exist in path") #else print
            self.uploadfile = False #upload flag set to false

        if self.closeproj: #if close button clicked
            self.closeproj = False #set close flag to false
            self.go_home() #return to home screen

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

class Manual(QDialog):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle("Manual")
        self.resize(600,600)
        rulelayout = QVBoxLayout(self)
        rules = [
            "Left Click - Selected Models & Wire Nodes",
            "Shift + Left Click - Multi-select wire nodes",
            "R + Left Click - Rotate Selected Models",
            "M + Left Click - Move Selected Models",
            "W + Left Click on start and end terminals - Draw Wire Nodes",
            "Left Click + Drag - Move Wire Nodes",
            "Left Click + Delete - Delete Wire Nodes, Wire & Selected Models",
            "After drawing nodes:",
            "   Enter - Draw Positive Wire",
            "   N + Enter - Draw Negative Wire"
        ]
        for rule in rules:
            rulelabel = QLabel(f"{rule}\n")
            rulelayout.addWidget(rulelabel)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Q:
            self.close()
