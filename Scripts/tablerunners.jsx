// Table Runner Templates Image Processor
// Follows the same pattern as bags.jsx and tissues.jsx

function getMostRecentFolder(basePath) {
    var folder = new Folder(basePath);
    if (!folder.exists) {
        return null;
    }

    var subfolders = folder.getFiles(function(file) {
        return file instanceof Folder && /^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(file.name);
    });

    if (subfolders.length === 0) {
        return null;
    }

    subfolders.sort(function(a, b) {
        return b.name.localeCompare(a.name);
    });

    return subfolders[0];
}

// Get the script's directory
var scriptFile = new File($.fileName);
var scriptDir = scriptFile.parent;

// Define your base paths for Download and Output relative to the script's parent directory (aa-auto)
var downloadBasePath = scriptDir.parent + "/Download";
var outputBasePath = scriptDir.parent + "/Output";

// Get the most recent Download and Output folders
var downloadFolder = getMostRecentFolder(downloadBasePath);
var outputFolder = getMostRecentFolder(outputBasePath);

if (downloadFolder == null || outputFolder == null) {
    // Exit silently if folders not found
} else {
    // Suppress ALL possible dialogs and warnings - COMPLETE AUTOMATION
    app.displayDialogs = DialogModes.NO;
    app.playbackDisplayDialogs = DialogModes.NO;
    app.preferences.showEnglishFontNames = true;
    app.preferences.askBeforeClosingUnsavedDocument = false;
    // Additional safety measures to prevent any save dialogs
    try {
        app.preferences.askBeforeSavingLayeredTIFF = false;
    } catch (e) {}
    try {
        app.preferences.askBeforeClosingUnsavedDocument = false;
    } catch (e) {}
    var originalRulerUnits = app.preferences.rulerUnits;
    var originalTypeUnits = app.preferences.typeUnits;
    app.preferences.rulerUnits = Units.PIXELS;
    app.preferences.typeUnits = TypeUnits.PIXELS;
    // Table runner template paths - using the correct filenames with spaces
    var tablerunnerTemplatePaths = [
        { path: scriptDir.parent + "/Bags & Tissues/Table Runner 1.psd", name: "tablerunner1", tileType: "6x6" },
        { path: scriptDir.parent + "/Bags & Tissues/Table Runner 2.psd", name: "tablerunner2", tileType: "6x6" },
        { path: scriptDir.parent + "/Bags & Tissues/Table Runner 3.psd", name: "tablerunner3", tileType: "6x6" }
    ];

    // Look for pattern files
    var patternFiles = Folder(downloadFolder).getFiles("*.png");

    // Process each pattern file with table runner templates
    for (var i = 0; i < patternFiles.length; i++) {
        var patternFile = patternFiles[i];
        var baseName = patternFile.name.replace(".png", "");
        
        // Process with table runner templates (assuming they use 6x6 tiles like your existing workflow)
        for (var j = 0; j < tablerunnerTemplatePaths.length; j++) {
            var tablerunnerConfig = tablerunnerTemplatePaths[j];
            
            // Match pattern files to table runner requirements
            if (tablerunnerConfig.tileType === "6x6" && baseName.slice(-2) === "_6") {
                processTablerunnerTemplate(tablerunnerConfig.path, patternFile.fsName, outputFolder.fsName, baseName, tablerunnerConfig.name);
            }
        }
    }

    // Restore preferences and quit Photoshop without dialogs
    try {
        app.preferences.rulerUnits = originalRulerUnits;
        app.preferences.typeUnits = originalTypeUnits;
    } catch (e) {
        // Continue if preference restore fails
    }
    var idquit = charIDToTypeID("quit");
    executeAction(idquit, undefined, DialogModes.NO);
}

// Helper function to process table runner templates
function processTablerunnerTemplate(templatePath, patternPath, outputFolder, baseName, tablerunnerType) {
    var templateDoc = null;
    var smartObjectDoc = null;
    var patternDoc = null;
    
    // Use minimal dialog suppression like the working mockup script
    
    try {
        var templateFile = new File(templatePath);
        if (!templateFile.exists) {
            return;
        }

        templateDoc = app.open(templateFile);
        
        // Ensure we don't have document save conflicts
        try {
            templateDoc.changeMode(ChangeMode.RGB);
        } catch (e) {
            // Continue if mode change fails
        }
        
        // Debug: Log all layers in the template
        // Removed alert to prevent hanging in non-interactive mode
        // logAllLayers(templateDoc, "");
        
        var targetLayer = null;
        
        // Simplified layer detection - find any smart object or editable layer
        targetLayer = findSmartObjectLayer(templateDoc) ||
                     findLayerRecursive(templateDoc, "CHANGE DESIGN HERE") ||
                     findLayerRecursive(templateDoc, "Your Design Here") ||
                     findLayerRecursive(templateDoc, "DESIGN HERE") ||
                     findLayerRecursive(templateDoc, "Smart Object");
        
        if (!targetLayer) {
            // Target layer not found - skip this template
            templateDoc.close(SaveOptions.DONOTSAVECHANGES);
            return;
        }

        // Continue processing with found target layer

        // Store original visibility and make layer visible
        var originalVisibility = targetLayer.visible;
        targetLayer.visible = true;
        templateDoc.activeLayer = targetLayer;

        // Check if it's actually a smart object before trying to edit contents
        var isSmartObject = false;
        try {
            if (targetLayer.kind && targetLayer.kind == LayerKind.SMARTOBJECT) {
                isSmartObject = true;
            }
        } catch (e) {
            // Not a smart object, continue with regular processing
        }

        if (isSmartObject) {
            // Open the Smart Object
            var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
            var desc = new ActionDescriptor();
            executeAction(idplacedLayerEditContents, desc, DialogModes.NO);

            smartObjectDoc = app.activeDocument;
        } else {
            // If not a smart object, work directly with the layer
            smartObjectDoc = templateDoc;
        }
        
        // Open pattern file
        var patternFile = new File(patternPath);
        if (!patternFile.exists) {
            smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES);
            templateDoc.close(SaveOptions.DONOTSAVECHANGES);
            return;
        }
        
        patternDoc = app.open(patternFile);
        
        // Copy pattern content
        patternDoc.selection.selectAll();
        patternDoc.selection.copy();
        patternDoc.close(SaveOptions.DONOTSAVECHANGES);
        patternDoc = null;
        
        // Switch back to Smart Object and clear existing content safely
        app.activeDocument = smartObjectDoc;
        
        // Simple method to clear content - just select all and delete
        try {
            smartObjectDoc.selection.selectAll();
            var iddelete = charIDToTypeID("Dlt ");
            executeAction(iddelete, undefined, DialogModes.NO);
        } catch (e) {
            // If clearing fails, just proceed (pattern will overlay)
        }
        
        // Follow the working mockup pattern: add new layer and manage layers properly
        app.activeDocument = smartObjectDoc;
        var newLayer = smartObjectDoc.artLayers.add();
        if (smartObjectDoc.layers.length > 1) {
            newLayer.move(smartObjectDoc.layers[0], ElementPlacement.PLACEBEFORE);
        }
        smartObjectDoc.paste();
        var currentLayer = smartObjectDoc.activeLayer;
        
        // Apply transforms based on table runner type
        // These values may need to be adjusted based on your actual table runner templates
        if (tablerunnerType === "tablerunner1") {
            // Table Runner 1 transforms - you may need to adjust these values
            var targetWidth = 2000;   // Placeholder values - adjust based on your templates
            var targetHeight = 2000;
            var targetX = 0;
            var targetY = 0;
            
            var width = currentLayer.bounds[2] - currentLayer.bounds[0];
            var height = currentLayer.bounds[3] - currentLayer.bounds[1];
            var widthRatio = targetWidth / width * 100;
            var heightRatio = targetHeight / height * 100;
            
            currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
            currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
            
        } else if (tablerunnerType === "tablerunner2") {
            // Table Runner 2 transforms - adjust as needed
            var targetWidth = 2000;
            var targetHeight = 2000;
            var targetX = 0;
            var targetY = 0;
            
            var width = currentLayer.bounds[2] - currentLayer.bounds[0];
            var height = currentLayer.bounds[3] - currentLayer.bounds[1];
            var widthRatio = targetWidth / width * 100;
            var heightRatio = targetHeight / height * 100;
            
            currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
            currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
            
        } else if (tablerunnerType === "tablerunner3") {
            // Table Runner 3 transforms - adjust as needed
            var targetWidth = 2000;
            var targetHeight = 2000;
            var targetX = 0;
            var targetY = 0;
            
            var width = currentLayer.bounds[2] - currentLayer.bounds[0];
            var height = currentLayer.bounds[3] - currentLayer.bounds[1];
            var widthRatio = targetWidth / width * 100;
            var heightRatio = targetHeight / height * 100;
            
            currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
            currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
        }
        
        // Clean up old layers (keep only the new pattern layer)
        if (smartObjectDoc.layers.length > 1) {
            try {
                // Remove the bottom layer (original content)
                var layerToRemove = smartObjectDoc.layers[smartObjectDoc.layers.length - 1];
                layerToRemove.remove();
            } catch (e) {
                // Continue if layer removal fails
            }
        }
        
        // Save and close Smart Object using the working pattern from mockups
        if (isSmartObject) {
            try {
                // Save first, then close with SaveChanges (following working mockup pattern)
                var saveOptions = new PhotoshopSaveOptions();
                saveOptions.embedColorProfile = true;
                saveOptions.maximizeCompatibility = true;
                smartObjectDoc.saveAs(smartObjectDoc.fullName, saveOptions, true);
                smartObjectDoc.close(SaveOptions.SAVECHANGES);
            } catch (e) {
                // If save fails, try simpler approach
                try {
                    smartObjectDoc.save();
                    smartObjectDoc.close(SaveOptions.SAVECHANGES);
                } catch (closeError) {
                    // Final fallback
                    try {
                        smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES);
                    } catch (finalError) {
                        // Continue if everything fails
                    }
                }
            }
        } else {
            // For regular layers, don't save
            try {
                smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES);
            } catch (e) {
                // Continue if close fails
            }
        }
        smartObjectDoc = null;
        
        // Restore original visibility
        targetLayer.visible = originalVisibility;
        
        // Export final image
        var outputFileName = baseName.replace(/_[0-9]$/, "") + "_" + tablerunnerType + ".png";
        var outputFilePath = outputFolder + "\\" + outputFileName;
        
        // Delete existing file if it exists to prevent overwrite dialog
        var outputFile = new File(outputFilePath);
        if (outputFile.exists) {
            try {
                outputFile.remove();
            } catch (e) {
                // Continue if file can't be deleted
            }
        }
        
        var exportOptions = new ExportOptionsSaveForWeb();
        exportOptions.format = SaveDocumentType.PNG;
        exportOptions.PNG8 = false;
        exportOptions.quality = 100;
        exportOptions.includeProfile = false;
        exportOptions.optimized = true;
        
        templateDoc.exportDocument(outputFile, ExportType.SAVEFORWEB, exportOptions);
        
        templateDoc.close(SaveOptions.DONOTSAVECHANGES);
        templateDoc = null;
        
    } catch (error) {
        // Clean up any open documents
        try {
            if (patternDoc) patternDoc.close(SaveOptions.DONOTSAVECHANGES);
            if (smartObjectDoc) smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES);
            if (templateDoc) templateDoc.close(SaveOptions.DONOTSAVECHANGES);
        } catch (cleanupError) {
            // Ignore cleanup errors
        }
    }
}

// Recursive function to find a layer by name
function findLayerRecursive(layerContainer, layerName) {
    if (!layerContainer.layers) {
        return null;
    }
    
    for (var i = 0; i < layerContainer.layers.length; i++) {
        var layer = layerContainer.layers[i];
        
        if (layer.name.toUpperCase() === layerName.toUpperCase()) {
            return layer;
        }
        
        if (layer.typename === "LayerSet") {
            var foundLayer = findLayerRecursive(layer, layerName);
            if (foundLayer) return foundLayer;
        }
    }
    return null;
}

// Debug function to log all layers in a document
function logAllLayers(doc, indent) {
    var layerInfo = "";
    try {
        // Log art layers
        for (var i = 0; i < doc.artLayers.length; i++) {
            var layer = doc.artLayers[i];
            var layerType = "ArtLayer";
            try {
                if (layer.kind == LayerKind.SMARTOBJECT) {
                    layerType = "SmartObject";
                }
            } catch (e) {}
            layerInfo += indent + "- " + layer.name + " (" + layerType + ")\n";
        }
        
        // Log layer sets
        for (var i = 0; i < doc.layerSets.length; i++) {
            var layerSet = doc.layerSets[i];
            layerInfo += indent + "+ " + layerSet.name + " (LayerSet)\n";
            layerInfo += logAllLayersInSet(layerSet, indent + "  ");
        }
    } catch (e) {
        layerInfo += indent + "Error reading layers: " + e.toString() + "\n";
    }
    
    if (indent === "") {
                    // Layer info logged to console
    }
    return layerInfo;
}

// Helper function to log layers in a layer set
function logAllLayersInSet(layerSet, indent) {
    var layerInfo = "";
    try {
        // Log art layers in this set
        for (var i = 0; i < layerSet.artLayers.length; i++) {
            var layer = layerSet.artLayers[i];
            var layerType = "ArtLayer";
            try {
                if (layer.kind == LayerKind.SMARTOBJECT) {
                    layerType = "SmartObject";
                }
            } catch (e) {}
            layerInfo += indent + "- " + layer.name + " (" + layerType + ")\n";
        }
        
        // Log nested layer sets
        for (var i = 0; i < layerSet.layerSets.length; i++) {
            var nestedSet = layerSet.layerSets[i];
            layerInfo += indent + "+ " + nestedSet.name + " (LayerSet)\n";
            layerInfo += logAllLayersInSet(nestedSet, indent + "  ");
        }
    } catch (e) {
        layerInfo += indent + "Error reading layer set: " + e.toString() + "\n";
    }
    return layerInfo;
}

// Helper function to find a smart object layer
function findSmartObjectLayer(doc) {
    try {
        // Check art layers first
        for (var i = 0; i < doc.artLayers.length; i++) {
            var layer = doc.artLayers[i];
            if (layer.kind && layer.kind == LayerKind.SMARTOBJECT) {
                return layer;
            }
        }
        
        // Check layer sets recursively
        for (var i = 0; i < doc.layerSets.length; i++) {
            var found = findSmartObjectInLayerSet(doc.layerSets[i]);
            if (found) return found;
        }
    } catch (e) {
        // If we can't access layer properties, return null
    }
    return null;
}

// Helper function to find smart object in layer sets recursively
function findSmartObjectInLayerSet(layerSet) {
    try {
        // Check art layers in this set
        for (var i = 0; i < layerSet.artLayers.length; i++) {
            var layer = layerSet.artLayers[i];
            if (layer.kind && layer.kind == LayerKind.SMARTOBJECT) {
                return layer;
            }
        }
        
        // Check nested layer sets
        for (var i = 0; i < layerSet.layerSets.length; i++) {
            var found = findSmartObjectInLayerSet(layerSet.layerSets[i]);
            if (found) return found;
        }
    } catch (e) {
        // If we can't access layer properties, continue
    }
    return null;
}
