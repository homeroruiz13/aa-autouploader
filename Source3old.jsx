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

            // Calculate scaling factor
            var scaleFactor;
            if (mockupPath.indexOf("011.psd") !== -1) {
                // For 011.psd, scale based on height only
                scaleFactor = (boundingBoxHeight / patternDoc.height) * 73;
            } else {
                // For other mockups, use the original scaling logic
                var widthRatio = boundingBoxWidth / patternDoc.width;
                var heightRatio = boundingBoxHeight / patternDoc.height;
                scaleFactor = Math.max(widthRatio, heightRatio) * 120;
            }

            // Resize the pattern
            patternDoc.resizeImage(null, null, scaleFactor, ResampleMethod.BICUBIC);

            // Copy and paste the pattern into the Smart Object
            patternDoc.selection.selectAll();
            patternDoc.selection.copy();
            patternDoc.close(SaveOptions.DONOTSAVECHANGES);

            app.activeDocument = psbDoc;
            var newLayer = psbDoc.artLayers.add();
            newLayer.move(psbDoc.layers[0], ElementPlacement.PLACEBEFORE);
            psbDoc.paste();

            // Center the pasted layer
            var deltaX = (boundingBoxWidth - newLayer.bounds[2] + newLayer.bounds[0]) / 2;
            var deltaY = (boundingBoxHeight - newLayer.bounds[3] + newLayer.bounds[1]) / 2;
            newLayer.translate(boundingBox[0] + deltaX, boundingBox[1] + deltaY);

            // Remove original content layer if necessary
            if (psbDoc.layers.length > 1) {
                psbDoc.layers[1].remove();
            }

            // Save and close the Smart Object
            psbDoc.save();
            psbDoc.close(SaveOptions.SAVECHANGES);
            app.activeDocument = mockupDoc;
        } catch (error) {
            alert("Failed to process pattern '" + patternPath + "' with mockup '" + mockupPath + "': " + error.toString());
        }
    }

    // Export the final mockup as a PNG
    var mockupName = mockupDoc.name.replace(/\.psd$/, "");
    var outputPNGFileName = outputFolder + "\\" + baseName + "_" + mockupName + ".png";
    var exportOptions = new ExportOptionsSaveForWeb();
    exportOptions.format = SaveDocumentType.PNG;
    exportOptions.PNG8 = false;
    exportOptions.quality = 100;
    mockupDoc.exportDocument(new File(outputPNGFileName), ExportType.SAVEFORWEB, exportOptions);

    mockupDoc.close(SaveOptions.DONOTSAVECHANGES);
}

// Main script execution
// ... [Keep the main execution part unchanged] ...

// Main script execution
var downloadFolder = "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Download\\2024-10-16";
var patternFiles = Folder(downloadFolder).getFiles("*.png");
var outputFolder = "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Output\\2024-10-16";
var mockupPaths = [
    "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\011.psd",
    "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\03_h.psd",
    "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\051_w.psd",
    "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\081_w.psd",
    "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\05 (2).psd"
];

var newMockupPath = "C:\\Users\\john\\OneDrive\\Desktop\\aa-auto\\Mockup\\04 (2).psd";

for (var i = 0; i < patternFiles.length; i++) {
    var patternFile = patternFiles[i];
    var baseName = patternFile.name.replace(".png", "");

    // Process with 011.psd for crossed rolls (_6 files)
    if (baseName.slice(-2) === "_6") {
        processMockup(mockupPaths[0], patternFile.fsName, outputFolder, baseName);
    }

    // Process _3 files with 05 (2).psd and one of the other mockups
    if (baseName.slice(-2) === "_6") {
        processMockup(mockupPaths[4], patternFile.fsName, outputFolder, baseName);
        var randomMockupPath = mockupPaths[Math.floor(Math.random() * 3) + 1];
        processMockup(randomMockupPath, patternFile.fsName, outputFolder, baseName);
        
        // Process _3 files with the new mockup
        processMockup(newMockupPath, patternFile.fsName, outputFolder, baseName);
    }
}