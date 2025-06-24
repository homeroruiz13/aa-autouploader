// === Begin Existing Code (unchanged) ===

function getMostRecentFolder(basePath) {
    var folder = new Folder(basePath);
    if (!folder.exists) {
        alert("Base folder not found: " + basePath);
        return null;
    }

    var subfolders = folder.getFiles(function(file) {
        // Ensure the file is a folder and matches the format YYYY-MM-DD_HH-MM-SS
        return file instanceof Folder && /^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(file.name);
    });

    if (subfolders.length === 0) {
        alert("No valid subfolders with the correct format found in: " + basePath);
        return null;
    }

    // Sort subfolders by name (descending order)
    subfolders.sort(function(a, b) {
        return b.name.localeCompare(a.name);
    });

    // Return the most recent folder (first one after sorting)
    return subfolders[0];
}

// Get the script's directory
var scriptFile = new File($.fileName);
var scriptDir = scriptFile.parent;

// Define your base paths for Download and Output relative to the script
var downloadBasePath = scriptDir + "/Download";
var outputBasePath = scriptDir + "/Output";

// Get the most recent Download and Output folders
var downloadFolder = getMostRecentFolder(downloadBasePath);
var outputFolder = getMostRecentFolder(outputBasePath);

if (downloadFolder == null || outputFolder == null) {
    alert("Error: Could not locate the most recent Download or Output folder.");
    exit();
}

var patternFiles = Folder(downloadFolder).getFiles("*.png");

var mockupPaths = [
    scriptDir + "/Mockup/011.psd",
    scriptDir + "/Mockup/03_h.psd",
    scriptDir + "/Mockup/051_w.psd",
    scriptDir + "/Mockup/081_w.psd",
    scriptDir + "/Mockup/05 (2).psd"
];

var newMockupPath = scriptDir + "/Mockup/04 (2).psd";

// Process each pattern file
for (var i = 0; i < patternFiles.length; i++) {
    var patternFile = patternFiles[i];
    var baseName = patternFile.name.replace(".png", "");

    // Process with 011.psd for crossed rolls (_6 files)
    if (baseName.slice(-2) === "_6") {
        processMockup(mockupPaths[0], patternFile.fsName, outputFolder.fsName, baseName);
    }

    // Process _3 files with 05 (2).psd and one of the other mockups
    if (baseName.slice(-2) === "_6") {
        processMockup(mockupPaths[4], patternFile.fsName, outputFolder.fsName, baseName);
        var randomMockupPath = mockupPaths[Math.floor(Math.random() * 3) + 1];
        processMockup(randomMockupPath, patternFile.fsName, outputFolder.fsName, baseName);
        processMockup(newMockupPath, patternFile.fsName, outputFolder.fsName, baseName);
    }
    
    // --- NEW: Process the rolled image output using the new rolled mockup ---
    if (baseName.slice(-2) === "_6") {
        processRolledImage(baseName, patternFile.fsName, outputFolder.fsName);
    }
}

// Quit Photoshop using Action Manager
var idquit = charIDToTypeID("quit");
executeAction(idquit, undefined, DialogModes.ALL);

// --- Helper function to process regular mockups (unchanged) ---
function processMockup(mockupPath, patternPath, outputFolder, baseName) {
    var mockupFile = new File(mockupPath);
    if (!mockupFile.exists) {
        alert("Mockup file not found: " + mockupPath);
        return;
    }

    var mockupDoc = app.open(mockupFile);

    var targetLayers = [];
    if (mockupPath.indexOf("011.psd") !== -1) {
        try {
            var smartObjectGroup = mockupDoc.layerSets.getByName("Smart Object Layers");
            targetLayers.push(smartObjectGroup.artLayers.getByName("You Design 02"));
            targetLayers.push(smartObjectGroup.artLayers.getByName("You Design 01"));
        } catch (e) {
            alert("One or both target layers ('You Design 02' and 'You Design 01') are not Smart Objects or do not exist in mockup '" + mockupPath + "'.");
            mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
            return;
        }
    } else if (mockupPath.indexOf("05 (2).psd") !== -1) {
        try {
            var smartObjectGroup = mockupDoc.layerSets.getByName("Smart Object Layers");
            targetLayers.push(smartObjectGroup.artLayers.getByName("Your Design Here"));
        } catch (e) {
            alert("The target layer 'Your Design Here' is not a Smart Object or does not exist in mockup '" + mockupPath + "'.");
            mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
            return;
        }
    } else if (mockupPath.indexOf("04 (2).psd") !== -1) {
        try {
            var smartObjectGroup = mockupDoc.layerSets.getByName("Smart Object Layers");
            targetLayers.push(smartObjectGroup.artLayers.getByName("Box 01"));
            targetLayers.push(smartObjectGroup.artLayers.getByName("Box 02"));
            targetLayers.push(smartObjectGroup.artLayers.getByName("Box 03"));
        } catch (e) {
            alert("One or more target layers ('Box 01', 'Box 02', 'Box 03') are not Smart Objects or do not exist in mockup '" + mockupPath + "'.");
            mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
            return;
        }
    } else {
        try {
            targetLayers.push(mockupDoc.artLayers.getByName("Your Design Here"));
        } catch (e) {
            alert("The target layer 'Your Design Here' is not a Smart Object or does not exist in mockup '" + mockupPath + "'.");
            mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
            return;
        }
    }

    var patternFile = new File(patternPath);
    if (!patternFile.exists) {
        alert("Pattern file not found: " + patternPath);
        return;
    }

    for (var j = 0; j < targetLayers.length; j++) {
        try {
            mockupDoc.activeLayer = targetLayers[j];

            var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
            var desc4 = new ActionDescriptor();
            executeAction(idplacedLayerEditContents, desc4, DialogModes.NO);

            var psbDoc = app.activeDocument;
            var patternDoc = app.open(patternFile);
            var boundingBox = psbDoc.layers[0].bounds;
            var boundingBoxWidth = boundingBox[2] - boundingBox[0];
            var boundingBoxHeight = boundingBox[3] - boundingBox[1];

            var scaleFactor;
            if (mockupPath.indexOf("011.psd") !== -1) {
                scaleFactor = (boundingBoxHeight / patternDoc.height) * 73;
            } else {
                var widthRatio = boundingBoxWidth / patternDoc.width;
                var heightRatio = boundingBoxHeight / patternDoc.height;
                scaleFactor = Math.max(widthRatio, heightRatio) * 120;
            }

            patternDoc.resizeImage(null, null, scaleFactor, ResampleMethod.BICUBIC);

            patternDoc.selection.selectAll();
            patternDoc.selection.copy();
            patternDoc.close(SaveOptions.DONOTSAVECHANGES);

            app.activeDocument = psbDoc;
            var newLayer = psbDoc.artLayers.add();
            newLayer.move(psbDoc.layers[0], ElementPlacement.PLACEBEFORE);
            psbDoc.paste();

            var deltaX = (boundingBoxWidth - newLayer.bounds[2] + newLayer.bounds[0]) / 2;
            var deltaY = (boundingBoxHeight - newLayer.bounds[3] + newLayer.bounds[1]) / 2;
            newLayer.translate(boundingBox[0] + deltaX, boundingBox[1] + deltaY);

            if (psbDoc.layers.length > 1) {
                psbDoc.layers[1].remove();
            }

            psbDoc.save();
            psbDoc.close(SaveOptions.SAVECHANGES);
            app.activeDocument = mockupDoc;
        } catch (error) {
            alert("Failed to process pattern '" + patternPath + "' with mockup '" + mockupPath + "': " + error.toString());
        }
    }

    // Modify the final mockup export name based on _w or _h, or other mockup types
    var mockupName = mockupDoc.name.replace(/\.psd$/, "");
    var finalFileName = baseName + "_" + mockupName + ".png";

    // For _w and _h files, append _hero
    if (mockupName.indexOf("_w") !== -1 || mockupName.indexOf("_h") !== -1) {
        finalFileName = baseName + "_hero.png";
    } else if (mockupPath.indexOf("011.psd") !== -1) {
        finalFileName = baseName + "_011.png";  // Adjust for 011.psd
    } else if (mockupPath.indexOf("05 (2).psd") !== -1) {
        finalFileName = baseName + "_05-(2).png"; // Adjust for 05 (2).psd
    } else if (mockupPath.indexOf("04 (2).psd") !== -1) {
        finalFileName = baseName + "_04-(2).png"; // Adjust for 04 (2).psd
    }

    // Export the final image as PNG
    var outputPNGFileName = outputFolder + "\\" + finalFileName;
    var exportOptions = new ExportOptionsSaveForWeb();
    exportOptions.format = SaveDocumentType.PNG;
    exportOptions.PNG8 = false;
    exportOptions.quality = 100;
    mockupDoc.exportDocument(new File(outputPNGFileName), ExportType.SAVEFORWEB, exportOptions);

    mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
}

// === NEW: Added Function to Process Rolled Image ===
function processRolledImage(baseName, patternPath, outputFolder) {
    var errorLog = "Rolled image processing started\n";
    var originalRulerUnits;
    try {
        // Use the rolled mockup file (path remains unchanged)
        var fileRef = new File("C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\rolled.psd");
        if (!fileRef.exists) {
            throw new Error("Rolled mockup file not found at: " + fileRef.fsName);
        }
        errorLog += "Opening rolled mockup...\n";
        app.open(fileRef);
        $.sleep(1000);
        var doc = app.activeDocument;
        errorLog += "Template opened: " + doc.name + "\n";
        
        // Find the "CHANGE HERE ROLL" layer
        var targetLayer = null;
        for (var i = 0; i < doc.layers.length; i++) {
            errorLog += "Checking layer: " + doc.layers[i].name + "\n";
            if (doc.layers[i].name === "CHANGE HERE ROLL") {
                targetLayer = doc.layers[i];
                break;
            }
        }
        if (!targetLayer) {
            targetLayer = findLayerRecursive(doc);
        }
        if (!targetLayer) {
            throw new Error("Could not find the 'CHANGE HERE ROLL' layer in the document");
        }
        errorLog += "Found target layer: " + targetLayer.name + "\n";
        doc.activeLayer = targetLayer;
        errorLog += "Activated target layer\n";
        
        // Open the Smart Object contents
        try {
            errorLog += "Attempting to open smart object contents...\n";
            app.runMenuItem(stringIDToTypeID("placedLayerEditContents"));
        } catch (e) {
            errorLog += "Error using runMenuItem: " + e + "\nTrying alternative method...\n";
            var idEditSmartObject = stringIDToTypeID("editSmartObject");
            var desc = new ActionDescriptor();
            executeAction(idEditSmartObject, desc, DialogModes.NO);
        }
        $.sleep(2000);
        var soDoc = app.activeDocument;
        errorLog += "Smart Object opened: " + soDoc.name + "\n";
        
        // Use the current pattern file as the replacement image
        var newImageFile = new File(patternPath);
        if (!newImageFile.exists) {
            throw new Error("Replacement pattern file not found: " + newImageFile.fsName);
        }
        errorLog += "Opening replacement image...\n";
        var replacementDoc = app.open(newImageFile);
        errorLog += "Replacement image opened\n";
        
        // Set the preference to use pixels and copy the content
        originalRulerUnits = app.preferences.rulerUnits;
        app.preferences.rulerUnits = Units.PIXELS;
        replacementDoc.selection.selectAll();
        replacementDoc.selection.copy();
        errorLog += "Copied content from replacement image\n";
        replacementDoc.close(SaveOptions.DONOTSAVECHANGES);
        errorLog += "Replacement image closed\n";
        
        // Switch back to the Smart Object document and paste
        app.activeDocument = soDoc;
        // NEW CODE: Clear any extra pasted layers from the Smart Object
        if (soDoc.artLayers.length > 1) {
            for (var i = soDoc.artLayers.length - 1; i >= 1; i--) {
                soDoc.artLayers[i].remove();
            }
            errorLog += "Cleared extra layers from Smart Object\n";
        }
        var newLayer = soDoc.artLayers.add();
        newLayer.name = baseName;
        newLayer.move(soDoc.layers[0], ElementPlacement.PLACEBEFORE);
        soDoc.paste();
        errorLog += "Pasted content into new layer\n";
        
        // --- NEW TRANSFORM: Double the size and rotate 90° ---
        soDoc.activeLayer.resize(200, 200, AnchorPosition.TOPLEFT);
        soDoc.activeLayer.rotate(90, AnchorPosition.MIDDLECENTER);
        // -----------------------------------------------
        
        soDoc.activeLayer = soDoc.layers[0];
        soDoc.activeLayer.translate(-soDoc.activeLayer.bounds[0], -soDoc.activeLayer.bounds[1]);
        errorLog += "Positioned image at 0,0\n";
        
        // Resize the pasted layer to exactly 8592x8592 pixels
        var currentWidth = soDoc.activeLayer.bounds[2] - soDoc.activeLayer.bounds[0];
        var currentHeight = soDoc.activeLayer.bounds[3] - soDoc.activeLayer.bounds[1];
        errorLog += "Current layer dimensions: " + currentWidth + " x " + currentHeight + "\n";
        var widthScale = (8592 / currentWidth) * 100;
        var heightScale = (8592 / currentHeight) * 100;
        soDoc.activeLayer.resize(widthScale, heightScale, AnchorPosition.TOPLEFT);
        errorLog += "Resized layer to 8592x8592 pixels\n";
        
        // Save the Smart Object
        var saveOptions = new PhotoshopSaveOptions();
        saveOptions.embedColorProfile = true;
        saveOptions.maximizeCompatibility = true;
        soDoc.saveAs(soDoc.fullName, saveOptions, true);
        errorLog += "Smart Object saved\n";
        soDoc.close(SaveOptions.SAVECHANGES);
        errorLog += "Smart Object closed\n";
        
        // Save the main document and export as PNG into the output folder
        doc.save();
        errorLog += "Main document saved\n";
        var outputFileName = baseName + "_rolled.png";
        var outputFilePath = outputFolder + "\\" + outputFileName;
        var exportOptions = new ExportOptionsSaveForWeb();
        exportOptions.format = SaveDocumentType.PNG;
        exportOptions.PNG8 = false;
        exportOptions.quality = 100;
        doc.exportDocument(new File(outputFilePath), ExportType.SAVEFORWEB, exportOptions);
        errorLog += "Exported rolled image to " + outputFilePath + "\n";
        
        app.preferences.rulerUnits = originalRulerUnits;
        doc.close(SaveOptions.SAVECHANGES);
    } catch (e) {
        $.writeln("Error in rolled image processing: " + e.message + "\nLog:\n" + errorLog);
        if (typeof originalRulerUnits !== 'undefined') {
            app.preferences.rulerUnits = originalRulerUnits;
        }
    }
}
// Helper function to recursively find a layer by name ("CHANGE HERE ROLL")
function findLayerRecursive(layerContainer) {
    // Check if the current container has a 'layers' property
    if (!layerContainer.layers) {
        return null;
    }
    for (var i = 0; i < layerContainer.layers.length; i++) {
        var lyr = layerContainer.layers[i];
        if (lyr.name === "CHANGE HERE ROLL") {
            return lyr;
        }
        // If the layer is a group, search recursively
        if (lyr.typename === "LayerSet") {
            var found = findLayerRecursive(lyr);
            if (found) {
                return found;
            }
        }
    }
    return null;
}

// === End of File ===
