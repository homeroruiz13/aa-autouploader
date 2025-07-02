// Complete Bag Templates Image Processor - ULTRA MINIMAL FIX
// Only fix the absolute minimum needed

function getMostRecentFolder(basePath) {
    var folder = new Folder(basePath);
    if (!folder.exists) {
        $.writeln("Base folder not found: " + basePath);
        return null;
    }

    var subfolders = folder.getFiles(function(file) {
        return file instanceof Folder && /^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(file.name);
    });

    if (subfolders.length === 0) {
        $.writeln("No valid subfolders with the correct format found in: " + basePath);
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

// ONLY PATH FIX - Use parent directory for templates
var downloadBasePath = scriptDir.parent + "/Download";
var outputBasePath = scriptDir.parent + "/Output";

// Get the most recent Download and Output folders
var downloadFolder = getMostRecentFolder(downloadBasePath);
var outputFolder = getMostRecentFolder(outputBasePath);

// NEW: Suppress dialogs early so all subsequent actions run without alerts
var originalDialogs = app.displayDialogs;
app.displayDialogs = DialogModes.NO;

if (downloadFolder == null || outputFolder == null) {
    $.writeln("Error: Could not locate the most recent Download or Output folder.");
    var idquit = charIDToTypeID("quit");
    executeAction(idquit, undefined, DialogModes.ALL);
}

// TEMPLATE PATH FIX ONLY
var bagTemplatePaths = [
    { path: scriptDir.parent + "/Bags & Tissues/Bag 1.psd", name: "bag1", tileType: "3x3" },
    { path: scriptDir.parent + "/Bags & Tissues/Bag 2.psd", name: "bag2", tileType: "6x6" },
    { path: scriptDir.parent + "/Bags & Tissues/Bag 3.psd", name: "bag3", tileType: "3x3" },
    { path: scriptDir.parent + "/Bags & Tissues/Bag 4.psd", name: "bag4", tileType: "4x4" },
    { path: scriptDir.parent + "/Bags & Tissues/Bag 5.psd", name: "bag5", tileType: "4x4" },
    { path: scriptDir.parent + "/Bags & Tissues/Bag 6.psd", name: "bag6", tileType: "4x4" },
    { path: scriptDir.parent + "/Bags & Tissues/Bag 7.psd", name: "bag7", tileType: "3x3" }
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

// FIXED QUIT - Use proper syntax
var idquit = charIDToTypeID("quit");
executeAction(idquit, undefined, DialogModes.ALL);

// Helper function - ONLY CHANGE LAYER DETECTION FOR 4,5,6,7
function processBagTemplate(templatePath, patternPath, outputFolder, baseName, bagType) {
    var templateDoc = null;
    var smartObjectDoc = null;
    var patternDoc = null;
    
    try {
        var templateFile = new File(templatePath);
        if (!templateFile.exists) {
            $.writeln("Template file not found: " + templatePath);
            return;
        }

        templateDoc = app.open(templateFile);
        var targetLayer = null;
        
        // KEEP ORIGINAL LOGIC for 1,2,3 - ADD FALLBACKS for 4,5,6,7
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
        } else if (bagType === "bag4" || bagType === "bag5" || bagType === "bag6") {
            var groupName = bagType.charAt(0).toUpperCase() + bagType.slice(1); // e.g., 'Bag4' -> 'Bag4'
            var group = findLayerRecursive(templateDoc, groupName) || findLayerRecursive(templateDoc, groupName.replace('bag', 'Bag ')) || findLayerRecursive(templateDoc, groupName.toUpperCase());
            var targets = [];
            if (group) {
                var t1 = findLayerRecursive(group, "CHANGE DESIGN HERE");
                if (t1) targets.push(t1);
                var t2 = findLayerRecursive(group, "CHANGE DESIGN HERE 2");
                if (t2) targets.push(t2);
            }
            // Fallbacks at document level
            if (targets.length === 0) {
                var t1 = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE");
                if (t1) targets.push(t1);
                var t2 = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE 2");
                if (t2) targets.push(t2);
            }
            if (targets.length === 0) {
                try { templateDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
                $.writeln("No CHANGE DESIGN HERE layers found for " + bagType + " in template: " + templatePath);
                return;
            }
            for (var ti = 0; ti < targets.length; ti++) {
                var targetLayer = targets[ti];
                var originalVisibility = targetLayer.visible;
                targetLayer.visible = true;
                templateDoc.activeLayer = targetLayer;
                var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
                var desc = new ActionDescriptor();
                executeAction(idplacedLayerEditContents, desc, DialogModes.NO);
                smartObjectDoc = app.activeDocument;
                var patternFile = new File(patternPath);
                if (!patternFile.exists) {
                    try { smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
                    try { templateDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
                    $.writeln("Pattern file not found: " + patternPath);
                    continue;
                }
                patternDoc = app.open(patternFile);
                patternDoc.selection.selectAll();
                patternDoc.selection.copy();
                patternDoc.close(SaveOptions.DONOTSAVECHANGES);
                patternDoc = null;
                app.activeDocument = smartObjectDoc;
                try {
                    if (smartObjectDoc.artLayers.length > 1) {
                        // Instead of deleting layers (which can trigger the alert), just hide them
                        for (var li = 0; li < smartObjectDoc.artLayers.length - 1; li++) {
                            try { smartObjectDoc.artLayers[li].visible = false; } catch (visErr) {}
                        }
                    }
                } catch (removeError) {
                    $.writeln("Bag 7: Error clearing layers in group: " + bagGroups[gi] + ": " + removeError);
                    try { smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
                    try { templateDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
                    continue;
                }
                try {
                    smartObjectDoc.paste();
                    var currentLayer = smartObjectDoc.activeLayer;
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
                    smartObjectDoc.save();
                    smartObjectDoc.close(SaveOptions.SAVECHANGES);
                } catch (e) {
                    try { smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e2) {}
                    $.writeln("Error pasting/saving for " + bagType + ": " + e);
                }
                smartObjectDoc = null;
                targetLayer.visible = originalVisibility;
            }
            var outputFileName = baseName.replace(/_[0-9]$/, "") + "_" + bagType + ".png";
            var outputFilePath = outputFolder + "\\" + outputFileName;
            var exportOptions = new ExportOptionsSaveForWeb();
            exportOptions.format = SaveDocumentType.PNG;
            exportOptions.PNG8 = false;
            exportOptions.quality = 100;
            templateDoc.exportDocument(new File(outputFilePath), ExportType.SAVEFORWEB, exportOptions);
            templateDoc.close(SaveOptions.DONOTSAVECHANGES);
            templateDoc = null;
            return;
        } else if (bagType === "bag7") {
            var bagGroups = ["Bag 1", "Bag 2", "Bag 3"];
            var bagSuffixes = ["_bag1.png", "_bag2.png", "_bag3.png"];
            var foundAny = false;
            for (var gi = 0; gi < bagGroups.length; gi++) {
                var group = findLayerRecursive(templateDoc, bagGroups[gi]);
                if (!group) {
                    $.writeln("Bag 7: Group not found: " + bagGroups[gi]);
                    continue;
                }
                var targetLayer = findLayerRecursive(group, "CHANGE DESIGN HERE") ||
                                 findLayerRecursive(group, "Your Design Here") ||
                                 findLayerRecursive(group, "DESIGN HERE") ||
                                 findLayerRecursive(group, "Smart Object") ||
                                 findLayerRecursive(group, "Pattern");
                if (!targetLayer) {
                    $.writeln("Bag 7: Smart Object not found in group: " + bagGroups[gi]);
                    continue;
                }
                foundAny = true;
                var originalVisibility = targetLayer.visible;
                targetLayer.visible = true;
                templateDoc.activeLayer = targetLayer;
                var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
                var desc = new ActionDescriptor();
                executeAction(idplacedLayerEditContents, desc, DialogModes.NO);
                smartObjectDoc = app.activeDocument;
                // Always use the original patternPath (e.g. *_3.png) for each group. We no longer look for *_bagX variations.
                var patternFile = new File(patternPath);
                patternDoc = app.open(patternFile);
                patternDoc.selection.selectAll();
                patternDoc.selection.copy();
                patternDoc.close(SaveOptions.DONOTSAVECHANGES);
                patternDoc = null;
                app.activeDocument = smartObjectDoc;
                try {
                    if (smartObjectDoc.artLayers.length > 1) {
                        while (smartObjectDoc.artLayers.length > 1) {
                            try { smartObjectDoc.artLayers[0].remove(); } catch (removeError) { break; }
                        }
                    } else if (smartObjectDoc.artLayers.length === 1) {
                        // Skip selection.clear to avoid Photoshop alert
                        // smartObjectDoc.selection.selectAll();
                    }
                } catch (removeError) {
                    $.writeln("Bag 7: Error clearing layers in group: " + bagGroups[gi] + ": " + removeError);
                    try { smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
                    try { templateDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
                    continue;
                }
                try {
                    smartObjectDoc.paste();
                    // No resize/translate for Bag 7, assume template is correct
                    smartObjectDoc.save();
                    smartObjectDoc.close(SaveOptions.SAVECHANGES);
                } catch (e) {
                    $.writeln("Bag 7: Error pasting/saving in group: " + bagGroups[gi] + ": " + e);
                    try { smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e2) {}
                }
                smartObjectDoc = null;
                targetLayer.visible = originalVisibility;
            }
            if (!foundAny) {
                $.writeln("Bag 7: No group-based layers processed – falling back to simple Bag 7 logic.");
                try { templateDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
            } else {
                var outputFileName = baseName.replace(/_[0-9]$/, "") + "_" + bagType + ".png";
                var outputFilePath = outputFolder + "\\" + outputFileName;
                var exportOptions = new ExportOptionsSaveForWeb();
                exportOptions.format = SaveDocumentType.PNG;
                exportOptions.PNG8 = false;
                exportOptions.quality = 100;
                templateDoc.exportDocument(new File(outputFilePath), ExportType.SAVEFORWEB, exportOptions);
                templateDoc.close(SaveOptions.DONOTSAVECHANGES);
                templateDoc = null;
                return;
            }
        }
        
        if (!targetLayer) {
            $.writeln("Target layer NOT FOUND for " + bagType + " in template: " + templatePath + "\n\nTried: 'CHANGE DESIGN HERE', 'Your Design Here', 'DESIGN HERE', 'Smart Object', 'Pattern'\n\nPlease check your PSD template and layer names.");
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
            $.writeln("Pattern file not found: " + patternPath);
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
        
        // Switch back to Smart Object and clear existing content
        app.activeDocument = smartObjectDoc;
        
        // SIMPLIFIED CLEARING - avoid delete/fill commands that cause errors
        try {
            // Just try to remove extra layers, don't use fill or delete
            while (smartObjectDoc.artLayers.length > 1) {
                smartObjectDoc.artLayers[0].remove();
            }
        } catch (removeError) {
            // If removal fails, just continue with paste
        }
        
        // Paste the pattern
        smartObjectDoc.paste();
        var currentLayer = smartObjectDoc.activeLayer;
        
        // KEEP ALL ORIGINAL TRANSFORMS
        if (bagType === "bag1") {
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
            var groupName = "Bag 6";
            var group = findLayerRecursive(templateDoc, groupName) || findLayerRecursive(templateDoc, groupName.toUpperCase()) || findLayerRecursive(templateDoc, "Bag6");
            var targets = [];
            if (group) {
                var t1 = findLayerRecursive(group, "CHANGE DESIGN HERE");
                if (t1) targets.push(t1);
                var t2 = findLayerRecursive(group, "CHANGE DESIGN HERE 2");
                if (t2) targets.push(t2);
            }
            if (targets.length === 0) {
                var t1 = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE");
                if (t1) targets.push(t1);
                var t2 = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE 2");
                if (t2) targets.push(t2);
            }
            if (targets.length === 0) {
                try { templateDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
                return;
            }
            for (var ti = 0; ti < targets.length; ti++) {
                var targetLayer = targets[ti];
                var originalVisibility = targetLayer.visible;
                targetLayer.visible = true;
                templateDoc.activeLayer = targetLayer;
                var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
                var desc = new ActionDescriptor();
                executeAction(idplacedLayerEditContents, desc, DialogModes.NO);
                smartObjectDoc = app.activeDocument;
                var patternFile = new File(patternPath);
                if (!patternFile.exists) {
                    try { smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
                    try { templateDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
                    continue;
                }
                patternDoc = app.open(patternFile);
                patternDoc.selection.selectAll();
                patternDoc.selection.copy();
                patternDoc.close(SaveOptions.DONOTSAVECHANGES);
                patternDoc = null;
                app.activeDocument = smartObjectDoc;
                try {
                    if (smartObjectDoc.artLayers.length > 1) {
                        // Instead of deleting layers (which can trigger the alert), just hide them
                        for (var li = 0; li < smartObjectDoc.artLayers.length - 1; li++) {
                            try { smartObjectDoc.artLayers[li].visible = false; } catch (visErr) {}
                        }
                    }
                } catch (removeError) {
                    try { smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
                    try { templateDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
                    continue;
                }
                try {
                    smartObjectDoc.paste();
                    var currentLayer = smartObjectDoc.activeLayer;
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
                    smartObjectDoc.save();
                    smartObjectDoc.close(SaveOptions.SAVECHANGES);
                } catch (e) {
                    try { smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES); } catch (e2) {}
                }
                smartObjectDoc = null;
                targetLayer.visible = originalVisibility;
            }
            var outputFileName = baseName.replace(/_[0-9]$/, "") + "_" + bagType + ".png";
            var outputFilePath = outputFolder + "\\" + outputFileName;
            var exportOptions = new ExportOptionsSaveForWeb();
            exportOptions.format = SaveDocumentType.PNG;
            exportOptions.PNG8 = false;
            exportOptions.quality = 100;
            templateDoc.exportDocument(new File(outputFilePath), ExportType.SAVEFORWEB, exportOptions);
            templateDoc.close(SaveOptions.DONOTSAVECHANGES);
            templateDoc = null;
            return;
        } else if (bagType === "bag7") {
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
        $.writeln("Failed to process " + bagType + " with pattern '" + patternPath + "': " + error.toString());
        
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

// At very end of script, before quitting Photoshop
app.displayDialogs = originalDialogs;