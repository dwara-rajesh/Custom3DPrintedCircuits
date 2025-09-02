snippetText = "snippet resourceSeize\n\
\tresourceSeize('${1:resource_name}')\n\
snippet resourceSeizeAGV\n\
\tresourceSeize('${1:resource_name}', '${2:agv}')\n\
snippet resourceRelease\n\
\tresourceRelease('${1:resource_name}')\n\
snippet urDashboard\n\
\turDashboard('${1:robot_name}', '${2:urp_file_path}')\n\
snippet cncRun\n\
\tcncRun('${1:cnc_name}', '${2:cnc_file}')\n\
snippet visionInspection\n\
\tvisionInspection('${1:camera}', '${2:solution_id}', '${3:output_variable}')\n\
snippet readyForAssembly\n\
\treadyForAssembly('${1:primary_process}', '${2:secondary_process}', ${3:assembly_step})\n\
snippet readyForAssemblyInit\n\
\treadyForAssembly('${1:primary_process}', '${2:secondary_process}', 'initializeAssembly')\n\
snippet readyForAssemblyStart\n\
\treadyForAssembly('${1:primary_process}', '${2:secondary_process}', 'startAssembly')\n\
snippet readyForAssemblyFinish\n\
\treadyForAssembly('${1:primary_process}', '${2:secondary_process}', 'finishAssembly')\n\
snippet startupTasksComplete\n\
\tstartupTasksComplete()\n\
snippet functionalPrinting()\n\
\tfunctionalPrinting()\n\
snippet dynamicfunctionalPrinting\n\
\tdynamicfunctionalPrinting('${1:schematic_filename}')\n\
snippet dynamicMachining\n\
\tdynamicMachining('${1:CNC_program_number}')\n\
";
/*
snippet dynamicfunctionalPrinting\n\ -> Snippet name for dynamicfunctionalPrinting() for autocomplete
\tdynamicfunctionalPrinting('${1:schematic_filename}')\n\ -> autocomplete syntax
snippet dynamicMachining\n\ -> Snippet name for dynamicfunctionalPrinting() for autocomplete
\tdynamicMachining('${1:CNC_program_number}')\n\ -> autocomplete syntax
*/