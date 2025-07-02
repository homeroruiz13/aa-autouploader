// Template Diagnostics Script
// Run this script to analyze your bag and tissue templates
// This will help identify the correct layer names and structure

function analyzeTemplate(templatePath, templateName) {
    try {
        var templateFile = new File(templatePath);
        if (!templateFile.exists) {
            $.writeln("Template not found: " + templatePath);
            return;
        }
        
        $.writeln("\n=== ANALYZING " + templateName + " ===");
        $.writeln("Path: " + templatePath);
        
        var doc = app.open(templateFile);
        
        $.writeln("Document name: " + doc.name);
        $.writeln("Document dimensions: " + doc.width + " x " + doc.height);
        $.writeln("Total layers: " + doc.layers.length);
        
        // Analyze the layer structure
        $.writeln("\nLAYER STRUCTURE:");
        analyzeLayerStructure(doc, 0);
        
        // Look for smart objects specifically
        $.writeln("\nSMART OBJECTS FOUND:");
        findSmartObjects(doc, "");
        
        doc.close(SaveOptions.DONOTSAVECHANGES);
        
    } catch (e) {
        $.writeln("Error analyzing " + templateName + ": " + e.toString());
    }
}

function analyzeLayerStructure(container, depth) {
    var indent = "";
    for (var i = 0; i < depth; i++) {
        indent += "  ";
    }
    
    if (!container.layers) {
        return;
    }
    
    for (var i = 0; i < container.layers.length; i++) {
        var layer = container.layers[i];
        var typeInfo = "";
        
        if (layer.typename === "LayerSet") {
            typeInfo = " [GROUP]";
        } else if (layer.kind === LayerKind.SMARTOBJECT) {
            typeInfo = " [SMART OBJECT] *** TARGET ***";
        } else if (layer.kind === LayerKind.NORMAL) {
            typeInfo = " [NORMAL]";
        } else {
            typeInfo = " [" + layer.kind + "]";
        }
        
        $.writeln(indent + "- " + layer.name + typeInfo + " (visible: " + layer.visible + ")");
        
        if (layer.typename === "LayerSet") {
            analyzeLayerStructure(layer, depth + 1);
        }
    }
}

function findSmartObjects(container, path) {
    if (!container.layers) {
        return;
    }
    
    for (var i = 0; i < container.layers.length; i++) {
        var layer = container.layers[i];
        var currentPath = path ? path + " > " + layer.name : layer.name;
        
        if (layer.kind === LayerKind.SMARTOBJECT) {
            $.writeln("  SMART OBJECT: " + currentPath);
        }
        
        if (layer.typename === "LayerSet") {
            findSmartObjects(layer, currentPath);
        }
    }
}

// Get the script's directory
var scriptFile = new File($.fileName);
var scriptDir = scriptFile.parent;

// Define template paths to analyze
var templatesToAnalyze = [
    { path: scriptDir + "/Bags & Tissues/Bag 1.psd", name: "Bag 1" },
    { path: scriptDir + "/Bags & Tissues/Bag 2.psd", name: "Bag 2" },
    { path: scriptDir + "/Bags & Tissues/Bag 3.psd", name: "Bag 3" },
    { path: scriptDir + "/Bags & Tissues/Bag 4.psd", name: "Bag 4" },
    { path: scriptDir + "/Bags & Tissues/Bag 5.psd", name: "Bag 5" },
    { path: scriptDir + "/Bags & Tissues/Bag 6.psd", name: "Bag 6" },
    { path: scriptDir + "/Bags & Tissues/Bag 7.psd", name: "Bag 7" },
    { path: scriptDir + "/Bags & Tissues/Tissue 1.psd", name: "Tissue 1" },
    { path: scriptDir + "/Bags & Tissues/Tissue 2.psd", name: "Tissue 2" },
    { path: scriptDir + "/Bags & Tissues/Tissue 3.psd", name: "Tissue 3" },
    { path: scriptDir + "/Bags & Tissues/Table Runner 1.psd", name: "Table Runner 1" },
    { path: scriptDir + "/Bags & Tissues/Table Runner 2.psd", name: "Table Runner 2" },
    { path: scriptDir + "/Bags & Tissues/Table Runner 3.psd", name: "Table Runner 3" }
];

$.writeln("TEMPLATE DIAGNOSTICS STARTING...");
$.writeln("=====================================");

// Analyze each template
for (var i = 0; i < templatesToAnalyze.length; i++) {
    analyzeTemplate(templatesToAnalyze[i].path, templatesToAnalyze[i].name);
}

$.writeln("\n=====================================");
$.writeln("DIAGNOSTICS COMPLETE");
$.writeln("=====================================");
$.writeln("\nLook for lines marked with '*** TARGET ***' - these are the Smart Objects");
$.writeln("that should be used as target layers in your processing scripts.");
$.writeln("\nIf no Smart Objects are found, check that your templates are set up correctly.");

// Don't quit Photoshop automatically so you can see the results