// === Begin Improved Code with Optimized Sleep Times ===

// Error logging setup
var logFile = new File(Folder.desktop + "/photoshop_script_log.txt");
logFile.open("w");
function logMessage(message) {
    logFile.writeln(new Date().toLocaleString() + ": " + message);
    $.writeln(message);
}

function getMostRecentFolder(basePath) {
    try {
        var folder = new Folder(basePath);
        if (!folder.exists) {
            logMessage("Base folder not found: " + basePath);
            return null;
        }

        var subfolders = folder.getFiles(function(file) {
            // Ensure the file is a folder and matches the format YYYY-MM-DD_HH-MM-SS
            return file instanceof Folder && /^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(file.name);
        });

        if (subfolders.length === 0) {
            logMessage("No valid subfolders with the correct format found in: " + basePath);
            return null;
        }

        // Sort subfolders by name (descending order)
        subfolders.sort(function(a, b) {
            return b.name.localeCompare(a.name);
        });

        // Return the most recent folder (first one after sorting)
        logMessage("Found most recent folder: " + subfolders[0].fsName);
        return subfolders[0];
    } catch (e) {
        logMessage("Error in getMostRecentFolder: " + e.message);
        return null;
    }
}

// Main Script Execution
try {
    logMessage("=== Starting Photoshop batch processing ===");
    
    // Define your base paths for Download and Output
    var downloadBasePath = "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Download";
    var outputBasePath = "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Output";

    // Get the most recent Download and Output folders
    var downloadFolder = getMostRecentFolder(downloadBasePath);
    var outputFolder = getMostRecentFolder(outputBasePath);

    if (downloadFolder == null || outputFolder == null) {
        logMessage("Error: Could not locate the most recent Download or Output folder.");
        logFile.close();
        exit();
    }

    logMessage("Using download folder: " + downloadFolder.fsName);
    logMessage("Using output folder: " + outputFolder.fsName);

    var patternFiles = Folder(downloadFolder).getFiles(function(file) {
        return file instanceof File && file.name.match(/\.png$/i);
    });

    logMessage("Found " + patternFiles.length + " pattern files to process");

    var mockupPaths = [
        "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\011.psd",
        "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\03_h.psd",
        "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\051_w.psd",
        "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\081_w.psd",
        "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\05 (2).psd"
    ];

    var newMockupPath = "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\04 (2).psd";

    // Verify the mockup files exist
    for (var i = 0; i < mockupPaths.length; i++) {
        var mockupFile = new File(mockupPaths[i]);
        if (!mockupFile.exists) {
            logMessage("Warning: Mockup file not found: " + mockupPaths[i]);
        }
    }

    var newMockupFile = new File(newMockupPath);
    if (!newMockupFile.exists) {
        logMessage("Warning: New mockup file not found: " + newMockupPath);
    }

    // Process each pattern file
    for (var i = 0; i < patternFiles.length; i++) {
        var patternFile = patternFiles[i];
        var baseName = patternFile.name.replace(".png", "");

        logMessage("Processing file " + (i+1) + "/" + patternFiles.length + ": " + baseName);

        // Process with 011.psd for crossed rolls (_6 files)
        if (baseName.slice(-2) === "_6") {
            logMessage("Processing " + baseName + " with mockup 011.psd");
            processMockup(mockupPaths[0], patternFile.fsName, outputFolder.fsName, baseName);
            
            // Process _6 files with 05 (2).psd and one of the other mockups
            logMessage("Processing " + baseName + " with mockup 05 (2).psd");
            processMockup(mockupPaths[4], patternFile.fsName, outputFolder.fsName, baseName);
            
            var randomIndex = Math.floor(Math.random() * 3) + 1;
            logMessage("Processing " + baseName + " with random mockup: " + mockupPaths[randomIndex]);
            processMockup(mockupPaths[randomIndex], patternFile.fsName, outputFolder.fsName, baseName);
            
            logMessage("Processing " + baseName + " with new mockup: " + newMockupPath);
            processMockup(newMockupPath, patternFile.fsName, outputFolder.fsName, baseName);
            
            // Process the rolled image output
            logMessage("Processing " + baseName + " as rolled image");
            processRolledImage(baseName, patternFile.fsName, outputFolder.fsName);
        } else {
            logMessage("Skipping " + baseName + " (not a _6 file)");
        }
    }

    logMessage("All processing complete. Closing Photoshop.");
    logFile.close();

    // Quit Photoshop using Action Manager
    var idquit = charIDToTypeID("quit");
    executeAction(idquit, undefined, DialogModes.ALL);
} catch (e) {
    logMessage("FATAL ERROR: " + e.message + " (line " + e.line + ")");
    logFile.close();
}

// --- Helper function to process regular mockups (optimized with reduced sleep times) ---
function processMockup(mockupPath, patternPath, outputFolder, baseName) {
    try {
        logMessage("[INFO] Starting processMockup for " + baseName + " with " + mockupPath);
        var mockupFile = new File(mockupPath);
        if (!mockupFile.exists) {
            logMessage("Mockup file not found: " + mockupPath);
            return;
        }

        logMessage("[INFO] Opening mockup document: " + mockupPath);
        var mockupDoc = app.open(mockupFile);
        // Wait for document to open completely - reduced sleep time
        $.sleep(300);

        var targetLayers = [];
        if (mockupPath.indexOf("011.psd") !== -1) {
            try {
                logMessage("[INFO] Finding layers in 011.psd");
                var smartObjectGroup = mockupDoc.layerSets.getByName("Smart Object Layers");
                targetLayers.push(smartObjectGroup.artLayers.getByName("You Design 02"));
                targetLayers.push(smartObjectGroup.artLayers.getByName("You Design 01"));
            } catch (e) {
                logMessage("Error finding layers in 011.psd: " + e.message);
                mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
                return;
            }
        } else if (mockupPath.indexOf("05 (2).psd") !== -1) {
            try {
                logMessage("[INFO] Finding layers in 05 (2).psd");
                var smartObjectGroup = mockupDoc.layerSets.getByName("Smart Object Layers");
                targetLayers.push(smartObjectGroup.artLayers.getByName("Your Design Here"));
            } catch (e) {
                logMessage("Error finding layers in 05 (2).psd: " + e.message);
                mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
                return;
            }
        } else if (mockupPath.indexOf("04 (2).psd") !== -1) {
            try {
                logMessage("[INFO] Finding layers in 04 (2).psd");
                var smartObjectGroup = mockupDoc.layerSets.getByName("Smart Object Layers");
                targetLayers.push(smartObjectGroup.artLayers.getByName("Box 01"));
                targetLayers.push(smartObjectGroup.artLayers.getByName("Box 02"));
                targetLayers.push(smartObjectGroup.artLayers.getByName("Box 03"));
            } catch (e) {
                logMessage("Error finding layers in 04 (2).psd: " + e.message);
                mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
                return;
            }
        } else {
            try {
                logMessage("[INFO] Finding 'Your Design Here' layer");
                targetLayers.push(mockupDoc.artLayers.getByName("Your Design Here"));
            } catch (e) {
                logMessage("Error finding 'Your Design Here' layer in " + mockupPath + ": " + e.message);
                mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
                return;
            }
        }

        var patternFile = new File(patternPath);
        if (!patternFile.exists) {
            logMessage("Pattern file not found: " + patternPath);
            mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
            return;
        }

        for (var j = 0; j < targetLayers.length; j++) {
            try {
                logMessage("[INFO] Processing target layer " + (j+1) + "/" + targetLayers.length + ": " + targetLayers[j].name);
                
                // Make sure the layer is actually selected
                mockupDoc.activeLayer = targetLayers[j];
                $.sleep(100);  // REDUCED - Give Photoshop time to update

                logMessage("[INFO] Editing smart object contents");
                // Edit the smart object contents
                var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
                var desc4 = new ActionDescriptor();
                executeAction(idplacedLayerEditContents, desc4, DialogModes.NO);
                $.sleep(300);  // REDUCED - Wait for smart object to open

                var psbDoc = app.activeDocument;
                // Wait for any document operations to complete
                $.sleep(100);  // REDUCED

                logMessage("[INFO] Opening pattern file: " + patternPath);
                var patternDoc = app.open(patternFile);
                $.sleep(100);  // REDUCED - Wait for pattern to open

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

                logMessage("[INFO] Resizing pattern to scale factor: " + scaleFactor);
                patternDoc.resizeImage(null, null, scaleFactor, ResampleMethod.BICUBIC);
                $.sleep(200);  // REDUCED - Wait for resize to complete

                logMessage("[INFO] Copying pattern content");
                patternDoc.selection.selectAll();
                patternDoc.selection.copy();
                patternDoc.close(SaveOptions.DONOTSAVECHANGES);
                $.sleep(100);  // REDUCED - Wait for close to complete

                logMessage("[INFO] Pasting content into smart object");
                app.activeDocument = psbDoc;
                var newLayer = psbDoc.artLayers.add();
                newLayer.name = "Pattern Layer";
                newLayer.move(psbDoc.layers[0], ElementPlacement.PLACEBEFORE);
                $.sleep(100); // REDUCED
                psbDoc.paste();
                $.sleep(200);  // REDUCED - Wait for paste to complete

                var deltaX = (boundingBoxWidth - newLayer.bounds[2] + newLayer.bounds[0]) / 2;
                var deltaY = (boundingBoxHeight - newLayer.bounds[3] + newLayer.bounds[1]) / 2;
                logMessage("[INFO] Positioning layer with translation: " + deltaX + ", " + deltaY);
                newLayer.translate(boundingBox[0] + deltaX, boundingBox[1] + deltaY);
                $.sleep(100);  // REDUCED - Wait for translate to complete

                if (psbDoc.layers.length > 1 && psbDoc.layers[1].name !== "Pattern Layer") {
                    logMessage("[INFO] Removing extra layer");
                    psbDoc.layers[1].remove();
                    $.sleep(100);  // REDUCED - Wait for layer removal
                }

                logMessage("[INFO] Saving smart object");
                psbDoc.save();
                $.sleep(300);  // REDUCED - Wait for save to complete
                psbDoc.close(SaveOptions.SAVECHANGES);
                $.sleep(300);  // REDUCED - Wait for close to complete
                
                app.activeDocument = mockupDoc;
                $.sleep(100);  // REDUCED - Wait for document to become active
            } catch (error) {
                logMessage("Error processing layer " + targetLayers[j].name + ": " + error.message);
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
        
        try {
            logMessage("[INFO] Exporting final image to: " + outputPNGFileName);
            mockupDoc.exportDocument(new File(outputPNGFileName), ExportType.SAVEFORWEB, exportOptions);
            logMessage("[SUCCESS] Exported: " + outputPNGFileName);
        } catch (e) {
            logMessage("Error exporting " + finalFileName + ": " + e.message);
        }

        mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
        $.sleep(300);  // REDUCED - Wait for document to close completely
        
    } catch (e) {
        logMessage("Error in processMockup: " + e.message);
        if (app.documents.length > 0) {
            app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
        }
    }
}

// === Original Rolled Image Processing Function that is KNOWN TO WORK ===
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
        logMessage("Opening rolled mockup template");
        app.open(fileRef);
        $.sleep(2000);  // Increased wait time for template to open
        
        var doc = app.activeDocument;
        errorLog += "Template opened: " + doc.name + "\n";
        logMessage("Template opened: " + doc.name);
        
        // Find the "CHANGE HERE ROLL" layer
        var targetLayer = null;
        
        // First try direct approach
        for (var i = 0; i < doc.layers.length; i++) {
            errorLog += "Checking layer: " + doc.layers[i].name + "\n";
            if (doc.layers[i].name === "CHANGE HERE ROLL") {
                targetLayer = doc.layers[i];
                break;
            }
        }
        
        // If not found, try recursive search through layer groups
        if (!targetLayer) {
            logMessage("Searching recursively for CHANGE HERE ROLL layer");
            targetLayer = findLayerRecursive(doc);
        }
        
        if (!targetLayer) {
            throw new Error("Could not find the 'CHANGE HERE ROLL' layer in the document");
        }
        
        errorLog += "Found target layer: " + targetLayer.name + "\n";
        logMessage("Found target layer: " + targetLayer.name);
        
        doc.activeLayer = targetLayer;
        errorLog += "Activated target layer\n";
        $.sleep(500);  // Wait for layer activation
        
        // Open the Smart Object contents
        try {
            errorLog += "Attempting to open smart object contents...\n";
            logMessage("Opening smart object contents");
            
            try {
                app.runMenuItem(stringIDToTypeID("placedLayerEditContents"));
            } catch (e) {
                errorLog += "Error using runMenuItem: " + e + "\nTrying alternative method...\n";
                logMessage("Using alternative method to open smart object");
                var idEditSmartObject = stringIDToTypeID("editSmartObject");
                var desc = new ActionDescriptor();
                executeAction(idEditSmartObject, desc, DialogModes.NO);
            }
            
            $.sleep(3000);  // Increased wait time for smart object to open
        } catch (e) {
            errorLog += "Error opening smart object: " + e + "\n";
            logMessage("Error opening smart object: " + e.message);
            throw e;
        }
        
        var soDoc = app.activeDocument;
        errorLog += "Smart Object opened: " + soDoc.name + "\n";
        logMessage("Smart Object opened: " + soDoc.name);
        
        // Use the current pattern file as the replacement image
        var newImageFile = new File(patternPath);
        if (!newImageFile.exists) {
            throw new Error("Replacement pattern file not found: " + newImageFile.fsName);
        }
        
        errorLog += "Opening replacement image...\n";
        logMessage("Opening replacement image: " + newImageFile.fsName);
        var replacementDoc = app.open(newImageFile);
        $.sleep(1000);  // Wait for image to open
        
        errorLog += "Replacement image opened\n";
        logMessage("Replacement image opened");
        
        // Set the preference to use pixels and copy the content
        originalRulerUnits = app.preferences.rulerUnits;
        app.preferences.rulerUnits = Units.PIXELS;
        
        replacementDoc.selection.selectAll();
        replacementDoc.selection.copy();
        errorLog += "Copied content from replacement image\n";
        logMessage("Copied content from replacement image");
        
        replacementDoc.close(SaveOptions.DONOTSAVECHANGES);
        errorLog += "Replacement image closed\n";
        $.sleep(500);  // Wait for close to complete
        
        // Switch back to the Smart Object document and paste
        app.activeDocument = soDoc;
        
        // Clear any extra pasted layers from the Smart Object
        if (soDoc.artLayers.length > 1) {
            for (var i = soDoc.artLayers.length - 1; i >= 1; i--) {
                soDoc.artLayers[i].remove();
            }
            errorLog += "Cleared extra layers from Smart Object\n";
            logMessage("Cleared extra layers from Smart Object");
        }
        
        var newLayer = soDoc.artLayers.add();
        newLayer.name = baseName;
        newLayer.move(soDoc.layers[0], ElementPlacement.PLACEBEFORE);
        soDoc.paste();
        $.sleep(500);  // Wait for paste operation
        errorLog += "Pasted content into new layer\n";
        logMessage("Pasted content into new layer: " + newLayer.name);
        
        // Apply the transformations and positioning
        soDoc.activeLayer.resize(200, 200, AnchorPosition.TOPLEFT);
        $.sleep(500);  // Wait for resize
        soDoc.activeLayer.rotate(90, AnchorPosition.MIDDLECENTER);
        $.sleep(500);  // Wait for rotation
        
        // Position at origin
        soDoc.activeLayer = soDoc.layers[0];
        soDoc.activeLayer.translate(-soDoc.activeLayer.bounds[0], -soDoc.activeLayer.bounds[1]);
        $.sleep(500);  // Wait for translation
        errorLog += "Positioned image at 0,0\n";
        logMessage("Positioned image at 0,0");
        
        // Resize to exact dimensions
        var currentWidth = soDoc.activeLayer.bounds[2] - soDoc.activeLayer.bounds[0];
        var currentHeight = soDoc.activeLayer.bounds[3] - soDoc.activeLayer.bounds[1];
        errorLog += "Current layer dimensions: " + currentWidth + " x " + currentHeight + "\n";
        logMessage("Current layer dimensions: " + currentWidth + " x " + currentHeight);
        
        var widthScale = (8592 / currentWidth) * 100;
        var heightScale = (8592 / currentHeight) * 100;
        soDoc.activeLayer.resize(widthScale, heightScale, AnchorPosition.TOPLEFT);
        $.sleep(1000);  // Wait for resize operation
        errorLog += "Resized layer to 8592x8592 pixels\n";
        logMessage("Resized layer to 8592x8592 pixels");
        
        // Save the Smart Object
        var saveOptions = new PhotoshopSaveOptions();
        saveOptions.embedColorProfile = true;
        saveOptions.maximizeCompatibility = true;
        soDoc.saveAs(soDoc.fullName, saveOptions, true);
        $.sleep(1000);  // Wait for save operation
        errorLog += "Smart Object saved\n";
        logMessage("Smart Object saved");
        
        soDoc.close(SaveOptions.SAVECHANGES);
        $.sleep(1000);  // Wait for close operation
        errorLog += "Smart Object closed\n";
        logMessage("Smart Object closed");
        
        // Save the main document and export as PNG
        doc.save();
        $.sleep(1000);  // Wait for save operation
        errorLog += "Main document saved\n";
        logMessage("Main document saved");
        
        var outputFileName = baseName + "_rolled.png";
        var outputFilePath = outputFolder + "\\" + outputFileName;
        var exportOptions = new ExportOptionsSaveForWeb();
        exportOptions.format = SaveDocumentType.PNG;
        exportOptions.PNG8 = false;
        exportOptions.quality = 100;
        
        doc.exportDocument(new File(outputFilePath), ExportType.SAVEFORWEB, exportOptions);
        errorLog += "Exported rolled image to " + outputFilePath + "\n";
        logMessage("Exported rolled image to: " + outputFilePath);
        
        // Restore original preferences
        app.preferences.rulerUnits = originalRulerUnits;
        
        doc.close(SaveOptions.SAVECHANGES);
        $.sleep(1000);  // Wait for close operation
        logMessage("Rolled image processing completed successfully");
        
    } catch (e) {
        errorLog += "ERROR in rolled image processing: " + e.message + "\n";
        logMessage("ERROR in rolled image processing: " + e.message);
        $.writeln("Error in rolled image processing: " + e.message + "\nLog:\n" + errorLog);
        
        // Restore preferences and clean up
        if (typeof originalRulerUnits !== 'undefined') {
            app.preferences.rulerUnits = originalRulerUnits;
        }
        
        // Close any open documents
        try {
            if (app.documents.length > 0) {
                app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
            }
        } catch (closeErr) {
            logMessage("Error closing document: " + closeErr.message);
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