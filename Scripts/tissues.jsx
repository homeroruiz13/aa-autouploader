// Tissue Templates Image Processor - ULTRA MINIMAL FIX
// Only fix tissue 3 layer detection and quit syntax

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

// ONLY PATH FIX
var downloadBasePath = scriptDir.parent + "/Download";
var outputBasePath = scriptDir.parent + "/Output";

// Get the most recent Download and Output folders
var downloadFolder = getMostRecentFolder(downloadBasePath);
var outputFolder = getMostRecentFolder(outputBasePath);

if (downloadFolder == null || outputFolder == null) {
    alert("Error: Could not locate the most recent Download or Output folder.");
    var idquit = charIDToTypeID("quit");
    executeAction(idquit, undefined, DialogModes.ALL);
}

// TEMPLATE PATH FIX ONLY
var tissueTemplatePaths = [
    { path: scriptDir.parent + "/Bags & Tissues/Tissue 1.psd", name: "tissue1", tileType: "6x6" },
    { path: scriptDir.parent + "/Bags & Tissues/Tissue 2.psd", name: "tissue2", tileType: "6x6" },
    { path: scriptDir.parent + "/Bags & Tissues/Tissue 3.psd", name: "tissue3", tileType: "6x6" }
];

// Look for pattern files
var patternFiles = Folder(downloadFolder).getFiles("*.png");

// Process each pattern file with tissue templates
for (var i = 0; i < patternFiles.length; i++) {
    var patternFile = patternFiles[i];
    var baseName = patternFile.name.replace(".png", "");
    
    // Process with tissue templates (using 6x6 tiles)
    for (var j = 0; j < tissueTemplatePaths.length; j++) {
        var tissueConfig = tissueTemplatePaths[j];
        
        // Match pattern files to tissue requirements
        if (tissueConfig.tileType === "6x6" && baseName.slice(-2) === "_6") {
            processTissueTemplate(tissueConfig.path, patternFile.fsName, outputFolder.fsName, baseName, tissueConfig.name);
        }
    }
}

// FIXED QUIT
var idquit = charIDToTypeID("quit");
executeAction(idquit, undefined, DialogModes.ALL);

// Helper function - KEEP WORKING LOGIC for 1&2, only add fallback for 3
function processTissueTemplate(templatePath, patternPath, outputFolder, baseName, tissueType) {
    var templateDoc = null;
    var smartObjectDoc = null;
    var patternDoc = null;
    
    try {
        var templateFile = new File(templatePath);
        if (!templateFile.exists) {
            alert("Tissue template file not found: " + templatePath);
            return;
        }

        templateDoc = app.open(templateFile);
        var targetLayer = null;
        
        // KEEP EXACT WORKING LOGIC for tissue1 and tissue2
        if (tissueType === "tissue1") {
            targetLayer = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE") ||
                         findLayerRecursive(templateDoc, "Your Design Here") ||
                         findLayerRecursive(templateDoc, "DESIGN HERE");
        } else if (tissueType === "tissue2") {
            // Check if there's a Tissue 2 group first
            var tissue2Group = findLayerRecursive(templateDoc, "Tissue 2") ||
                              findLayerRecursive(templateDoc, "Tissue2");
            if (tissue2Group) {
                targetLayer = findLayerRecursive(tissue2Group, "CHANGE DESIGN HERE") ||
                             findLayerRecursive(tissue2Group, "Your Design Here");
            } else {
                targetLayer = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE") ||
                             findLayerRecursive(templateDoc, "Your Design Here");
            }
        } else if (tissueType === "tissue3") {
            var tissue3Group = findLayerRecursive(templateDoc, "Grupo 1") || findLayerRecursive(templateDoc, "Tissue 3") || findLayerRecursive(templateDoc, "Tissue3") || findLayerRecursive(templateDoc, "TISSUE 3");
            if (tissue3Group) {
                targetLayer = findLayerRecursive(tissue3Group, "CHANGE DESIGN HERE") ||
                             findLayerRecursive(tissue3Group, "Your Design Here") ||
                             findLayerRecursive(tissue3Group, "DESIGN HERE") ||
                             findLayerRecursive(tissue3Group, "Smart Object") ||
                             findLayerRecursive(tissue3Group, "Pattern") ||
                             findLayerRecursive(tissue3Group, "change design here copia");
            }
            if (!targetLayer) {
                targetLayer = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE") ||
                             findLayerRecursive(templateDoc, "Your Design Here") ||
                             findLayerRecursive(templateDoc, "DESIGN HERE") ||
                             findLayerRecursive(templateDoc, "Smart Object") ||
                             findLayerRecursive(templateDoc, "Pattern") ||
                             findLayerRecursive(templateDoc, "change design here copia");
            }
        }
        
        if (!targetLayer) {
            alert("Target layer NOT FOUND for " + tissueType + " in template: " + templatePath + "\n\nTried: 'CHANGE DESIGN HERE', 'Your Design Here', 'DESIGN HERE', 'Smart Object', 'Pattern', 'change design here copia'\n\nPlease check your PSD template and layer names.");
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
        
        // Safer method to clear existing layers
        try {
            while (smartObjectDoc.artLayers.length > 1) {
                smartObjectDoc.artLayers[0].remove();
            }
        } catch (removeError) {
            // Continue with paste if layer removal fails
        }
        
        // Paste the pattern
        smartObjectDoc.paste();
        var currentLayer = smartObjectDoc.activeLayer;
        
        // KEEP EXACT WORKING TRANSFORMS for all tissues
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
        
        // Save and close Smart Object
        smartObjectDoc.save();
        smartObjectDoc.close(SaveOptions.SAVECHANGES);
        smartObjectDoc = null;
        
        // Restore original visibility
        targetLayer.visible = originalVisibility;
        
        // Export final image
        var outputFileName = baseName.replace(/_[0-9]$/, "") + "_" + tissueType + ".png";
        var outputFilePath = outputFolder + "\\" + outputFileName;
        
        var exportOptions = new ExportOptionsSaveForWeb();
        exportOptions.format = SaveDocumentType.PNG;
        exportOptions.PNG8 = false;
        exportOptions.quality = 100;
        
        templateDoc.exportDocument(new File(outputFilePath), ExportType.SAVEFORWEB, exportOptions);
        
        templateDoc.close(SaveOptions.DONOTSAVECHANGES);
        templateDoc = null;
        
    } catch (error) {
        alert("Failed to process " + tissueType + " with pattern '" + patternPath + "': " + error.toString());
        
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