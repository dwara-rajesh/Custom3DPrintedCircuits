import adsk.core, adsk.fusion, adsk.cam, traceback,os

inchtocm = 2.54
def count_files(folder):
    """Counts the number of .nc files in a given directory using os module."""
    count = 0
    for filename in os.listdir(folder):
        if filename.endswith(".nc"):
            count += 1
    return count

def add_footer(filepath,ui):
    with open(filepath, 'r') as file:
        lines = file.readlines()

    for i in range(len(lines)):
        if "M30" in lines[i]:
            footerindex = i
    lines.insert(footerindex, "M98 P9004\n")

    with open(filepath, 'w') as file:
        file.writelines(lines)

def set_operation_parameters(opInput, operation_name):
    global inchtocm
    opInput.parameters.itemByName('clearanceHeight_mode').value.value = 'from retract height'
    opInput.parameters.itemByName('clearanceHeight_offset').value.value = 0.393701 * inchtocm

    opInput.parameters.itemByName('retractHeight_mode').value.value = 'from highest of'
    opInput.parameters.itemByName('retractHeightFromHighest_checkStock').value.value = 'top'
    opInput.parameters.itemByName('retractHeightFromHighest_checkModel').value.value = 'top'
    opInput.parameters.itemByName('retractHeightFromHighest_checkFixture').value.value = 'top'
    opInput.parameters.itemByName('retractHeight_offset').value.value = 0.19685 * inchtocm

    if operation_name == "trace":
        opInput.parameters.itemByName('feedHeight_mode').value.value = 'from highest of'
        opInput.parameters.itemByName('feedHeightFromHighest_checkStock').value.value = 'ignore'
        opInput.parameters.itemByName('feedHeightFromHighest_checkModel').value.value = 'top'
        opInput.parameters.itemByName('feedHeightFromHighest_checkFixture').value.value = 'ignore'
        opInput.parameters.itemByName('feedHeight_offset').value.value = 0.19685 * inchtocm
    else:
        opInput.parameters.itemByName('feedHeight_mode').value.value = 'from top'
        opInput.parameters.itemByName('feedHeight_offset').value.value = 0.19685 * inchtocm

        opInput.parameters.itemByName('topHeight_mode').value.value = 'from highest of'
        opInput.parameters.itemByName('topHeightFromHighest_checkStock').value.value = 'top'
        opInput.parameters.itemByName('topHeightFromHighest_checkModel').value.value = 'ignore'
        opInput.parameters.itemByName('topHeightFromHighest_checkFixture').value.value = 'ignore'
        opInput.parameters.itemByName('topHeight_offset').value.value = 0.0 * inchtocm

        opInput.parameters.itemByName('bottomHeight_mode').value.value = 'from contour'
        opInput.parameters.itemByName('bottomHeight_offset').value.value = 0.0 * inchtocm

    if operation_name == "pocket" or operation_name == "t10pocket":
        opInput.parameters.itemByName('tolerance').value.value = 0.00393701 * inchtocm
    elif operation_name == "trace":
        opInput.parameters.itemByName('tolerance').value.value = 0.000393701 * inchtocm
        opInput.parameters.itemByName('passExtension').value.value = 0
    elif operation_name == "contour":
        opInput.parameters.itemByName('tolerance').value.value = 0.00039370 * inchtocm

    if operation_name == "trace":
        opInput.parameters.itemByName('compensation').value.value = 'center'
        opInput.parameters.itemByName('nullPass').value.value = True
        opInput.parameters.itemByName('preserveOrder').value.value = True
    else:
        opInput.parameters.itemByName('compensation').value.value = 'left'
        if operation_name == "contour":
            opInput.parameters.itemByName('compensationType').value.value = 'computer'
            opInput.parameters.itemByName('finishingSmoothingDeviation').value.value  = 0.0 * inchtocm
            opInput.parameters.itemByName('doMultipleFinishingPasses').value.value = False
            opInput.parameters.itemByName('finishFeedrate').value.value = 25 * inchtocm * 10 #Takes mm/min as input so convert inch to mm
            opInput.parameters.itemByName('nullPass').value.value = True
            opInput.parameters.itemByName('finishingOverlap').value.value = 0
            opInput.parameters.itemByName('leadEndDistance').value.value = 0
            opInput.parameters.itemByName('cornerMode').value.value = 'roll'
            opInput.parameters.itemByName('tangentialFragmentExtensionDistance').value.value = 0

        opInput.parameters.itemByName('minimumCuttingRadius').value.value = 0.0 * inchtocm
        opInput.parameters.itemByName('preserveOrder').value.value = False

    opInput.parameters.itemByName('bothWays').value.value = False

    if operation_name == "trace":
        opInput.parameters.itemByName('maximumAngle').value.value = 90
        opInput.parameters.itemByName('axialOffset').value.value = 0
        opInput.parameters.itemByName('upDownMilling').value.value = 'dont care'

    if operation_name == "pocket":
        opInput.parameters.itemByName('maximumStepover').value.value = 0.075 * inchtocm
        opInput.parameters.itemByName('doMultipleDepths').value.value = True
        opInput.parameters.itemByName('maximumStepdown').value.value = 0.0625 * inchtocm
        opInput.parameters.itemByName('numberOfFinishingStepdowns').value.value = 0
        opInput.parameters.itemByName('finishingStepdown').value.value = 0.00787402 * inchtocm
        opInput.parameters.itemByName('slopeAngle').value.value = 0.0
        opInput.parameters.itemByName('useEvenStepdowns').value.value = True
        opInput.parameters.itemByName('orderByDepth').value.value = False
        opInput.parameters.itemByName('orderByStep').value.value = False
    elif operation_name == "t10pocket":
        opInput.parameters.itemByName('maximumStepover').value.value = 0.0375 * inchtocm
        opInput.parameters.itemByName('doMultipleDepths').value.value = False
    else:
        if operation_name == "contour":
            opInput.parameters.itemByName('doRoughingPasses').value.value = False

        opInput.parameters.itemByName('doMultipleDepths').value.value = False

    if operation_name == "pocket" or operation_name == "t10pocket":
        opInput.parameters.itemByName('useMorphedSpiralMachining').value.value = False
        opInput.parameters.itemByName('allowStepoverCusps').value.value = False
        opInput.parameters.itemByName('smoothingDeviation').value.value = 0.00393701 * inchtocm
        opInput.parameters.itemByName('doFinishingPasses').value.value = False

    opInput.parameters.itemByName('useStockToLeave').value.value = False
    opInput.parameters.itemByName('smoothingFilter').value.value = False
    opInput.parameters.itemByName('useFeedOptimization').value.value = False

    if operation_name == "trace":
        opInput.parameters.itemByName('retractionPolicy').value.value = 'full'

    opInput.parameters.itemByName('highFeedrateMode').value.value = 'disabled'

    if operation_name != "trace":
        opInput.parameters.itemByName('allowRapidRetract').value.value = True

    if operation_name == "pocket":
        opInput.parameters.itemByName('safeDistance').value.value = 0.025 * inchtocm
        opInput.parameters.itemByName('keepToolDown').value.value = True
        opInput.parameters.itemByName('stayDownDistance').value.value = 1.9685 * inchtocm
        opInput.parameters.itemByName('liftHeight').value.value = 0.0 * inchtocm
    elif operation_name == "t10pocket":
        opInput.parameters.itemByName('safeDistance').value.value = 0.0125 * inchtocm
        opInput.parameters.itemByName('keepToolDown').value.value = True
        opInput.parameters.itemByName('stayDownDistance').value.value = 1.9685 * inchtocm
        opInput.parameters.itemByName('liftHeight').value.value = 0.0 * inchtocm
    elif operation_name == "trace":
        opInput.parameters.itemByName('safeDistance').value.value = 0.0787402 * inchtocm
        opInput.parameters.itemByName('keepToolDown').value.value = False
    elif operation_name == "contour":
        opInput.parameters.itemByName('safeDistance').value.value = 0.0393701 * inchtocm
        opInput.parameters.itemByName('keepToolDown').value.value = False
        opInput.parameters.itemByName('liftHeight').value.value = 0.0 * inchtocm

    if operation_name == "trace":
        opInput.parameters.itemByName('doLeadIn').value.value = False
        opInput.parameters.itemByName('doLeadOut').value.value = False
    else:
        opInput.parameters.itemByName('doLeadIn').value.value = True

    if operation_name == "pocket":
        opInput.parameters.itemByName('entry_radius').value.value = 0.0125 * inchtocm
        opInput.parameters.itemByName('entry_distance').value.value = 0.0125 * inchtocm
        opInput.parameters.itemByName('entry_verticalRadius').value.value = 0.0125 * inchtocm
    elif operation_name == "t10pocket":
        opInput.parameters.itemByName('entry_radius').value.value = 0.00625 * inchtocm
        opInput.parameters.itemByName('entry_distance').value.value = 0.00625 * inchtocm
        opInput.parameters.itemByName('entry_verticalRadius').value.value = 0.00625 * inchtocm
    elif operation_name == "contour":
        opInput.parameters.itemByName('entry_radius').value.value = 0.025 * inchtocm
        opInput.parameters.itemByName('entry_distance').value.value = 0.025 * inchtocm
        opInput.parameters.itemByName('entry_verticalRadius').value.value = 0.025 * inchtocm

    if operation_name != "trace":
        opInput.parameters.itemByName('entry_sweep').value.value = 90.0
        opInput.parameters.itemByName('entry_perpendicular').value.value = False

        opInput.parameters.itemByName('doLeadOut').value.value = True
        opInput.parameters.itemByName('exit_sameAsEntry').value.value = True

        if operation_name == "contour":
            opInput.parameters.itemByName('doRamp').value.value = False
        else:
            opInput.parameters.itemByName('rampType').value.value = 'plunge'
            opInput.parameters.itemByName('rampClearanceHeight').value.value = 0.0984252 * inchtocm
            opInput.parameters.itemByName('rampRadialClearance').value.value = 0.0 * inchtocm

    return opInput

def run(context):
    global inchtocm
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent
        stock_occ = None
        for occ in rootComp.occurrences:
            if 'stock' in occ.name.lower():
                stock_occ = occ
            else:
                occ.isLightBulbOn = False

        camWS = ui.workspaces.itemById('CAMEnvironment')
        camWS.activate()
        cam = adsk.cam.CAM.cast(app.activeProduct)

        # Create a setup
        setups = cam.setups
        setupInput = setups.createInput(adsk.cam.OperationTypes.MillingOperation)

        setupInput.parameters.itemByName('wcs_orientation_mode').value.value = 'modelOrientation'
        setupInput.parameters.itemByName('wcs_origin_mode').value.value = 'modelPoint'
        setupInput.parameters.itemByName('wcs_origin_boxPoint').value.value = 'bottom 4'

        setupInput.models = [stock_occ.bRepBodies.item(0)]

        setupInput.parameters.itemByName('job_stockMode').value.value = 'default'
        setupInput.parameters.itemByName('job_stockOffsetMode').value.value = 'keep'

        # setupInput.parameters.itemByName('job_programName').value.value = '1001'
        # setupInput.parameters.itemByName('job_programComment').value.value = 'Automatic CAM for Circuit'
        setupInput.parameters.itemByName('job_workOffset').value.value = 1
        setupInput.parameters.itemByName('job_multipleWorkOffsets').value.value = False

        setup = setups.add(setupInput)


        # Get a reference to the CAMManager object.
        camMgr = adsk.cam.CAMManager.get()
        # Get the ToolLibraries object.
        toolLibs = camMgr.libraryManager.toolLibraries
        # Get the URL for the local libraries.
        localLibLocationURL = toolLibs.urlByLocation(adsk.cam.LibraryLocations.LocalLibraryLocation)
        f360LibraryURLs = toolLibs.childAssetURLs(localLibLocationURL)
        toolLib = None
        for libURL in f360LibraryURLs:
            if 'CircuitPrintingToolLibrary' in libURL.leafName:
                toolLib = toolLibs.toolLibraryAtURL(libURL)

        selectedtool = None
        # Find a specific tool.
        for tool in toolLib:
            if tool.parameters.itemByName('tool_description').value.value == 'Tool1':
                selectedtool = tool
                break

        #Pocket2D
        pocketOpInput = setup.operations.createInput('pocket2d')
        pocketOpInput.tool = selectedtool
        pocketOpInput.toolPreset = selectedtool.presets.itemsByName('Pocket&PathCutting')[0]

        pocketcurves = pocketOpInput.parameters.itemByName('pockets').value.getCurveSelections()

        stockextrudes = stock_occ.component.features.extrudeFeatures

        for stockext in stockextrudes:
            if "pocket" in stockext.name.lower() or "wire" in stockext.name.lower():
                pocket = stockext.endFaces.item(0)
                pocket_pockets = pocketcurves.createNewPocketSelection()
                pocket_pockets.isSelectingSamePlaneFaces = False
                pocket_pockets.inputGeometry = [pocket]
                pocketOpInput.parameters.itemByName('pockets').value.applyCurveSelections(pocketcurves)

        pocketOpInput = set_operation_parameters(pocketOpInput, "pocket")
        PocketOp = setup.operations.add(pocketOpInput)
        cam.generateToolpath(PocketOp)
        while not PocketOp.isToolpathValid:
            adsk.doEvents()

        #Trace
        TraceOpInput = setup.operations.createInput('trace')
        TraceOpInput.tool = selectedtool
        TraceOpInput.toolPreset = selectedtool.presets.itemsByName('NegativeTerminalPathCutting')[0]

        tracecurves = TraceOpInput.parameters.itemByName('curves').value.getCurveSelections()

        stocksweeps = stock_occ.component.features.sweepFeatures
        tracepaths = []
        for stocksweep in stocksweeps:
            if "sweep" in stocksweep.name.lower():
                stocksweep.timelineObject.rollTo(True)
                tracepath = stocksweep.path
                design.timeline.moveToEnd()
                for i in range(tracepath.count):
                    tracepaths.append(tracepath.item(i).entity)

        planes = stock_occ.component.constructionPlanes
        numtraces = int(len(tracepaths)/4)
        wireidxpairs = []
        for i in range(numtraces):
            target_plane = None
            if i == 0:
                planename = "Mid Plane 1"
            else:
                planename = f"Mid Plane 1 ({i})"
            for plane in planes:
                if plane.name == planename:
                    target_plane = plane
                    break
            sketch = stock_occ.component.sketches.add(target_plane)
            sketch.name = f"Sketch creaed on {target_plane.name}"
            startptsweep2projected = sketch.project(tracepaths[(i*4) + 1].startSketchPoint)
            endptsweep1projected = sketch.project(tracepaths[(i*4)].startSketchPoint)
            startptsweep2 = adsk.fusion.SketchPoint.cast(startptsweep2projected.item(0))
            endptsweep1 = adsk.fusion.SketchPoint.cast(endptsweep1projected.item(0))

            connected = sketch.sketchCurves.sketchLines.addByTwoPoints(endptsweep1.geometry, startptsweep2.geometry)

            pair = {"connection": connected, "index": (i*4) + 1}
            wireidxpairs.append(pair)

            sketch.isVisible = False

        for wireidxpair in wireidxpairs:
            tracepaths.insert(wireidxpair["index"], wireidxpair["connection"])

        for tracepath in tracepaths:
            tracelines = tracecurves.createNewChainSelection()
            tracelines.inputGeometry = [tracepath]
            TraceOpInput.parameters.itemByName('curves').value.applyCurveSelections(tracecurves)


        TraceOpInput = set_operation_parameters(TraceOpInput, "trace")

        TraceOp = setup.operations.add(TraceOpInput)
        cam.generateToolpath(TraceOp)
        while not TraceOp.isToolpathValid:
            adsk.doEvents()

        #2DContour
        stockchamfers = stock_occ.component.features.chamferFeatures
        for stockchamfer in stockchamfers:
            if "chamfer" in stockchamfer.name.lower():
                selectedtool = None
                # Find a specific tool.
                for tool in toolLib:
                    if tool.parameters.itemByName('tool_description').value.value == 'Tool5':
                        selectedtool = tool
                        break

                Contour2dOpInput = setup.operations.createInput('contour2d')
                Contour2dOpInput.tool = selectedtool
                contourselection = Contour2dOpInput.parameters.itemByName('contours').value.getCurveSelections()

                Contour2dOpInput = set_operation_parameters(Contour2dOpInput, "contour")

                if "led" in stockchamfer.name.lower():
                    bottomedges = []
                    for i in range(stockchamfer.faces.count):
                        face = stockchamfer.faces.item(i)
                        bottomedge = None
                        minZ = float('inf')
                        for i in range(face.edges.count):
                            edge = face.edges.item(i)
                            point_on_edge = edge.pointOnEdge
                            if point_on_edge.z < minZ:
                                minZ = point_on_edge.z
                                bottomedge = edge
                        if bottomedge:
                            bottomedges.append(bottomedge)

                    if bottomedges:
                        for edge in bottomedges:
                            contourlines = contourselection.createNewChainSelection()
                            contourlines.inputGeometry = [edge]
                            contourlines.isReverted = True
                            Contour2dOpInput.parameters.itemByName('contours').value.applyCurveSelections(contourselection)

                    #setup heights
                    Contour2dOpInput.parameters.itemByName('doChamfer').value.value = True
                    Contour2dOpInput.parameters.itemByName('chamferWidth').value.value = 0
                    Contour2dOpInput.parameters.itemByName('chamferTipOffset').value.value = 0
                    Contour2dOpLED = setup.operations.add(Contour2dOpInput)
                    cam.generateToolpath(Contour2dOpLED)
                    while not Contour2dOpLED.isToolpathValid:
                        adsk.doEvents()

                elif "button" in stockchamfer.name.lower():
                    bottomedges = []
                    for i in range(stockchamfer.faces.count):
                        face = stockchamfer.faces.item(i)
                        bottomedge = None
                        minZ = float('inf')
                        for i in range(face.edges.count):
                            edge = face.edges.item(i)
                            point_on_edge = edge.pointOnEdge
                            if point_on_edge.z < minZ:
                                minZ = point_on_edge.z
                                bottomedge = edge
                        if bottomedge:
                            bottomedges.append(bottomedge)

                    if bottomedges:
                        for edge in bottomedges:
                            contourlines = contourselection.createNewChainSelection()
                            contourlines.inputGeometry = [edge]
                            contourlines.isReverted = True
                            Contour2dOpInput.parameters.itemByName('contours').value.applyCurveSelections(contourselection)

                    #setup heights
                    Contour2dOpInput.parameters.itemByName('doChamfer').value.value = True
                    Contour2dOpInput.parameters.itemByName('chamferWidth').value.value = 0
                    Contour2dOpInput.parameters.itemByName('chamferTipOffset').value.value = 0.011811 * inchtocm
                    Contour2dOpButton = setup.operations.add(Contour2dOpInput)
                    cam.generateToolpath(Contour2dOpButton)
                    while not Contour2dOpButton.isToolpathValid:
                        adsk.doEvents()


        #2DPocket Final Touch Up
        for tool in toolLib:
            if tool.parameters.itemByName('tool_description').value.value == 'Tool10':
                selectedtool = tool
                break

        #Pocket2D
        pocketOpInput = setup.operations.createInput('pocket2d')
        pocketOpInput.tool = selectedtool

        pocketcurves = pocketOpInput.parameters.itemByName('pockets').value.getCurveSelections()

        stockextrudes = stock_occ.component.features.extrudeFeatures

        for stockext in stockextrudes:
            if "pocket" in stockext.name.lower() and "battery" not in stockext.name.lower():
                pocket = stockext.endFaces.item(0)
                pocket_pockets = pocketcurves.createNewPocketSelection()
                pocket_pockets.isSelectingSamePlaneFaces = False
                pocket_pockets.inputGeometry = [pocket]
                pocketOpInput.parameters.itemByName('pockets').value.applyCurveSelections(pocketcurves)

        pocketOpInput = set_operation_parameters(pocketOpInput, "t10pocket")
        pocketOp = setup.operations.add(pocketOpInput)
        cam.generateToolpath(pocketOp)
        while not pocketOp.isToolpathValid:
            adsk.doEvents()

        # Get the PostConfiguration Manager object.
        postConfigLib = camMgr.libraryManager.postLibrary
        # Get the URL for the local libraries.
        localPCLibLocationURL = postConfigLib.urlByLocation(adsk.cam.LibraryLocations.LocalLibraryLocation)
        f360PCLibraryURLs = postConfigLib.childAssetURLs(localPCLibLocationURL)
        postConfig = None
        for libURL in f360PCLibraryURLs:
            if 'haas' in libURL.leafName:
                postConfig = postConfigLib.postConfigurationAtURL(libURL)

        outputfolder = "D:/BU/Internship/GUICADCAM Python/Custom3DPrintedCircuits/NCPrograms"
        programName = None
        while programName is None:
            programName_save = ui.inputBox('Please enter filename:', 'Enter Filename')
            if programName_save[0]:
                (programName,cancelled) = programName_save
                if cancelled:
                    programName = None

        programComment = 'Automatic CAM Program'

        programNumber_base = 10005
        num_nc_files = count_files(outputfolder)
        programNumber = programNumber_base + num_nc_files
        ncPrograms = cam.ncPrograms
        ncProgramInput = ncPrograms.createInput()
        ncProgramInput.displayName = programName
        ncProgramInput.operations = list(setup.operations)

        ncParameters = ncProgramInput.parameters

        ncParameters.itemByName('nc_program_comment').value.value = programName
        ncParameters.itemByName('nc_program_name').value.value = f'{programNumber}'
        ncParameters.itemByName('nc_program_filename').value.value = programName
        ncParameters.itemByName('nc_program_unit').value.value = 'Inches' #adsk.cam.PostOutputUnitOptions.InchesOutput
        ncParameters.itemByName('nc_program_output_folder').value.value = outputfolder
        ncParameters.itemByName('nc_program_openInEditor').value.value = True

        ncProgram = ncPrograms.add(ncProgramInput)
        ncProgram.postConfiguration = postConfig

        postprocessparams = ncProgram.postParameters
        postprocessparams.itemByName('optionalStop').value.value = False
        ncProgram.updatePostParameters(postprocessparams)
        postOptions = adsk.cam.NCProgramPostProcessOptions.create()
        ncProgram.postProcess(postOptions)

        add_footer(outputfolder +"/" + programName + ".nc",ui)
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


#2D Pocket - Tool1 - for pocket cutting of all components and wire path
    #Tool - #1 - Phi 1/8" flat (1/8 in)
#Trace - Tool1 - for negative terminal of battery
    #Tool - #1 - Phi 1/8" flat (1/8 in) - 2nd preset - negative something something
#2D Contour - Tool5 - LED - edge clearing for LED
    #Tool - #5 - Phi 1/4" 90 deg spot drill
#2D Contour - Tool5 - Button - edge clearing for button
    #Tool - #5 - Phi 1/4" 90 deg spot drill
#2D Pocket - Tool10 - final touch up
    #Tool - #10 - phi 1/16" flat (1/16 in)