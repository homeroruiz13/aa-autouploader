// Complete Bag Templates Image Processor
// Updated to use all available bag templates and fix the delete error

function getMostRecentFolder(basePath) {
    var folder = new Folder(basePath);
    if (!folder.exists) {
        alert("Base folder not found: " + basePath);
        return null;
    }

    var subfolders = folder.getFiles(function(file) {
        return file instanceof Folder && /^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(file.name);
    });

    if (subfolders.length === 0) {
        alert("No valid subfolders with the correct format found in: " + basePath);
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

// Updated bag template paths - using all 7 bag templates
var bagTemplatePaths = [
    { path: scriptDir + "/Bags & Tissues/Bag 1.psd", name: "bag1", tileType: "3x3" },
    { path: scriptDir + "/Bags & Tissues/Bag 2.psd", name: "bag2", tileType: "6x6" },
    { path: scriptDir + "/Bags & Tissues/Bag 3.psd", name: "bag3", tileType: "3x3" },
    { path: scriptDir + "/Bags & Tissues/Bag 4.psd", name: "bag4", tileType: "4x4" },
    { path: scriptDir + "/Bags & Tissues/Bag 5.psd", name: "bag5", tileType: "4x4" },
    { path: scriptDir + "/Bags & Tissues/Bag 6.psd", name: "bag6", tileType: "4x4" },
    { path: scriptDir + "/Bags & Tissues/Bag 7.psd", name: "bag7", tileType: "3x3" }
];

// Look for pattern files
var patternFiles = Folder(downloadFolder).getFiles("*.png");

// Process each pattern file with appropriate bag templates
for (var i = 0; i < patternFiles.length; i++) {
    var patternFile = patternFiles[i];
    var baseName = patternFile.name.replace(".png", "");
    
    // Process with different bag templates based on tile requirements
    for (var j = 0; j < bagTemplatePaths.length; j++) {
        var bagConfig = bagTemplatePaths[j];
        
        // Match pattern files to bag requirements
        if ((bagConfig.tileType === "6x6" && baseName.slice(-2) === "_6") ||
            (bagConfig.tileType === "3x3" && baseName.slice(-2) === "_3") ||
            (bagConfig.tileType === "4x4" && baseName.slice(-2) === "_4")) {
            
            processBagTemplate(bagConfig.path, patternFile.fsName, outputFolder.fsName, baseName, bagConfig.name);
        }
    }
}

// Quit Photoshop
var idquit = charIDToTypeID("quit");
executeAction(idquit, undefined, DialogModes.ALL);

// Helper function to process bag templates (with error fixes)
function processBagTemplate(templatePath, patternPath, outputFolder, baseName, bagType) {
    var templateDoc = null;
    var smartObjectDoc = null;
    var patternDoc = null;
    
    try {
        var templateFile = new File(templatePath);
        if (!templateFile.exists) {
            alert("Template file not found: " + templatePath);
            return;
        }

        templateDoc = app.open(templateFile);
        var targetLayer = null;
        
        // Find the target layer based on bag type
        if (bagType === "bag1") {
            targetLayer = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE");
        } else if (bagType === "bag2") {
            var bag2Group = findLayerRecursive(templateDoc, "Bag 2");
            if (bag2Group) {
                targetLayer = findLayerRecursive(bag2Group, "CHANGE DESIGN HERE");
            }
        } else if (bagType === "bag3") {
            var bag3Group = findLayerRecursive(templateDoc, "Bag 3");
            if (bag3Group) {
                targetLayer = findLayerRecursive(bag3Group, "CHANGE DESIGN");
            }
        } else if (bagType === "bag4") {
            var bag4Group = findLayerRecursive(templateDoc, "Bag 4");
            if (bag4Group) {
                targetLayer = findLayerRecursive(bag4Group, "CHANGE DESIGN HERE");
            }
        } else if (bagType === "bag5") {
            var bag5Group = findLayerRecursive(templateDoc, "Bag 5");
            if (bag5Group) {
                targetLayer = findLayerRecursive(bag5Group, "CHANGE DESIGN HERE");
            }
        } else if (bagType === "bag6") {
            var bag6Group = findLayerRecursive(templateDoc, "Bag 6");
            if (bag6Group) {
                targetLayer = findLayerRecursive(bag6Group, "CHANGE DESIGN HERE");
            }
        } else if (bagType === "bag7") {
            // Bag 7 might have different layer structure - adjust as needed
            targetLayer = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE");
            // Or if it's in a group:
            // var bag7Group = findLayerRecursive(templateDoc, "Bag 7");
            // if (bag7Group) {
            //     targetLayer = findLayerRecursive(bag7Group, "CHANGE DESIGN HERE");
            // }
        }
        
        if (!targetLayer) {
            alert("Target layer not found for " + bagType + " in template: " + templatePath);
            templateDoc.close(SaveOptions.DONOTSAVECHANGES);
            return;
        }

        // Store original visibility and make layer visible
        var originalVisibility = targetLayer.visible;
        targetLayer.visible = true;
        templateDoc.activeLayer = targetLayer;

        // Open the Smart Object
        var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
        var desc = new ActionDescriptor();
        executeAction(idplacedLayerEditContents, desc, DialogModes.NO);

        smartObjectDoc = app.activeDocument;
        
        // Open pattern file
        var patternFile = new File(patternPath);
        if (!patternFile.exists) {
            alert("Pattern file not found: " + patternPath);
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
        
        // FIXED: Safer method to clear existing layers
        try {
            // Remove all layers except the background layer
            while (smartObjectDoc.artLayers.length > 1) {
                smartObjectDoc.artLayers[0].remove();
            }
        } catch (removeError) {
            // If we can't remove layers, try selecting all and filling with transparency
            try {
                smartObjectDoc.selection.selectAll();
                var fillColor = new SolidColor();
                fillColor.rgb.red = 255;
                fillColor.rgb.green = 255;
                fillColor.rgb.blue = 255;
                smartObjectDoc.selection.fill(fillColor);
            } catch (fillError) {
                // If that fails too, just proceed with paste (will overlay)
            }
        }
        
        // Paste the pattern
        smartObjectDoc.paste();
        var currentLayer = smartObjectDoc.activeLayer;
        
        // Apply transforms based on bag type
        if (bagType === "bag1") {
            // Bag 1 transforms
            var targetWidth = 1554;
            var targetHeight = 1440;
            var targetX = -187;
            var targetY = -583;
            
            var width = currentLayer.bounds[2] - currentLayer.bounds[0];
            var height = currentLayer.bounds[3] - currentLayer.bounds[1];
            var widthRatio = targetWidth / width * 100;
            var heightRatio = targetHeight / height * 100;
            
            currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
            currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
            
        } else if (bagType === "bag2") {
            // Bag 2 transforms
            var targetWidth = 1897;
            var targetHeight = 1897;
            var targetX = -151;
            var targetY = -391;
            
            var width = currentLayer.bounds[2] - currentLayer.bounds[0];
            var height = currentLayer.bounds[3] - currentLayer.bounds[1];
            var widthRatio = targetWidth / width * 100;
            var heightRatio = targetHeight / height * 100;
            
            currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
            currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
            
        } else if (bagType === "bag3") {
            // Bag 3 transforms
            var targetWidth = 1250;
            var targetHeight = 1250;
            var targetX = -128;
            var targetY = -481;
            
            var width = currentLayer.bounds[2] - currentLayer.bounds[0];
            var height = currentLayer.bounds[3] - currentLayer.bounds[1];
            var widthRatio = targetWidth / width * 100;
            var heightRatio = targetHeight / height * 100;
            
            currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
            currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
            
            // Hide the paper layer if it exists
            var paperLayer = findLayerRecursive(templateDoc, "midsummer-grovepainted-paper-524010 copia");
            if (paperLayer) {
                paperLayer.visible = false;
            }
        } else if (bagType === "bag4") {
            // Bag 4 transforms (from your original bags2_1.py)
            var targetWidth = 919;
            var targetHeight = 918;
            var targetX = -36;
            var targetY = -41;
            
            var width = currentLayer.bounds[2] - currentLayer.bounds[0];
            var height = currentLayer.bounds[3] - currentLayer.bounds[1];
            var widthRatio = targetWidth / width * 100;
            var heightRatio = targetHeight / height * 100;
            
            currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
            currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
            
        } else if (bagType === "bag5") {
            // Bag 5 transforms (same as Bag 4 for now, adjust if needed)
            var targetWidth = 919;
            var targetHeight = 918;
            var targetX = -36;
            var targetY = -41;
            
            var width = currentLayer.bounds[2] - currentLayer.bounds[0];
            var height = currentLayer.bounds[3] - currentLayer.bounds[1];
            var widthRatio = targetWidth / width * 100;
            var heightRatio = targetHeight / height * 100;
            
            currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
            currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
            
        } else if (bagType === "bag6") {
            // Bag 6 transforms (same as Bag 4/5 for now, adjust if needed)
            var targetWidth = 919;
            var targetHeight = 918;
            var targetX = -36;
            var targetY = -41;
            
            var width = currentLayer.bounds[2] - currentLayer.bounds[0];
            var height = currentLayer.bounds[3] - currentLayer.bounds[1];
            var widthRatio = targetWidth / width * 100;
            var heightRatio = targetHeight / height * 100;
            
            currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
            currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
            
        } else if (bagType === "bag7") {
            // Bag 7 transforms (from your bag7maker.py)
            var targetWidth = 408;
            var targetHeight = 408;
            var targetX = -48;
            var targetY = -4;
            
            var width = currentLayer.bounds[2] - currentLayer.bounds[0];
            var height = currentLayer.bounds[3] - currentLayer.bounds[1];
            var widthRatio = targetWidth / width * 100;
            var heightRatio = targetHeight / height * 100;
            
            currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
            currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
        }
        
        // Save and close Smart Object
        smartObjectDoc.save();
        smartObjectDoc.close(SaveOptions.SAVECHANGES);
        smartObjectDoc = null;
        
        // Restore original visibility
        targetLayer.visible = originalVisibility;
        
        // Export final image
        var outputFileName = baseName.replace(/_[0-9]$/, "") + "_" + bagType + ".png";
        var outputFilePath = outputFolder + "\\" + outputFileName;
        
        var exportOptions = new ExportOptionsSaveForWeb();
        exportOptions.format = SaveDocumentType.PNG;
        exportOptions.PNG8 = false;
        exportOptions.quality = 100;
        
        templateDoc.exportDocument(new File(outputFilePath), ExportType.SAVEFORWEB, exportOptions);
        
        templateDoc.close(SaveOptions.DONOTSAVECHANGES);
        templateDoc = null;
        
    } catch (error) {
        alert("Failed to process " + bagType + " with pattern '" + patternPath + "': " + error.toString());
        
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
