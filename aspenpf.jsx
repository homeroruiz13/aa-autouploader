// Disable warning dialogs at the start
app.preferences.setBooleanPreference("ShowExternalJSXWarning", false);
app.preferences.setBooleanPreference("trustAllScripts", true);

// Setup log file
var logFile = new File(Folder.desktop + "/illustrator_script_log.txt");
logFile.open("w");
function logMessage(message) {
    var timestamp = new Date().toLocaleString();
    var logText = "[" + timestamp + "] " + message;
    logFile.writeln(logText);
    $.writeln(logText);
}

logMessage("Starting Illustrator PDF processing script");

// Updated base paths
var BASE_FOLDER = "D:/Uploader Transfer/aa-auto";
var TEMPLATE_IMAGES_FOLDER = BASE_FOLDER + "/Templateimages";

function getOutputFolder() {
    // Try to get output folder from environment variable
    var outputFolder = $.getenv("OUTPUT_FOLDER");
    
    // Fallback to default if environment variable is not set
    if (!outputFolder) {
        logMessage("[WARNING] OUTPUT_FOLDER environment variable not set. Using default.");
        outputFolder = BASE_FOLDER + "/printpanels/output";
    }
    
    // Ensure the folder exists
    var folderObj = new Folder(outputFolder);
    if (!folderObj.exists) {
        folderObj.create();
    }
    
    logMessage("[INFO] Using output folder: " + outputFolder);
    return outputFolder;
}

function openTemplate(templatePath) {
    var file = new File(templatePath);
    if (!file.exists) {
        throw new Error("Template file not found: " + templatePath);
    }
    try {
        return app.open(file); // Open the Illustrator file
    } catch (e) {
        throw new Error("Failed to open template file: " + e.message);
    }
}

function trimString(str) {
    return str.replace(/^\s+|\s+$/g, ""); // Removes leading and trailing spaces
}

function readCSV(filePath) {
    var file = new File(filePath);
    if (!file.exists) {
        throw new Error("CSV file not found: " + filePath);
    }

    file.open('r');
    var lines = file.read().split("\n");
    file.close();

    var data = [];
    for (var i = 0; i < lines.length; i++) {
        var line = trimString(lines[i]);
        if (line) {
            var parts = line.split(",");
            if (parts.length >= 2) {
                data.push({ text: trimString(parts[0]), filePath: trimString(parts[1]) });
            }
        }
    }
    return data;
}

function writeCSV(filePath, data) {
    var file = new File(filePath);
    file.open('w');
    for (var i = 0; i < data.length; i++) {
        var row = data[i].join(","); // Convert array to comma-separated string
        file.writeln(row);
    }
    file.close();
    $.writeln("[INFO] Results written back to CSV: " + filePath);
}

function createPatternSwatch(doc, placedImage) {
    try {
        placedImage.selected = true;
        $.writeln("[INFO] Applying action: make_pattern_apply from action set aaa");
        app.doScript('make_pattern_apply', 'aaa', false); // Ensure this action exists
        var patternSwatch = doc.swatches[doc.swatches.length - 1];
        $.writeln("[INFO] Pattern swatch created: " + patternSwatch.name);

        // Remove selected items
        var docSelected = doc.selection;
        for (var j = 0; j < docSelected.length; j++) {
            docSelected[j].remove();
        }
        return patternSwatch;
    } catch (e) {
        $.writeln("[ERROR] Error creating pattern swatch: " + e.message);
        throw new Error("Failed to create pattern swatch");
    }
}

function saveAsPDF(doc, outputPath, patternName, suffix) {
    var pdfFilePath = outputPath + "/" + patternName + "_" + suffix + ".pdf";
    $.writeln("[INFO] Attempting to save PDF: " + pdfFilePath);

    try {
        var pdfFile = new File(pdfFilePath);
        var pdfOptions = new PDFSaveOptions();
        pdfOptions.compatibility = PDFCompatibility.ACROBAT7;
        pdfOptions.optimization = true;
        pdfOptions.preserveEditability = false;

        doc.saveAs(pdfFile, pdfOptions);
        $.writeln("[INFO] PDF saved successfully: " + pdfFilePath);
        return pdfFilePath;
    } catch (e) {
        $.writeln("[ERROR] Error saving PDF: " + e.message);
        throw new Error("Failed to save PDF");
    }
}

function resizePlacedItem(item, targetWidth, targetHeight) {
    var maxAttempts = 10;
    for (var i = 0; i < maxAttempts; i++) {
        app.redraw();
        if (item.width > 0 && item.height > 0) {
            break;
        }
        $.sleep(100);
    }

    if (item.width === 0 || item.height === 0) {
        throw new Error("Failed to get item dimensions after " + maxAttempts + " attempts");
    }

    var currentWidth = item.width / 72; // Convert points to inches
    var currentHeight = item.height / 72;

    var scaleX = (targetWidth / currentWidth) * 100;
    var scaleY = (targetHeight / currentHeight) * 100;

    item.resize(scaleX, scaleY);
    app.redraw();
}

function processPattern(templatePath, outputPath, patternName, imagePath, suffix) {
    $.writeln("[INFO] Processing pattern: " + patternName);
    $.writeln("[INFO] Image path: " + imagePath);
    $.writeln("[INFO] Template path: " + templatePath);

    var imageFile = new File(imagePath);
    if (!imageFile.exists) {
        $.writeln("[ERROR] Image file not found: " + imagePath);
        throw new Error("Image file not found: " + imagePath);
    }

    var doc = openTemplate(templatePath);
    if (!doc) {
        $.writeln("[ERROR] Failed to open template: " + templatePath);
        throw new Error("Failed to open template: " + templatePath);
    }
    $.writeln("[INFO] Template opened successfully.");

    try {
        // Place and resize the image
        var placedItem = doc.placedItems.add();
        placedItem.file = imageFile;
        app.redraw();
        resizePlacedItem(placedItem, 6, 6); // Resize to 6in x 6in
        placedItem.embed();
        $.writeln("[INFO] Image placed and resized successfully.");

        // Create pattern swatch
        var patternSwatch = createPatternSwatch(doc, placedItem);

        // Apply pattern to <Path> in 'Layer 1'
        var layer = doc.layers.getByName("Layer 1");
        var pathItem = layer.pageItems.getByName("Image");
        pathItem.fillColor = patternSwatch.color;
        $.writeln("[INFO] Pattern applied to <Path> successfully.");

        // Update text layer inside <Group>
        var group = layer.groupItems.getByName("Footer");
        var textLayer = group.textFrames.getByName("Name");
        textLayer.contents = "Pattern: " + patternName;
        $.writeln("[INFO] Text updated to: " + textLayer.contents);

        // Save as PDF
        var pdfFilePath = saveAsPDF(doc, outputPath, patternName, suffix);

        // Close the document without saving changes
        doc.close(SaveOptions.DONOTSAVECHANGES);

        return { pdf: pdfFilePath };
    } catch (e) {
        if (doc) doc.close(SaveOptions.DONOTSAVECHANGES);
        $.writeln("[ERROR] Error in processPattern: " + e.message);
        throw e;
    }
}

function getRandomElement(array) {
    return array[Math.floor(Math.random() * array.length)];
}

function processAll() {
    var csvPath = "C:/Users/john/OneDrive/Desktop/aa-auto/printpanels/csv/meta_file_list.csv";

    // Get dynamically set output folder
    var outputFolder = getOutputFolder();

    // Define all template variations
    var sixFtTemplates = [
        "C:/Users/john/OneDrive/Desktop/aa-auto/printpanels/PatternName_6ft_panel.ai",
        "C:/Users/john/OneDrive/Desktop/aa-auto/printpanels/PatternName_6ft_panel (1).ai",
        "C:/Users/john/OneDrive/Desktop/aa-auto/printpanels/PatternName_6ft_panel (2).ai"
    ];

    var fifteenFtTemplates = [
        "C:/Users/john/OneDrive/Desktop/aa-auto/printpanels/PatternName_15ft_panel.ai",
        "C:/Users/john/OneDrive/Desktop/aa-auto/printpanels/PatternName_15ft_panel (1).ai",
        "C:/Users/john/OneDrive/Desktop/aa-auto/printpanels/PatternName_15ft_panel (2).ai"
    ];

    // Read input data
    var inputData = readCSV(csvPath);
    $.writeln("[INFO] Loaded CSV with " + inputData.length + " entries.");

    var outputData = [];
    for (var i = 0; i < inputData.length; i++) {
        var patternName = inputData[i].text;
        var imagePath = inputData[i].filePath;
        $.writeln("[INFO] Starting processing for: " + patternName);

        if (!patternName || !imagePath) {
            $.writeln("[WARNING] Skipping invalid row: " + patternName + ", " + imagePath);
            continue;
        }

        var row = [patternName, imagePath];

        try {
            var selected6ftTemplate = getRandomElement(sixFtTemplates);
            var selected15ftTemplate = getRandomElement(fifteenFtTemplates);

            var result6ft = processPattern(selected6ftTemplate, outputFolder, patternName, imagePath, "6");
            row.push(result6ft.pdf);

            var result15ft = processPattern(selected15ftTemplate, outputFolder, patternName, imagePath, "15");
            row.push(result15ft.pdf);

        } catch (e) {
            $.writeln("[ERROR] Unexpected error processing pattern '" + patternName + "': " + e.message);
            row.push("Error processing pattern: " + e.message);
        }

        outputData.push(row);
    }

    // Write processed data back to CSV
    writeCSV(csvPath, outputData);
    $.writeln("[INFO] Processing complete. Files saved to: " + outputFolder);
    
    // Write completion marker
    var completionMarker = new File(outputFolder + "/illustrator_complete.txt");
    completionMarker.open('w');
    completionMarker.write("Complete");
    completionMarker.close();

    // Quit Illustrator
    app.quit();
}

// Run the script
try {
    processAll();
} catch (e) {
    $.writeln("[ERROR] Script terminated unexpectedly: " + e.message);
    app.quit();  // Quit even if there's an error
}