import adsk.core, adsk.fusion, traceback, math
import time

def run(context):
    ui = None
    try:
        # Get Fusion 360 application objects
        app = adsk.core.Application.get()
        ui  = app.userInterface
        # ui.messageBox("Cutting Pockets")
        design = app.activeProduct
        rootComp = design.rootComponent

        component_occurences = []
        invisibleoccurences = []

        stock_occurence = None
        stock_body = None
        inchtocm = 2.54
        mmtocm = 10
        pocket_depth = {"button": (2.0 / mmtocm, 1.5 / mmtocm), #(Extrusion/Cut, Chamfer Distance)
                 "battery": (1.5 / mmtocm, 0.0),
                 "microcontroller": (0.8 / mmtocm, 0.635 / mmtocm),
                 "led": (1.0 / mmtocm, 1.0 / mmtocm),
                 }

        for occ in rootComp.occurrences:
            if "stock" in occ.name.lower():
                stock_body = occ.component.bRepBodies.item(0)
                stock_occurence = occ
            else:
                component_occurences.append(occ)

        if stock_occurence is None:
            ui.messageBox("Stock model is not imported. Please check Heirarchy")
            return

        if stock_body is None:
            ui.messageBox("Stock model does not have a body.")
            return

        # ui.messageBox(f"Number of components to engrave: {len(component_occurences)}")
        if len(component_occurences) + 1 < 2:
            ui.messageBox("Need at least two bodies for engraving/pocket creation process.")
            return

        for component_occurence in component_occurences:
            component_body = None
            if component_occurence is None:
                ui.messageBox(f"{component_occurence.name} model is not imported. Please check Heirarchy")
                return

            component_body = component_occurence.component.bRepBodies.item(0)
            if component_body is None:
                ui.messageBox(f"{component_occurence.name} model does not have a body.")
                return

            for occ in component_occurences:
                if occ != component_occurence:
                    occ.isLightBulbOn = False
            app.activeViewport.refresh()
            time.sleep(0.3)

            # Create a new sketch on the top face of the stock to project the component outline
            sketches = rootComp.sketches
            xyPlane = rootComp.xYConstructionPlane
            sketch = sketches.add(xyPlane)
            sketch.name = f"{component_occurence.name} Outline Projection"
            # Navigate to component level
            component_body_asm = component_body.createForAssemblyContext(component_occurence)
            projected = sketch.project(component_body_asm)

            if "button" in component_occurence.name.lower():
                offset_distance = 0.005 + (0.018 * inchtocm)
            else:
                offset_distance = 0.005  # Adjust as needed, in cm (since you're working in cm)

            sketch.offset(projected, adsk.core.Point3D.create(0, 0, 0), offset_distance)

            for entity in projected:
                entity.deleteMe()

            profiles = adsk.core.ObjectCollection.create()
            # ui.messageBox(f"Number of profiles in sketch: {sketch.profiles.count}")
            for profile in sketch.profiles:
                profiles.add(profile)
            sketch.isVisible = False

            #Get extrusion/cut depth
            pocketDepth = 0
            chamferDepth = 0
            for component, depth in pocket_depth.items():
                if component in component_occurence.name.lower():
                    pocketDepth = depth[0]
                    chamferDepth = depth[1]

            #Turn off component visibility
            component_occurence.isLightBulbOn = False
            invisibleoccurences.append(component_occurence)
            app.activeViewport.refresh()
            time.sleep(0.5)

            # Create an extrude cut using the profile.
            extrudes = rootComp.features.extrudeFeatures
            extrudeInput = extrudes.createInput(profiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
            extrudeInput.targetBodies = [stock_body]
            # Define the extent: a distance extent downward into the stock.
            # We use NegativeExtentDirection so that the cut goes into the stock.
            distance = adsk.core.ValueInput.createByReal(-pocketDepth)  # Negative value goes downward
            extrudeInput.setDistanceExtent(False, distance)

            # Create the extrude (pocket cut)
            extrudeFeature = extrudes.add(extrudeInput)
            extrudeFeature.name = f"{component_occurence.name} Pocket"

            #Battery negative terminal
            if "battery" in component_occurence.name.lower():
                bottomprofiles = adsk.core.ObjectCollection.create()
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
                    sketches = stock_occurence.component.sketches
                    bottomSketch = sketches.add(bottomface)
                    bottomSketch.name = "Battery Negative Terminal"
                    bbox = bottomface.boundingBox
                    centerX = (bbox.minPoint.x + bbox.maxPoint.x) / 2
                    centerY = (bbox.minPoint.y + bbox.maxPoint.y) / 2
                    centerPoint = adsk.core.Point3D.create(centerX, centerY, 0)
                    radius = 4/mmtocm
                    bottomSketch.sketchCurves.sketchCircles.addByCenterRadius(centerPoint, radius)
                    minarea = float('inf')
                    minprofile = None
                    for profile in bottomSketch.profiles:
                        bb = profile.boundingBox
                        width = abs(bb.maxPoint.x - bb.minPoint.x)
                        length = abs(bb.maxPoint.y - bb.minPoint.y)
                        area = width * length
                        if area < minarea:
                            minarea = area
                            minprofile = profile
                    bottomprofiles.add(minprofile)
                    bottomSketch.isVisible = False
                    bottomextrudes = stock_occurence.component.features.extrudeFeatures
                    bottomextrudeInput = bottomextrudes.createInput(bottomprofiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
                    bottomextrudeInput.targetBodies = [stock_body]
                    # Define the extent: a distance extent downward into the stock.
                    # We use NegativeExtentDirection so that the cut goes into the stock.
                    distance = adsk.core.ValueInput.createByReal(-0.5/mmtocm)  # Negative value goes downward
                    bottomextrudeInput.setDistanceExtent(False, distance)

                    # Create the extrude (pocket cut)
                    bottomextrudeFeature = bottomextrudes.add(bottomextrudeInput)
                    bottomextrudeFeature.name = f"{component_occurence.name} Negative Terminal"

            #Chamfer component
            if chamferDepth > 0:
                topEdges = adsk.core.ObjectCollection.create()
                for sideFace in extrudeFeature.sideFaces:
                    for loop in sideFace.loops:
                        for edgeinloop in loop.edges:
                            startZ = edgeinloop.startVertex.geometry.z
                            endZ = edgeinloop.endVertex.geometry.z
                            if abs(startZ) < 0.05 and abs(endZ) < 0.05:
                                topEdges.add(edgeinloop)
                if topEdges.count > 0:
                    chamfers = rootComp.features.chamferFeatures
                    chamferinput = chamfers.createInput2()
                    chamferinput.chamferEdgeSets.addEqualDistanceChamferEdgeSet(topEdges, adsk.core.ValueInput.createByReal(chamferDepth), True)
                    chamferedpocket = chamfers.add(chamferinput)
                    chamferedpocket.name = f"{component_occurence.name} Chamfer"

            for occ in component_occurences:
                if occ != component_occurence:
                    occ.isLightBulbOn = True
            app.activeViewport.refresh()
            time.sleep(0.3)
            # ui.messageBox(f"Pocket cut for {component_occurence.name} has been created on the stock.")

        for occurence in invisibleoccurences:
            occurence.isLightBulbOn = True
        # ui.messageBox(f"Pocket cuts for all components have been created on the stock.")
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))