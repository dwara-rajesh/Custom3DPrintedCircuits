#viewer.py
from PyQt5.QtWidgets import QOpenGLWidget, QSizePolicy
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QMouseEvent
from OpenGL.GL import *
from OpenGL.GLU import *

import trimesh,os
from trimesh.ray.ray_pyembree import RayMeshIntersector
import numpy as np

class OpenGLViewer(QOpenGLWidget):
    def __init__(self, parent=None):
        super(OpenGLViewer, self).__init__(parent)
        #Set up widget for key presses
        self.setFocusPolicy(Qt.StrongFocus)

        #Dynamic Resolution
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        #Component terminals relative to component centre
        self.component_terminals = {
            "LED.obj": [(-0.1378,0),(0.1378,0)],
            "microcontroller.obj": [(-0.225,0.375),(0.225, 0.375),(-0.25,0.225),(0.25,0.225),(-0.25,0.125),(0.25,0.125),(-0.25,0.025),(0.25,0.025),(-0.25,-0.075),(0.25,-0.075),(-0.25,-0.175),(0.25,-0.175),(-0.24,-0.27),(0.24,-0.27)], #top to bottom - (right, left)
            "button.obj": [(-0.378,0),(0.378,0)],
            "battery.obj": [(0,0),(0.36,0)] #negative terminal at (0,0)
        }
        #Component Loading
        self.stock = None #stock variable
        self.model_id = 0
        self.loadedmodels = [] #Loaded models
        self.manualbook = None

        self.wire_start_terminal = None
        self.wirenodesdata = [] #Wire Nodes data for saving
        self.wiredata = [] #Wire data for saving
        self.start = 0
        self.end = 0

        self.selected_model_indices = [] #current selected model indices
        self.selected_node_indices = [] #current selected node indices

        self.last_mouse_pos = None #Last mouse position

        #Camera Position
        self.camera_pos = (0,0,10) #x,y,z
        #Camera LookAt Position
        self.camera_lookat = (0,0,0)
        #Camera Positive Y Direction
        self.posycam = (0,1,0)

        #MultiSelect Feature
        self.multiselect = False
        #Draw Wire Node Feature
        self.drawwirenode = False

        self.n_pressed = False
        self.stockdrawn = False

    def orient_camera(self):
        glLoadIdentity()
        gluLookAt(
            self.camera_pos[0],self.camera_pos[1], self.camera_pos[2],  # Camera position (eye)
            self.camera_lookat[0],self.camera_lookat[1], self.camera_lookat[2],    # Look-at point (center)
            self.posycam[0],self.posycam[1], self.posycam[2]     # Up vector (positive Y is up)
        )

    def initializeGL(self):
        glClearColor(0.5, 0.5, 0.5, 1.0) #almost black bakcground
        glEnable(GL_DEPTH_TEST) #Enable depth
        glDepthFunc(GL_LESS)
        glDisable(GL_LIGHTING) #Disable lighting
        self.scaley = 10
        aspect = self.width() / self.height() if self.height() != 0 else 1.0
        self.scalex = self.scaley * aspect
        self.set_projection() #Set scale and projetcion

    def set_projection(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-self.scalex, self.scalex, -self.scaley, self.scaley, -1000, 1000) #Define scale and camera type - orthographic or perspective
        glMatrixMode(GL_MODELVIEW)
        self.orient_camera() #Orient camera

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.orient_camera() #Orient camera

        glLineWidth(10/self.scaley)
        glBegin(GL_LINES)

        glColor3f(0.0,1.0,0.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 0.1, 0.0)

        glColor3f(1.0,0.0,0.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.1, 0.0, 0.0)
        glEnd()

        if self.stock: #If stock present
            self.load_stock(*self.stock) #load stock

        for i, obj_data in enumerate(self.loadedmodels): #if models loaded
            # #Draw all models
            # glPushMatrix()
            glTranslatef(*[0,0,1])
            for mesh in obj_data['meshes']:
                self.draw_model(mesh,obj_data['transform'],i)
            # glPopMatrix()

            glPointSize(10 / self.scaley)
            glBegin(GL_POINTS)
            glColor3f(0.0,1.0,0.0)
            terminals = obj_data['permodel_terminals']
            for x,y in terminals:
                glVertex3f(x, y, 2.0)
            glEnd()

        for i, nodedata in enumerate(self.wirenodesdata):
            self.draw_wirenodes(i,nodedata)

        for wire in self.wiredata:
            glLineWidth(10/self.scaley)
            glBegin(GL_LINES)
            for i in range(len(wire['wireNodesdata'])):
                if i != len(wire['wireNodesdata']) - 1:
                    start = wire['wireNodesdata'][i]
                    end = wire['wireNodesdata'][i + 1]
                    if wire['pole'] == 'p':
                        glColor3f(0.0, 1.0, 0.0)
                    elif wire['pole'] == 'n':
                        glColor3f(0.0, 0.0, 0.0)
                    glVertex3f(start['posX'], start['posY'], 2.0)  # slight z offset
                    glVertex3f(end['posX'], end['posY'], 2.0)
            glEnd()

        self.orient_camera()

    def move_selected_to_position(self,dx,dy):
        for index in self.selected_model_indices:
            model = self.loadedmodels[index]
            tx = trimesh.transformations.translation_matrix([dx, -dy, 0])
            model['transform'] = np.dot(tx, model['transform'])
            model['position'][0] += dx
            model['position'][1] -= dy

            # Move any wire nodes attached to this model
            for node in self.wirenodesdata:
                if node['componentid'] == model['id']:
                    node['posX'] += dx
                    node['posY'] -= dy

            # Update terminal positions
            translated_terminals = []
            for x, y in model['permodel_terminals']:
                translated_terminals.append((round(x + dx, 4), round(y - dy, 4)))
            model['permodel_terminals'] = translated_terminals
        self.update()

    def draw_model(self, mesh, transform, i):
        #get faces and vertices
        faces = mesh.faces
        vertices = mesh.vertices

        glPushMatrix()
        glMultMatrixf(transform.T)

        #get materials
        if hasattr(mesh.visual, 'material') and hasattr(mesh.visual.material, 'diffuse'):
            color = mesh.visual.material.diffuse
            norm_color = np.array(color[:3]) / 255
            #if material not present
            if i in self.selected_model_indices:
                glColor3f(1.0,0.5,0.2)
            elif np.allclose(norm_color, 0.0) or np.allclose(norm_color, 1.0):
                glColor3f(0.8, 0.8, 0.8)
            else: #else add material
                glColor3f(*norm_color)
        else:
            glColor3f(0.6, 0.6, 0.6)
        #draw faces
        glBegin(GL_TRIANGLES)
        for face in faces:
            for idx in face:
                glVertex3fv(vertices[idx])
        glEnd()
        glPopMatrix()

    def load_model(self, path): #loads model
        sceneormesh = trimesh.load(path, force = 'scene', skip_materials = False) #get mesh from model path (.obj path)
        meshes = []

        if isinstance(sceneormesh,trimesh.Scene): #check if scene or mesh
            for _, mesh in sceneormesh.geometry.items(): #if scene, add all meshes
                meshes.append(mesh)
        else:
            meshes.append(sceneormesh) #if mesh, add mesh

        name = os.path.basename(path)
        if name in self.component_terminals:
            terminals = []
            for x,y in self.component_terminals[name]:
                terminals.append((round(x,4),round(y,4)))
        model_entry = {'id': self.model_id, 'name': path,'meshes': meshes, 'position': [0,0,1], 'rotation': [0,0,0],'transform': np.eye(4), 'permodel_terminals':terminals} #add 'transform': np.eye(4)
        self.loadedmodels.append(model_entry) #append meshes to loadedmodels
        self.model_id += 1
        self.update() #Calls paintGL function

    def stock_available(self, length, width, height):
        self.stock = (length, width, height) #defines stock dimensions
        self.update() #calls paintGL function

    def load_stock(self, l, w, h):
        glPushMatrix()
        glColor3f(1.0, 1.0, 1.0) #colour of stock = white
        #define vertices
        l = round(l,4)
        w = round(w,4)
        h = round(h,4)
        vertices = [
            [-l, 0, 0],
            [0, 0, 0],
            [0, -w, 0],
            [-l, -w, 0],
        ]
        #Draw stock
        glBegin(GL_QUADS)
        for vertex in vertices:
            glVertex3fv(vertex)
        glEnd()
        glPopMatrix()
        self.center_and_zoom_camera_on_stock(l,w)

    def center_and_zoom_camera_on_stock(self, l, w, margin_factor=1.01):
        # Center camera
        center_x = round(-l / 2,4)
        center_y = round(-w / 2,4)

        # Use max dimension to determine scale
        max_dim = round(max(l, w),4)

        # Adjust scaley (which sets vertical extent in ortho projection)
        self.scaley = round((max_dim / 2) * margin_factor,4)  # add a margin for visibility

        # Set scalex based on aspect ratio (done in set_projection)
        aspect = self.width() / self.height() if self.height() != 0 else 1.0
        self.scalex = round(self.scaley * aspect,4)

        # Adjust camera position
        self.camera_pos = (center_x, center_y, max_dim * margin_factor)
        self.camera_lookat = (center_x, center_y, 0)
        self.set_projection()
        self.update()

    def draw_wirenodes(self, i, nodedata):
        self.radius = round(0.0075 * self.scaley,4) #Wire node radius
        if i in self.selected_node_indices:
            glColor3f(0.0,0.0,1.0)
        else:
            glColor3f(1.0, 0.0, 0.0)

        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(nodedata['posX'], nodedata['posY'], 2.0)

        for i in range(65):
            theta = 2.0 * np.pi * i / 64
            x = self.radius * np.cos(theta) + nodedata['posX']
            y = self.radius * np.sin(theta) + nodedata['posY']
            glVertex3f(round(x,4),round(y,4),3.0)
        glEnd()

    def mousePressEvent(self, event): #when mouse pressed
        if not self.drawwirenode:
            hitornot = []
            self.last_mouse_pos = event.pos() #get position of mouse on press time
            ray_origin, ray_direction = self.screen_to_ray(event.x(), event.y()) #get raycast of mous ein that position

            for i, nodedata in enumerate(self.wirenodesdata):
                node_center = np.array([nodedata['posX'], nodedata['posY']])
                if np.linalg.norm(ray_origin[:2] - node_center) <= self.radius:
                    hitornot.append(True)
                    if i not in self.selected_node_indices:
                        self.selected_node_indices.append(i)
                    else:
                        self.selected_node_indices.remove(i)
                    self.update()
                    return
                    # if not self.multiselect:
                    #     break
                else:
                    hitornot.append(False)

            for i, model in enumerate(self.loadedmodels):
                transformed_meshes = []
                for mesh in model['meshes']:
                    transformed = mesh.copy()
                    transformed.apply_transform(model['transform'])
                    transformed_meshes.append(transformed)

                raycast_mesh = trimesh.util.concatenate(transformed_meshes)
                ray = RayMeshIntersector(raycast_mesh)

                hit = ray.intersects_any(
                    ray_origins=[ray_origin],
                    ray_directions=[ray_direction]
                )[0]

                if hit:
                    hitornot.append(True)
                    if i not in self.selected_model_indices:
                        self.selected_model_indices.append(i)
                    else:
                        self.selected_model_indices.remove(i)
                    self.update()
                    # if not self.multiselect:
                    #     break
                else:
                    hitornot.append(False)

            if True in hitornot:
                self.update()
            else:
                self.selected_model_indices.clear()
                self.selected_node_indices.clear()
                self.update()

        else:
            centre, _ = self.screen_to_ray(event.x(), event.y())
            clicked_terminal = None
            clicked_key = None
            clicked_id = None
            battery_neg = None
            min_dist = float('inf')
            threshold = 0.1 * self.scaley
            for model in self.loadedmodels:
                for tx,ty in model['permodel_terminals']:
                    dist = np.hypot(centre[0] - tx, centre[1] - ty)
                    if dist < min_dist and dist <= threshold:
                        clicked_terminal = (round(tx, 4), round(ty, 4))
                        clicked_id = model['id']
                        clicked_key = os.path.splitext(os.path.basename(model['name']))[0]
                        if clicked_key == "battery":
                            if clicked_terminal[0] == model['position'][0] and clicked_terminal[1] == model['position'][1]:
                                battery_neg = "n"
                            else:
                                battery_neg = "p"
                        min_dist = dist

            if clicked_terminal:
                if self.wire_start_terminal is None:
                    self.wire_start_terminal = (clicked_terminal, clicked_id, clicked_key)
                    self.wirenodesdata.append({'posX': clicked_terminal[0], 'posY': clicked_terminal[1], 'component': clicked_key, 'componentid': clicked_id, 'batteryneg': battery_neg})
                    self.update()
                else:
                    (terminal, id, _) = self.wire_start_terminal
                    if id == clicked_id:
                        print("Error")
                    else:
                        if terminal[0] == clicked_terminal[0] or terminal[1] == clicked_terminal[1]:
                            pass
                        elif abs(terminal[0] - clicked_terminal[0]) > abs(terminal[1] - clicked_terminal[1]):
                            self.wirenodesdata.append({'posX': clicked_terminal[0], 'posY': terminal[1], 'component': None, 'componentid': None, 'batteryneg': None})
                        else:
                            self.wirenodesdata.append({'posX': terminal[0]+0.5, 'posY': clicked_terminal[1]+0.1,'component': None, 'componentid': None, 'batteryneg': None})
                            self.wirenodesdata.append({'posX': clicked_terminal[0]+0.5, 'posY': clicked_terminal[1]+0.1,'component': None, 'componentid': None, 'batteryneg': None})
                        self.wirenodesdata.append({'posX': clicked_terminal[0], 'posY': clicked_terminal[1],'component': clicked_key, 'componentid': clicked_id, 'batteryneg': battery_neg })
                        self.wire_start_terminal = None
                        self.update()
            else:
                print("Click closer to terminal")


    def mouseMoveEvent(self, event): #when mouse dragged
    #     if self.selected_model_indices: #check if any model selected
    #         dx = event.x() - self.last_mouse_pos.x()
    #         dy = event.y() - self.last_mouse_pos.y()

    #         # Convert pixel movement to world coordinates (approximate)
    #         dx_world = dx * (2 * self.scalex / self.width())
    #         dy_world = dy * (2 * self.scaley / self.height())

    #         for selected_model_index in self.selected_model_indices:
    #             selectedmodel = self.loadedmodels[selected_model_index]
    #             # Update position
    #             selectedmodel['position'][0] += dx_world
    #             selectedmodel['position'][1] -= dy_world

    #             transformed_meshes = []
    #             for mesh in selectedmodel['meshes']:
    #                 mesh.apply_translation([dx_world, -dy_world, 0])
    #                 transformed_meshes.append(mesh)
    #             self.loadedmodels[selected_model_index]['meshes'] = transformed_meshes
    #             self.loadedmodels[selected_model_index]['position'] = selectedmodel['position']

        if self.selected_node_indices: #check if any node selected
            dx = event.x() - self.last_mouse_pos.x()
            dy = event.y() - self.last_mouse_pos.y()

            # Convert pixel movement to world coordinates (approximate)
            dx_world = dx * (2 * self.scalex / self.width())
            dy_world = dy * (2 * self.scaley / self.height())

            for selected_node_index in self.selected_node_indices:
                # Update position
                self.wirenodesdata[selected_node_index]['posX'] = round(self.wirenodesdata[selected_node_index]['posX'] + dx_world,4)
                self.wirenodesdata[selected_node_index]['posY'] = round(self.wirenodesdata[selected_node_index]['posY'] - dy_world,4)

        if self.selected_node_indices: #self.selected_model_indices or
            self.last_mouse_pos = event.pos()
            self.update()
        else:
            self.update()

    def mouseReleaseEvent(self, event):
        # if self.selected_model_indices and not self.multiselect:
        #     self.selected_model_indices.clear()
        #     self.update()
        if self.selected_node_indices and not self.multiselect:
            self.selected_node_indices.clear()
            self.update()

    def screen_to_ray(self, x, y):
        # Convert screen coordinates to normalized device coordinates [-1, 1]
        ndc_x = 2.0 * x / self.width() - 1.0
        ndc_y = 1.0 - 2.0 * y / self.height()  # Flip Y

        world_x = ndc_x * self.scalex + self.camera_pos[0]
        world_y = ndc_y * self.scaley + self.camera_pos[1]

        ray_origin_z = self.camera_pos[2]

        ray_origin = np.array([world_x, world_y, ray_origin_z])
        ray_direction = np.array([0.0, 0.0, -1.0])
        return ray_origin, ray_direction

    def rotate_selected(self,angle_degrees = 90, axis = 'z'):
        if not self.selected_model_indices:
            return

        angle_radians = np.radians(angle_degrees)
        direction = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, -1]}[axis]
        for i in self.selected_model_indices:
            model = self.loadedmodels[i]
            rotation_matrix = trimesh.transformations.rotation_matrix(
                angle_radians,
                direction,
                point=model['position']
            )
            model['transform'] = np.dot(rotation_matrix, model['transform'])
            model['rotation'][2] += angle_degrees
            if model['rotation'][2] >= 360:
                model['rotation'][2] = 0


            cos = np.cos(angle_radians)
            sin = np.sin(angle_radians)
            px, py = model['position'][:2]
            rotated_terminals = []
            for x, y in model['permodel_terminals']:
                dx, dy = x - px, y - py
                rx = dx * cos - dy * sin + px
                ry = dx * sin + dy * cos + py
                rotated_terminals.append((round(rx, 4), round(ry, 4)))
            model['permodel_terminals'] = rotated_terminals

            for node in self.wirenodesdata:
                if node['componentid'] == model['id']:
                    for idx, (x, y) in enumerate(rotated_terminals):
                        if abs(node['posX'] - x) < 0.001 and abs(node['posY'] - y) < 0.001:
                            node['posX'], node['posY'] = x, y
                            break
        self.update()

    def delete_selected(self):
        if not self.selected_model_indices and not self.selected_node_indices:
            return

        for i in sorted(self.selected_model_indices, reverse=True):
            del self.loadedmodels[i]

        self.selected_model_indices.clear()
        self.update()

        for i in sorted(self.selected_node_indices, reverse=True):
            inwire = False
            for j in reversed(range(len(self.wiredata))):
                if self.wirenodesdata[i] in self.wiredata[j]["wireNodesdata"]:
                    inwire = True
                    for wirenodesdata in self.wiredata[j]["wireNodesdata"]:
                        index = self.wirenodesdata.index(wirenodesdata)
                        del self.wirenodesdata[index]
                        self.start -= 1
                    del self.wiredata[j]
                    break

            if not inwire:
                del self.wirenodesdata[i]

            self.wire_start_terminal = None

        self.selected_node_indices.clear()
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self.multiselect = True

        if event.key() == Qt.Key_R:
            self.rotate_selected()

        if event.key() == Qt.Key_N:
            self.n_pressed = True

        if event.key() == Qt.Key_M:
            parent = self.parent()
            if parent:
                parent.keyPressEvent(event)
            return

        if event.key() == Qt.Key_Q:
            parent = self.parent()
            if parent:
                from uibuilder import Manual
                self.manualbook = Manual(parent)
                self.manualbook.show()

        if event.key() == Qt.Key_Delete:
            self.delete_selected()

        if event.key() == Qt.Key_W and self.stockdrawn:
            self.drawwirenode = True

        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and self.stockdrawn:
            self.end = len(self.wirenodesdata)
            if len(self.wirenodesdata[self.start:self.end]) >= 2:
                if self.n_pressed:
                    pole = 'n'
                else:
                    pole = 'p'
                self.wiredata.append({'wireNodesdata': self.wirenodesdata[self.start:self.end], 'pole': pole})
                self.start = len(self.wirenodesdata)
                self.update()
            else:
                print("Not Enough nodes")

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self.multiselect = False

        if event.key() == Qt.Key_W:
            self.drawwirenode = False

        if event.key() == Qt.Key_N:
            self.n_pressed = False