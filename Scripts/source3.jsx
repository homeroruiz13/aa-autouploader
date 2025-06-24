#target photoshop

// === Begin Script ===

// Main function to process images
function processImages() {
    try {
        // Get the script's directory and workspace root
        var scriptFile = new File($.fileName);
        var scriptDir = scriptFile.parent;
        var workspaceRoot = scriptDir.parent; // Go up one level from Scripts to get workspace root

        $.writeln("Script directory: " + scriptDir.fsName);
        $.writeln("Workspace root: " + workspaceRoot.fsName);

        // Define your base paths for Download and Output relative to workspace root
        var downloadBasePath = workspaceRoot + "/Download";
        var outputBasePath = workspaceRoot + "/Output";

        $.writeln("Looking for Download folder at: " + downloadBasePath);
        $.writeln("Looking for Output folder at: " + outputBasePath);

        // Function to get the most recent folder
        function getMostRecentFolder(basePath) {
            var folder = new Folder(basePath);
            if (!folder.exists) {
                $.writeln("Base folder not found: " + basePath);
                return null;
            }

            $.writeln("Found base folder: " + basePath);
            var subfolders = folder.getFiles(function(file) {
                return file instanceof Folder && /^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(file.name);
            });

            $.writeln("Found " + subfolders.length + " timestamped subfolders");

            if (subfolders.length === 0) {
                $.writeln("No valid subfolders with the correct format found in: " + basePath);
                return null;
            }

            subfolders.sort(function(a, b) {
                return b.name.localeCompare(a.name);
            });

            var mostRecent = subfolders[0];
            $.writeln("Most recent folder: " + mostRecent.fsName);
            return mostRecent;
        }

        // Get the most recent Download and Output folders
        var downloadFolder = getMostRecentFolder(downloadBasePath);
        var outputFolder = getMostRecentFolder(outputBasePath);

        if (downloadFolder == null || outputFolder == null) {
            $.writeln("Error: Could not locate the most recent Download or Output folder.");
            return false;
        }

        $.writeln("Processing files from: " + downloadFolder.fsName);
        var patternFiles = Folder(downloadFolder).getFiles("*.png");
        $.writeln("Found " + patternFiles.length + " PNG files to process");

        // Define mockup paths relative to workspace root
        var mockupPaths = {
            crossed: workspaceRoot + "/Mockup/011.psd",
            hero: workspaceRoot + "/Mockup/03_h.psd",  // Using 03_h.psd as the hero image
            single: workspaceRoot + "/Mockup/05 (2).psd",
            threeBox: workspaceRoot + "/Mockup/04 (2).psd",
            rolled: workspaceRoot + "/Mockup/rolled.psd"
        };

        // Verify mockup files exist
        $.writeln("Verifying mockup files...");
        for (var key in mockupPaths) {
            var file = new File(mockupPaths[key]);
            $.writeln("Checking " + key + " mockup: " + mockupPaths[key] + " - " + (file.exists ? "Found" : "Not found"));
        }

        // Process each pattern file
        for (var i = 0; i < patternFiles.length; i++) {
            var patternFile = patternFiles[i];
            var baseName = patternFile.name.replace(".png", "");
            $.writeln("\n=== Processing file: " + patternFile.name + " ===");

            if (baseName.slice(-2) === "_6") {
                // Process hero image first with detailed logging
                $.writeln("\n=== Starting hero image processing ===");
                $.writeln("Using hero template: " + mockupPaths.hero);
                processMockup(mockupPaths.hero, patternFile.fsName, outputFolder.fsName, baseName, "hero", ["Your Design Here"]);
                $.writeln("=== Completed hero image processing ===\n");

                // Process other mockups
                $.writeln("Processing crossed rolls with 011.psd");
                processMockup(mockupPaths.crossed, patternFile.fsName, outputFolder.fsName, baseName, "011", ["You Design 01", "You Design 02"]);

                $.writeln("Processing single roll with 05 (2).psd");
                processMockup(mockupPaths.single, patternFile.fsName, outputFolder.fsName, baseName, "05-(2)", ["Your Design Here"]);

                $.writeln("Processing three box display with 04 (2).psd");
                processMockup(mockupPaths.threeBox, patternFile.fsName, outputFolder.fsName, baseName, "04-(2)", ["Box 01", "Box 02", "Box 03"]);

                // Process rolled image
                $.writeln("Processing rolled image");
                processRolledImage(baseName, patternFile.fsName, outputFolder.fsName);
            }
        }

        $.writeln("All files processed successfully");
        return true;
    } catch (e) {
        $.writeln("Error in processImages: " + e.toString());
        return false;
    }
}

// Helper function to process regular mockups
function processMockup(mockupPath, patternPath, outputFolder, baseName, type, targetLayerNames) {
    try {
        $.writeln("=== Starting processMockup ===");
        $.writeln("Mockup type: " + type);
        $.writeln("Mockup path: " + mockupPath);
        $.writeln("Pattern path: " + patternPath);
        $.writeln("Output folder: " + outputFolder);
        $.writeln("Base name: " + baseName);
        
        var mockupFile = new File(mockupPath);
        if (!mockupFile.exists) {
            $.writeln("ERROR: Mockup file not found: " + mockupPath);
            return;
        }
        $.writeln("Mockup file exists: " + mockupPath);

        $.writeln("Opening mockup: " + mockupPath);
        var mockupDoc = app.open(mockupFile);
        $.sleep(300);
        $.writeln("Mockup opened successfully");

        var targetLayers = [];
        for (var i = 0; i < targetLayerNames.length; i++) {
            try {
                var smartObjectGroup = mockupDoc.layerSets.getByName("Smart Object Layers");
                var layer = smartObjectGroup.artLayers.getByName(targetLayerNames[i]);
                if (layer) {
                    targetLayers.push(layer);
                    $.writeln("Found target layer: " + targetLayerNames[i]);
                }
            } catch (e) {
                $.writeln("Could not find layer: " + targetLayerNames[i]);
            }
        }

        if (targetLayers.length === 0) {
            // Fallback: search the entire document hierarchy for the requested layer names
            function findLayerRecursive(container, name) {
                if (!container.layers) {
                    return null;
                }
                for (var idx = 0; idx < container.layers.length; idx++) {
                    var lyr = container.layers[idx];
                    if (lyr.name === name) {
                        return lyr;
                    }
                    if (lyr.typename === "LayerSet") {
                        var found = findLayerRecursive(lyr, name);
                        if (found) {
                            return found;
                        }
                    }
                }
                return null;
            }

            for (var j = 0; j < targetLayerNames.length; j++) {
                var fallbackLayer = findLayerRecursive(mockupDoc, targetLayerNames[j]);
                if (fallbackLayer) {
                    targetLayers.push(fallbackLayer);
                    $.writeln("Found target layer via fallback search: " + targetLayerNames[j]);
                }
            }

            if (targetLayers.length === 0) {
                $.writeln("No target layers found in mockup even after fallback search: " + mockupPath);
                mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
                return;
            }
        }

        // Open and place the pattern
        var patternFile = new File(patternPath);
        if (!patternFile.exists) {
            $.writeln("Pattern file not found: " + patternPath);
            mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
            return;
        }

        // Process each target layer
        for (var i = 0; i < targetLayers.length; i++) {
            try {
                mockupDoc.activeLayer = targetLayers[i];
                $.sleep(100);

                // Open the Smart Object
                var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
                var desc = new ActionDescriptor();
                executeAction(idplacedLayerEditContents, desc, DialogModes.NO);
                $.sleep(300);

                var soDoc = app.activeDocument;
                var patternDoc = app.open(patternFile);
                $.sleep(100);

                // Get the bounds of the smart object
                var boundingBox = soDoc.layers[0].bounds;
                var boundingBoxWidth = boundingBox[2] - boundingBox[0];
                var boundingBoxHeight = boundingBox[3] - boundingBox[1];

                // Calculate scale factor based on mockup type
                var scaleFactor;
                if (type === "011") {
                    scaleFactor = (boundingBoxHeight / patternDoc.height) * 73;
                } else {
                    var widthRatio = boundingBoxWidth / patternDoc.width;
                    var heightRatio = boundingBoxHeight / patternDoc.height;
                    scaleFactor = Math.max(widthRatio, heightRatio) * 120;
                }

                // Resize and place the pattern
                patternDoc.resizeImage(null, null, scaleFactor, ResampleMethod.BICUBIC);
                $.sleep(200);

                patternDoc.selection.selectAll();
                patternDoc.selection.copy();
                patternDoc.close(SaveOptions.DONOTSAVECHANGES);
                $.sleep(200);

                app.activeDocument = soDoc;
                var newLayer = soDoc.artLayers.add();
                newLayer.move(soDoc.layers[0], ElementPlacement.PLACEBEFORE);
                soDoc.paste();
                $.sleep(200);

                // Center the pattern
                var deltaX = (boundingBoxWidth - newLayer.bounds[2] + newLayer.bounds[0]) / 2;
                var deltaY = (boundingBoxHeight - newLayer.bounds[3] + newLayer.bounds[1]) / 2;
                newLayer.translate(boundingBox[0] + deltaX, boundingBox[1] + deltaY);
                $.sleep(200);

                // Clean up and save
                if (soDoc.layers.length > 1) {
                    soDoc.layers[1].remove();
                }

                soDoc.save();
                soDoc.close(SaveOptions.SAVECHANGES);
                app.activeDocument = mockupDoc;
                $.sleep(200);
            } catch (e) {
                $.writeln("Error processing layer " + targetLayerNames[i] + ": " + e.toString());
            }
        }

        // Export the final image with special handling for hero image
        var outputPath;
        if (type === "hero") {
            outputPath = outputFolder + "/" + baseName + "_hero.png";
            $.writeln("Processing hero image - Output path: " + outputPath);
        } else {
            outputPath = outputFolder + "/" + baseName + "_" + type + ".png";
            $.writeln("Processing regular image - Output path: " + outputPath);
        }
        
        var saveFile = new File(outputPath);
        $.writeln("Creating save file at: " + outputPath);
        
        var exportOptions = new ExportOptionsSaveForWeb();
        exportOptions.format = SaveDocumentType.PNG;
        exportOptions.PNG8 = false;
        exportOptions.quality = 100;
        
        $.writeln("Exporting document...");
        mockupDoc.exportDocument(saveFile, ExportType.SAVEFORWEB, exportOptions);
        $.writeln("Document exported successfully");

        mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
        $.writeln("=== Successfully completed processMockup for type: " + type + " ===");
    } catch (e) {
        $.writeln("ERROR in processMockup: " + e.toString());
        $.writeln("Stack trace: " + e.stack);
        if (app.documents.length > 0) {
            app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
        }
    }
}

// Function to process rolled images
function processRolledImage(baseName, patternPath, outputFolder) {
    try {
        $.writeln("Starting processRolledImage for: " + baseName);
        var fileRef = new File(workspaceRoot + "/Mockup/rolled.psd");
        if (!fileRef.exists) {
            $.writeln("Rolled mockup file not found at: " + fileRef.fsName);
            return;
        }

        app.open(fileRef);
        $.sleep(1000);
        var doc = app.activeDocument;

        // Helper – walk the layer tree and return first layer whose name matches predicate
        function findLayerRecursive(container, predicate) {
            if (!container.layers) {
                return null;
            }
            for (var li = 0; li < container.layers.length; li++) {
                var lyr = container.layers[li];
                if (predicate(lyr)) {
                    return lyr;
                }
                if (lyr.typename === "LayerSet") {
                    var found = findLayerRecursive(lyr, predicate);
                    if (found) {
                        return found;
                    }
                }
            }
            return null;
        }

        // Accept a few possible layer names so the script is resilient to template edits
        var targetLayer = findLayerRecursive(doc, function(lyr) {
            var n = lyr.name.toLowerCase();
            return n === "change here roll" || n.indexOf("roll") !== -1 || n.indexOf("your design here") !== -1;
        });

        if (!targetLayer) {
            $.writeln("Could not find a suitable roll replacement layer – aborting rolled image generation");
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return;
        }

        doc.activeLayer = targetLayer;
        $.sleep(200);

        // Open the Smart Object
        var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
        var desc = new ActionDescriptor();
        executeAction(idplacedLayerEditContents, desc, DialogModes.NO);
        $.sleep(300);

        var soDoc = app.activeDocument;
        var patternFile = new File(patternPath);
        if (!patternFile.exists) {
            $.writeln("Pattern file not found: " + patternPath);
            soDoc.close(SaveOptions.DONOTSAVECHANGES);
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return;
        }

        var patternDoc = app.open(patternFile);
        $.sleep(200);

        // Clear existing design layers in smart object (keep bottommost)
        while (soDoc.artLayers.length > 1) {
            soDoc.artLayers[1].remove();
        }

        patternDoc.selection.selectAll();
        patternDoc.selection.copy();
        patternDoc.close(SaveOptions.DONOTSAVECHANGES);
        $.sleep(200);

        app.activeDocument = soDoc;
        var newLayer = soDoc.artLayers.add();
        newLayer.move(soDoc.layers[0], ElementPlacement.PLACEBEFORE);
        soDoc.paste();
        $.sleep(200);

        // Position at 0,0
        soDoc.activeLayer.translate(-soDoc.activeLayer.bounds[0], -soDoc.activeLayer.bounds[1]);
        $.sleep(100);

        // Resize to exact dimensions (8592x8592 px)
        var currentWidth = soDoc.activeLayer.bounds[2] - soDoc.activeLayer.bounds[0];
        var currentHeight = soDoc.activeLayer.bounds[3] - soDoc.activeLayer.bounds[1];
        var widthScale = (8592 / currentWidth) * 100;
        var heightScale = (8592 / currentHeight) * 100;
        soDoc.activeLayer.resize(widthScale, heightScale, AnchorPosition.TOPLEFT);
        $.sleep(200);

        // Save and close the Smart Object
        var saveOptions = new PhotoshopSaveOptions();
        saveOptions.embedColorProfile = true;
        saveOptions.maximizeCompatibility = true;
        soDoc.saveAs(soDoc.fullName, saveOptions, true);
        soDoc.close(SaveOptions.SAVECHANGES);
        $.sleep(300);

        // Save the main document and export as PNG
        doc.save();
        var outputPath = outputFolder + "/" + baseName + "_rolled.png";
        $.writeln("Exporting rolled image to: " + outputPath);
        var saveFile = new File(outputPath);
        var exportOptions = new ExportOptionsSaveForWeb();
        exportOptions.format = SaveDocumentType.PNG;
        exportOptions.PNG8 = false;
        exportOptions.quality = 100;
        doc.exportDocument(saveFile, ExportType.SAVEFORWEB, exportOptions);

        doc.close(SaveOptions.DONOTSAVECHANGES);
        $.writeln("Successfully processed rolled image");
    } catch (e) {
        $.writeln("Error in processRolledImage: " + e.toString());
        if (app.documents.length > 0) {
            app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
        }
    }
}

// Execute the main function
$.writeln("Starting script execution...");
var success = processImages();
$.writeln(success ? "Script completed successfully" : "Script completed with errors");

// Quit Photoshop using Action Manager
$.writeln("Quitting Photoshop...");
var idquit = charIDToTypeID("quit");
executeAction(idquit, undefined, DialogModes.NO); 