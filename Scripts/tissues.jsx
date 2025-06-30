// Tissue Templates Image Processor
// Follows the same pattern as bags.jsx and source3.jsx

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

// Tissue template paths - using the Bags & Tissues folder
var tissueTemplatePaths = [
    { path: scriptDir + "/Bags & Tissues/Tissue1.psd", name: "tissue1", tileType: "6x6" },
    { path: scriptDir + "/Bags & Tissues/Tissue2.psd", name: "tissue2", tileType: "6x6" },
    { path: scriptDir + "/Bags & Tissues/Tissue3.psd", name: "tissue3", tileType: "6x6" }
];

// Look for pattern files
var patternFiles = Folder(downloadFolder).getFiles("*.png");

// Process each pattern file with tissue templates
for (var i = 0; i < patternFiles.length; i++) {
    var patternFile = patternFiles[i];
    var baseName = patternFile.name.replace(".png", "");
    
    // Process with tissue templates (assuming they use 6x6 tiles like your existing workflow)
    for (var j = 0; j < tissueTemplatePaths.length; j++) {
        var tissueConfig = tissueTemplatePaths[j];
        
        // Match pattern files to tissue requirements
        if (tissueConfig.tileType === "6x6" && baseName.slice(-2) === "_6") {
            processTissueTemplate(tissueConfig.path, patternFile.fsName, outputFolder.fsName, baseName, tissueConfig.name);
        }
    }
}

// Quit Photoshop
var idquit = charIDToTypeID("quit");
executeAction(idquit, undefined, DialogModes.ALL);

// Helper function to process tissue templates
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
        
        // Find the target layer based on tissue type
        // You may need to adjust these layer names based on your actual tissue PSD structures
        if (tissueType === "tissue1") {
            // Look for common tissue layer names - adjust as needed
            targetLayer = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE") ||
                         findLayerRecursive(templateDoc, "Your Design Here") ||
                         findLayerRecursive(templateDoc, "DESIGN HERE");
        } else if (tissueType === "tissue2") {
            // Check if there's a Tissue 2 group
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
            // Check if there's a Tissue 3 group
            var tissue3Group = findLayerRecursive(templateDoc, "Tissue 3") ||
                              findLayerRecursive(templateDoc, "Tissue3");
            if (tissue3Group) {
                targetLayer = findLayerRecursive(tissue3Group, "CHANGE DESIGN HERE") ||
                             findLayerRecursive(tissue3Group, "Your Design Here");
            } else {
                targetLayer = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE") ||
                             findLayerRecursive(templateDoc, "Your Design Here");
            }
        }
        
        if (!targetLayer) {
            alert("Target layer not found for " + tissueType + " in template: " + templatePath);
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
            // If we can't remove layers, just proceed with paste (will overlay)
        }
        
        // Paste the pattern
        smartObjectDoc.paste();
        var currentLayer = smartObjectDoc.activeLayer;
        
        // Apply transforms based on tissue type
        // These values may need to be adjusted based on your actual tissue templates
        if (tissueType === "tissue1") {
            // Tissue 1 transforms - you may need to adjust these values
            var targetWidth = 2000;   // Placeholder values
            var targetHeight = 2000;
            var targetX = 0;
            var targetY = 0;
            
            var width = currentLayer.bounds[2] - currentLayer.bounds[0];
            var height = currentLayer.bounds[3] - currentLayer.bounds[1];
            var widthRatio = targetWidth / width * 100;
            var heightRatio = targetHeight / height * 100;
            
            currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
            currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
            
        } else if (tissueType === "tissue2") {
            // Tissue 2 transforms - adjust as needed
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
            
        } else if (tissueType === "tissue3") {
            // Tissue 3 transforms - adjust as needed
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
