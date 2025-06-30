// Table Runner Templates Image Processor
// Follows the same pattern as bags.jsx and tissues.jsx

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

// Table runner template paths - using the correct filenames with spaces
var tablerunnerTemplatePaths = [
    { path: scriptDir + "/Bags & Tissues/Table Runner 1.psd", name: "tablerunner1", tileType: "6x6" },
    { path: scriptDir + "/Bags & Tissues/Table Runner 2.psd", name: "tablerunner2", tileType: "6x6" },
    { path: scriptDir + "/Bags & Tissues/Table Runner 3.psd", name: "tablerunner3", tileType: "6x6" }
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

// Quit Photoshop
var idquit = charIDToTypeID("quit");
executeAction(idquit, undefined, DialogModes.ALL);

// Helper function to process table runner templates
function processTablerunnerTemplate(templatePath, patternPath, outputFolder, baseName, tablerunnerType) {
    var templateDoc = null;
    var smartObjectDoc = null;
    var patternDoc = null;
    
    try {
        var templateFile = new File(templatePath);
        if (!templateFile.exists) {
            alert("Table runner template file not found: " + templatePath);
            return;
        }

        templateDoc = app.open(templateFile);
        var targetLayer = null;
        
        // Find the target layer based on table runner type
        // You may need to adjust these layer names based on your actual table runner PSD structures
        if (tablerunnerType === "tablerunner1") {
            // Look for common table runner layer names - adjust as needed
            targetLayer = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE") ||
                         findLayerRecursive(templateDoc, "Your Design Here") ||
                         findLayerRecursive(templateDoc, "DESIGN HERE");
        } else if (tablerunnerType === "tablerunner2") {
            // Check if there's a Table Runner 2 group
            var tablerunner2Group = findLayerRecursive(templateDoc, "Table Runner 2") ||
                                   findLayerRecursive(templateDoc, "TableRunner2");
            if (tablerunner2Group) {
                targetLayer = findLayerRecursive(tablerunner2Group, "CHANGE DESIGN HERE") ||
                             findLayerRecursive(tablerunner2Group, "Your Design Here");
            } else {
                targetLayer = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE") ||
                             findLayerRecursive(templateDoc, "Your Design Here");
            }
        } else if (tablerunnerType === "tablerunner3") {
            // Check if there's a Table Runner 3 group
            var tablerunner3Group = findLayerRecursive(templateDoc, "Table Runner 3") ||
                                   findLayerRecursive(templateDoc, "TableRunner3");
            if (tablerunner3Group) {
                targetLayer = findLayerRecursive(tablerunner3Group, "CHANGE DESIGN HERE") ||
                             findLayerRecursive(tablerunner3Group, "Your Design Here");
            } else {
                targetLayer = findLayerRecursive(templateDoc, "CHANGE DESIGN HERE") ||
                             findLayerRecursive(templateDoc, "Your Design Here");
            }
        }
        
        if (!targetLayer) {
            alert("Target layer not found for " + tablerunnerType + " in template: " + templatePath);
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
        
        // Save and close Smart Object
        smartObjectDoc.save();
        smartObjectDoc.close(SaveOptions.SAVECHANGES);
        smartObjectDoc = null;
        
        // Restore original visibility
        targetLayer.visible = originalVisibility;
        
        // Export final image
        var outputFileName = baseName.replace(/_[0-9]$/, "") + "_" + tablerunnerType + ".png";
        var outputFilePath = outputFolder + "\\" + outputFileName;
        
        var exportOptions = new ExportOptionsSaveForWeb();
        exportOptions.format = SaveDocumentType.PNG;
        exportOptions.PNG8 = false;
        exportOptions.quality = 100;
        
        templateDoc.exportDocument(new File(outputFilePath), ExportType.SAVEFORWEB, exportOptions);
        
        templateDoc.close(SaveOptions.DONOTSAVECHANGES);
        templateDoc = null;
        
    } catch (error) {
        alert("Failed to process " + tablerunnerType + " with pattern '" + patternPath + "': " + error.toString());
        
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
