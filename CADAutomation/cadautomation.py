import adsk.core, adsk.fusion, traceback, json, os, sys, math
sys.path.append(r'C:\Users\dwara\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\Scripts\CADAutomation\helper') #Edit file path location
from cutpocket import run as run_cutpocket
#Get file
def get_file(ui):
    selectionmenu = ui.createFileDialog()
    selectionmenu.isMultiSelectEnabled = False
    selectionmenu.filter = 'JSON files (*.json)'
    selected = selectionmenu.showOpen()
    if selected == adsk.core.DialogResults.DialogOK:
            return selectionmenu.filename
    else:
        return None

def run(context):
    ui = None
    try:
        inchtocm = 2.54 #to convert inches to cm (Fusion360 API takes cm only)
        mmtocm = 10
        app = adsk.core.Application.get()
        ui = app.userInterface
        #activate design in Fusion360
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent

        #Get most recent file from save folder
        json_path = get_file(ui)

        if json_path is None:
            ui.messageBox("Select valid file please.")
            return
        #display file loaded
        # if json_path:
        #     ui.messageBox("Latest file: " + json_path)

        #open loaded file for parsing
        with open(json_path, 'r') as f:
            data = json.load(f)

        #define f3d import instance
        import_manager = app.importManager

        components = []
        #Parse JSON file to obtain component data
        for item in data['componentdata']:
            model_path = item['f3dName']  # Obtain f3d filename
            #Convert inches to cm
            posX = item['posX'] * inchtocm
            posY = item['posY'] * inchtocm
            posZ = 0 * inchtocm

            #Check if model path is stock
            if (model_path == "stock.f3d"):
                #get dimensions and convert to cm
                dimX = item['dimX'] * inchtocm
                dimY = item['dimY'] * inchtocm
                dimZ = item['dimZ'] * inchtocm

                #create a new component & save as stock component
                occ = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                occ.component.name = "Stock"
                stockComp = occ.component

                #create a sketch to draw the stock
                sketches = stockComp.sketches
                xyPlane = stockComp.xYConstructionPlane
                sketch = sketches.add(xyPlane) #create sketch on XY plane

                #define points for sketch of stock
                point0 = adsk.core.Point3D.create(0, 0, 0)
                point1 = adsk.core.Point3D.create(-dimX, -dimY, 0) #defines the top right of the stock as origin (similar to mill origin)

                #stock is rectangle - so draws a rectangle with points given above
                sketch.sketchCurves.sketchLines.addTwoPointRectangle(point0, point1)

                # Get the profile defined of the rectangle
                prof = sketch.profiles.item(0)

                #Set up extrusion
                extrudes = stockComp.features.extrudeFeatures
                extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)# Create the extrusion
                distance = adsk.core.ValueInput.createByReal(-dimZ)  # define extrusion distance to stock height
                extInput.setDistanceExtent(False, distance)

                #Do extrusion
                stockextrusion = extrudes.add(extInput)
                stockextrusionbody = stockextrusion.bodies.item(0)
                stockextrusionbody.name = "stockbody"

            else: #Get rotation of component
                rotZ = 0 if item['rotZ'] == 0 else 360 - item['rotZ']
                if not os.path.exists(model_path):
                    ui.messageBox(f"Model not found: {model_path}")
                    continue

                #import model
                f3d_options = import_manager.createFusionArchiveImportOptions(model_path)
                if not f3d_options.isValid:
                    ui.messageBox(f"Invalid F3D file: {model_path}")
                    continue

                import_manager.importToTarget(f3d_options, rootComp)
                last_occ = rootComp.occurrences[-1]

                #create component
                transform = adsk.core.Matrix3D.create()

                #Do rotation
                axisZ = adsk.core.Vector3D.create(0, 0, 1)
                rotationZ = adsk.core.Matrix3D.create()
                rotationZ.setToRotation(math.radians(rotZ), axisZ, adsk.core.Point3D.create(0, 0, 0))
                transform.transformBy(rotationZ)

                #Do Translation
                transform.translation = adsk.core.Vector3D.create(posX, posY, posZ)
                last_occ.transform = transform
                components.append(last_occ)
        #Capture position
        design.snapshots.add()
        # ui.messageBox("Import and placement capture complete.")
        run_cutpocket(context)

        #Hide all imported models
        for component in components:
            component.isLightBulbOn = False

        #Draw wires
        #verify if stock component is present
        if 'stockComp' not in locals():
            ui.messageBox("Stock component not found. Cannot draw wires.")
            return

        batterynegatives = []
        #Parse JSON file to obtain wire data
        if data['wiresdata']:
            wirenum = 0
            for wiredata in data['wiresdata']:
                #get negative wire
                if wiredata['pole'] == "n":
                    for i,node in enumerate(wiredata['wireNodesdata']):
                        if node["component"] == "battery" and node['batteryneg'] == "n":
                            batteryneg = None
                            s_point = None
                            e_point = None
                            ps_point = None
                            if i == 0:
                                x_cm = wiredata['wireNodesdata'][i+2]['posX'] * inchtocm
                                y_cm = wiredata['wireNodesdata'][i+2]['posY'] * inchtocm
                                ps_point = adsk.core.Point3D.create(x_cm, y_cm, 0)
                                x_cm = wiredata['wireNodesdata'][i+1]['posX'] * inchtocm
                                y_cm = wiredata['wireNodesdata'][i+1]['posY'] * inchtocm
                                s_point = adsk.core.Point3D.create(x_cm, y_cm, 0)
                                x_cm = wiredata['wireNodesdata'][i]['posX'] * inchtocm
                                y_cm = wiredata['wireNodesdata'][i]['posY'] * inchtocm
                                e_point = adsk.core.Point3D.create(x_cm, y_cm, 0)
                            else:
                                x_cm = wiredata['wireNodesdata'][i-2]['posX'] * inchtocm
                                y_cm = wiredata['wireNodesdata'][i-2]['posY'] * inchtocm
                                ps_point = adsk.core.Point3D.create(x_cm, y_cm, 0)
                                x_cm = wiredata['wireNodesdata'][i-1]['posX'] * inchtocm
                                y_cm = wiredata['wireNodesdata'][i-1]['posY'] * inchtocm
                                s_point = adsk.core.Point3D.create(x_cm, y_cm, 0)
                                x_cm = wiredata['wireNodesdata'][i]['posX'] * inchtocm
                                y_cm = wiredata['wireNodesdata'][i]['posY'] * inchtocm
                                e_point = adsk.core.Point3D.create(x_cm, y_cm, 0)
                            batteryneg = [s_point,e_point,ps_point]
                            batterynegatives.append(batteryneg)
                            break
                #create sketch on stock component
                sketches = stockComp.sketches
                xyPlane = stockComp.xYConstructionPlane
                sketch = sketches.add(xyPlane) #create sketch on XY plane

                points = [] #define points list
                #Go through all nodes in wire data
                for node in wiredata['wireNodesdata']:
                    #obtain position of nodes
                    x_cm = node['posX'] * inchtocm
                    y_cm = node['posY'] * inchtocm
                    #create points on those positions and add to points
                    points.append(adsk.core.Point3D.create(x_cm, y_cm, 0))

                lines = sketch.sketchCurves.sketchLines #set up to sketch lines on created sketch
                circles = sketch.sketchCurves.sketchCircles
                for i in range(len(points)): #go through each point
                    if (i != len(points) - 1):
                        start = points[i] #get start position
                        end = points[i + 1] #get end position
                        line = lines.addByTwoPoints(start, end) #draw line from start to end position
                        curveCollection = adsk.core.ObjectCollection.create()
                        curveCollection.add(line)

                        dx = end.x - start.x
                        dy = end.y - start.y
                        mid_x = (start.x + end.x)/2
                        mid_y = (start.y + end.y)/2
                        length = (dx**2 + dy**2)**0.5
                        unit_x = dx/length
                        unit_y = dy/length
                        offsetDistance = 1.6/mmtocm
                        offset_anchor = adsk.core.Point3D.create(
                            mid_x - unit_y,
                            mid_y + unit_x,
                            0
                        )
                        sketch.offset(curveCollection, offset_anchor, offsetDistance)
                        sketch.offset(curveCollection, offset_anchor, -offsetDistance)
                        if i == 0:
                            circles.addByCenterRadius(start, 1.6/mmtocm)
                        circles.addByCenterRadius(end, 1.6/mmtocm)
                        line.deleteMe()

                wireprofiles = adsk.core.ObjectCollection.create()
                for profile in sketch.profiles:
                    wireprofiles.add(profile)
                sketch.isVisible = False
                wireextrudes = stockComp.features.extrudeFeatures
                wireextInput = wireextrudes.createInput(wireprofiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
                cutDepth = adsk.core.ValueInput.createByReal(-0.5/mmtocm)
                wireextInput.setDistanceExtent(False, cutDepth)
                wiredraw = wireextrudes.add(wireextInput)
                wiredraw.name = f"Wire {wirenum}"
                wirenum += 1

            if len(batterynegatives) > 0:
                for batterynegative in batterynegatives:
                    i = 1
                    if batterynegative is not None:
                        #last line cut to base of battery negative cut
                        sketches = stockComp.sketches
                        xyPlane = stockComp.xYConstructionPlane
                        negativebatterysketch = sketches.add(xyPlane)
                        negativebatterysketch.name = "Negative Wire To Battery"
                        lines = negativebatterysketch.sketchCurves.sketchLines #set up to sketch lines on created sketch
                        circles = negativebatterysketch.sketchCurves.sketchCircles
                        line = lines.addByTwoPoints(batterynegative[0], batterynegative[1]) #draw line from start to end position
                        line1 = lines.addByTwoPoints(batterynegative[0],batterynegative[2])
                        curveCollection = adsk.core.ObjectCollection.create()
                        curveCollection.add(line)

                        dx = batterynegative[1].x - batterynegative[0].x
                        dy = batterynegative[1].y - batterynegative[0].y
                        mid_x = (batterynegative[0].x + batterynegative[1].x)/2
                        mid_y = (batterynegative[0].y + batterynegative[1].y)/2
                        length = (dx**2 + dy**2)**0.5
                        unit_x = dx/length
                        unit_y = dy/length
                        offsetDistance = 1.6/mmtocm
                        offset_anchor = adsk.core.Point3D.create(
                            mid_x - unit_y,
                            mid_y + unit_x,
                            0
                        )
                        negativebatterysketch.offset(curveCollection, offset_anchor, offsetDistance)
                        negativebatterysketch.offset(curveCollection, offset_anchor, -offsetDistance)
                        circles.addByCenterRadius(batterynegative[0], 1.6/mmtocm)
                        circles.addByCenterRadius(batterynegative[1], 1.6/mmtocm)

                        negativewireprofiles = adsk.core.ObjectCollection.create()
                        for profile in negativebatterysketch.profiles:
                            negativewireprofiles.add(profile)
                        sketch.isVisible = False
                        negativewireextrudes = stockComp.features.extrudeFeatures
                        extInput = negativewireextrudes.createInput(negativewireprofiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
                        cutDepth = adsk.core.ValueInput.createByReal(-2.0/mmtocm)
                        extInput.setDistanceExtent(False, cutDepth)
                        extrudeFeature = negativewireextrudes.add(extInput)

                        #draw body for first sweep
                        sweeponeprofiles = adsk.core.ObjectCollection.create()
                        bottomface = None
                        minZ = float('inf')

                        for face in extrudeFeature.endFaces:
                            if face.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                                point = face.pointOnFace
                                if point.z < minZ:
                                    minZ = point.z
                                    bottomface = face
                        if bottomface is None:
                            ui.messageBox("Couldn't find the bottom face for the battery cut.")
                        else:
                            sketches = stockComp.sketches
                            sweeponesketch = sketches.add(bottomface)
                            sweeponesketch.name = "Sweep one"
                            sweeponesketch.sketchCurves.sketchCircles.addByCenterRadius(batterynegative[0], 1.6/mmtocm)

                            minarea = float('inf')
                            minprofile = None
                            for profile in sweeponesketch.profiles:
                                bb = profile.boundingBox
                                width = abs(bb.maxPoint.x - bb.minPoint.x)
                                length = abs(bb.maxPoint.y - bb.minPoint.y)
                                area = width * length
                                if area < minarea:
                                    minarea = area
                                    minprofile = profile
                            sweeponeprofiles.add(minprofile)
                            # sweeponesketch.isVisible = False
                            sweeponeextrudes = stockComp.features.extrudeFeatures
                            sweeponeextrudesInput = sweeponeextrudes.createInput(sweeponeprofiles, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                            distance = adsk.core.ValueInput.createByReal(4/mmtocm)
                            sweeponeextrudesInput.setDistanceExtent(False, distance)
                            sweeponeextrude = sweeponeextrudes.add(sweeponeextrudesInput)
                            sweeponeextrude.name = "Sweep one body extrude"
                            sweeponebody = sweeponeextrude.bodies.item(0)
                            sweeponebody.name = "Sweep One Body"

                        #construct midplanes to draw sweep paths
                        planes = stockComp.constructionPlanes
                        planeInput = planes.createInput()
                        planeInput2 = planes.createInput()
                        planeInput.setByAngle(line,adsk.core.ValueInput.createByString('90 deg'),stockComp.xYConstructionPlane)
                        planeInput2.setByAngle(line1,adsk.core.ValueInput.createByString('90 deg'),stockComp.xYConstructionPlane)
                        plane = planes.add(planeInput)
                        plane2 = planes.add(planeInput2)
                        plane.name = "Mid Plane 1"
                        plane2.name = "Mid Plane 2"

                        #draw first sweep path
                        sketches = stockComp.sketches
                        firstsweeppathsketch = sketches.add(plane2)
                        firstsweeppathsketch.name = "SPathOne"
                        projectedline = firstsweeppathsketch.project(line1)
                        projectedbottomline = firstsweeppathsketch.project(min(sweeponebody.faces, key=(lambda f: f.centroid.z)))
                        lineProj = adsk.fusion.SketchLine.cast(projectedline.item(0))
                        start_pt = lineProj.startSketchPoint.geometry
                        end_pt = lineProj.endSketchPoint.geometry
                        mid_pt = adsk.core.Point3D.create(
                            (start_pt.x + end_pt.x) / 2,
                            (start_pt.y + end_pt.y) / 2,
                            (start_pt.z + end_pt.z) / 2
                        )
                        upvector = adsk.core.Vector3D.create(0, 0, 1)
                        anchor = mid_pt.copy()
                        dir = upvector.copy()
                        dir.normalize()
                        dir.scaleBy(-0.1)
                        anchor.translateBy(dir)
                        line1 = firstsweeppathsketch.offset(projectedline, anchor, 0.5/mmtocm)
                        topline = adsk.fusion.SketchLine.cast(line1.item(0))
                        lineProj.deleteMe()
                        start_pt = topline.startSketchPoint.geometry
                        end_pt = topline.endSketchPoint.geometry
                        mid_pt = adsk.core.Point3D.create(
                            (start_pt.x + end_pt.x) / 2,
                            (start_pt.y + end_pt.y) / 2,
                            (start_pt.z + end_pt.z) / 2
                        )

                        line2 = adsk.fusion.SketchLine.cast(projectedbottomline.item(0))
                        start_pt1 = line2.startSketchPoint.geometry
                        end_pt1 = line2.endSketchPoint.geometry
                        mid_pt1 = adsk.core.Point3D.create(
                            (start_pt1.x + end_pt1.x) / 2,
                            (start_pt1.y + end_pt1.y) / 2,
                            (start_pt1.z + end_pt1.z) / 2
                        )

                        #get face for battery negative terminal extrusion
                        face = min(sweeponebody.faces, key=(lambda f: f.centroid.z))
                        planes = stockComp.constructionPlanes
                        planeInput = planes.createInput()
                        planeInput.setByOffset(face,adsk.core.ValueInput.createByReal(0.0))
                        facePlane = planes.add(planeInput)
                        facePlane.name = "Plane at Face"
                        #Perform first sweep - 2nd to last line
                        path = firstsweeppathsketch.sketchCurves.sketchLines.addByTwoPoints(mid_pt1,mid_pt)
                        sweeppath = stockComp.features.createPath(path) #create path
                        sweeps = stockComp.features.sweepFeatures #set up sweep cut
                        sweepInput = sweeps.createInputForSolid(sweeponebody, sweeppath, adsk.fusion.FeatureOperations.CutFeatureOperation) #create sweep cut
                        sweepInput.distanceTwo = adsk.core.ValueInput.createByReal(0.0)
                        sweeps.add(sweepInput) #do sweep cut
                        # sweeponebody.isVisible = False

                        #extrude negative terminal by 0.2mm upwards
                        sketches = stockComp.sketches
                        negativeterminalextrudesketch = sketches.add(facePlane)
                        centre = negativeterminalextrudesketch.modelToSketchSpace(batterynegative[1])
                        centrepoint = centre
                        centrepoint.z = 0
                        negativeterminalextrudesketch.sketchCurves.sketchCircles.addByCenterRadius(centrepoint, 4/mmtocm)
                        negativeterminalprofiles = adsk.core.ObjectCollection.create()
                        for profile in negativeterminalextrudesketch.profiles:
                            negativeterminalprofiles.add(profile)

                        negativeterminalextrudes = stockComp.features.extrudeFeatures
                        negativeterminalextrudesInput = negativeterminalextrudes.createInput(negativeterminalprofiles, adsk.fusion.FeatureOperations.JoinFeatureOperation)
                        negativeterminalextrudesInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-0.2/mmtocm))
                        negpocket = negativeterminalextrudes.add(negativeterminalextrudesInput)
                        negpocket.name = f"Battery {i} Negative Pocket"
                        i += 1
                        #draw second sweep path
                        sketches = stockComp.sketches
                        secondweeppathsketch = sketches.add(plane)
                        secondweeppathsketch.name = "SPathTwo"
                        projectedline = secondweeppathsketch.project(line)
                        lineProj = adsk.fusion.SketchLine.cast(projectedline.item(0))
                        start_pt = lineProj.startSketchPoint.geometry
                        end_pt = lineProj.endSketchPoint.geometry
                        mid_pt = adsk.core.Point3D.create(
                            (start_pt.x + end_pt.x) / 2,
                            (start_pt.y + end_pt.y) / 2,
                            (start_pt.z + end_pt.z) / 2
                        )
                        upvector = adsk.core.Vector3D.create(0, 0, 1)
                        anchor = mid_pt.copy()
                        dir = upvector.copy()
                        dir.normalize()
                        dir.scaleBy(-0.1)
                        anchor.translateBy(dir)
                        line1 = secondweeppathsketch.offset(projectedline, anchor, -facePlane.geometry.origin.z)
                        topline = adsk.fusion.SketchLine.cast(line1.item(0))
                        lineProj.deleteMe()

                        top_start = topline.startSketchPoint.geometry
                        top_end = topline.endSketchPoint.geometry

                        line_direction = adsk.core.Vector3D.create(
                            top_end.x - top_start.x,
                            top_end.y - top_start.y,
                            top_end.z - top_start.z
                        )
                        line_direction.normalize()
                        line_direction.scaleBy(1.6/mmtocm)

                        offset_point = top_start.copy()
                        offset_point.translateBy(line_direction)

                        offset_point_sketch = secondweeppathsketch.sketchPoints.add(offset_point)
                        end_pt = topline.endSketchPoint.geometry
                        mid_pt = adsk.core.Point3D.create(
                            (offset_point.x + end_pt.x) / 2,
                            (offset_point.y + end_pt.y) / 2,
                            (offset_point.z + end_pt.z) / 2
                        )
                        upvector = adsk.core.Vector3D.create(0, 0, 1)
                        anchor = mid_pt.copy()
                        dir = upvector.copy()
                        dir.normalize()
                        dir.scaleBy(-0.1)
                        anchor.translateBy(dir)

                        midstart = adsk.core.Point3D.create(
                            (offset_point.x + mid_pt.x) / 2,
                            (offset_point.y + mid_pt.y) / 2,
                            (offset_point.z + mid_pt.z) / 2
                        )

                        midend = adsk.core.Point3D.create(
                            (end_pt.x + mid_pt.x) / 2,
                            (end_pt.y + mid_pt.y) / 2,
                            (end_pt.z + mid_pt.z) / 2
                        )
                        line = secondweeppathsketch.sketchCurves.sketchLines.addByTwoPoints(midstart,midend)
                        secondsweepcurveCollection = adsk.core.ObjectCollection.create()
                        secondsweepcurveCollection.add(line)
                        line2 = secondweeppathsketch.offset(secondsweepcurveCollection, anchor, 1.2/mmtocm)
                        line.deleteMe()
                        bottomline = adsk.fusion.SketchLine.cast(line2.item(0))
                        path = adsk.core.ObjectCollection.create()
                        startbottom = bottomline.startSketchPoint.geometry
                        endbottom = bottomline.endSketchPoint.geometry
                        path.add(secondweeppathsketch.sketchCurves.sketchLines.addByTwoPoints(offset_point,startbottom))
                        path.add(bottomline)
                        path.add(secondweeppathsketch.sketchCurves.sketchLines.addByTwoPoints(endbottom,end_pt))

                        #sweep body two
                        sketches = stockComp.sketches
                        sweeptwosketch = sketches.add(facePlane)
                        sweeptwosketch.name = "Sweep two"
                        offset_pt = sweeptwosketch.project(offset_point_sketch)
                        offset_p = adsk.fusion.SketchPoint.cast(offset_pt.item(0))
                        sweeptwosketch.sketchCurves.sketchCircles.addByCenterRadius(offset_p, 1.6/mmtocm)

                        sweeptwoprofiles = adsk.core.ObjectCollection.create()
                        for profiles in sweeptwosketch.profiles:
                            sweeptwoprofiles.add(profiles)

                        sweeptwoextrudes = stockComp.features.extrudeFeatures
                        sweeptwoextrudesInput = sweeptwoextrudes.createInput(sweeptwoprofiles, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                        distance = adsk.core.ValueInput.createByReal(-4/mmtocm)
                        sweeptwoextrudesInput.setDistanceExtent(False, distance)
                        sweeptwoextrude = sweeptwoextrudes.add(sweeptwoextrudesInput)
                        sweeptwoextrude.name = "Sweep two body extrude"
                        sweeptwobody = sweeptwoextrude.bodies.item(0)
                        sweeptwobody.name = "Sweep Two Body"
                        secondsweeppath = stockComp.features.createPath(path) #create path
                        secondsweeps = stockComp.features.sweepFeatures #set up sweep cut
                        secondsweepInput = secondsweeps.createInputForSolid(sweeptwobody, secondsweeppath, adsk.fusion.FeatureOperations.CutFeatureOperation) #create sweep cut
                        secondsweepInput.distanceTwo = adsk.core.ValueInput.createByReal(0.0)
                        secondsweeps.add(secondsweepInput) #do sweep cut
                        sweeptwosketch.isVisible = False
                        # sweeptwobody.isVisible = False
        #Turn on visibility of all components
        for component in components:
            component.isLightBulbOn = True

        # ui.messageBox("Components Imported and Pocket Created! Ink Path Engraved!")

    except Exception as e:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
