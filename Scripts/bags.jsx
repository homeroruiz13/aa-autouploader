#target photoshop

/*
 Bag Templates Image Processor – Bags 1 / 2 / 3
 -----------------------------------------------------------------------------
 This script mirrors the behaviour of Scripts/source3.jsx but for the
 personalised shopping-bag mock-ups.  It expects the regular pipeline to have
 already created *_6.png* (6×6) and *_3.png* (3×3) pattern tiles inside
 Download/<timestamp>/ .  It searches the most-recent timestamped Download &
 Output folders relative to the workspace root directory and, for each tile,
 injects the design into the PSD template(s) listed below.

 Bag 1 – Bags & Tissues/Bag 1.psd – uses the *_3.png* tile       → *_bag1.png
 Bag 2 – Bags & Tissues/Bag 2.psd – uses the *_6.png* tile       → *_bag2.png
 Bag 3 – Bags & Tissues/Bag 3.psd – uses the *_3.png* tile       → *_bag3.png
*/

(function () {
    // =====================================================================
    // Helper – newest folder YYYY-MM-DD_HH-MM-SS
    // =====================================================================
    function getMostRecentFolder(basePath) {
        var base = new Folder(basePath);
        if (!base.exists) {
            alert("Folder not found: " + basePath);
            return null;
        }
        var child = base.getFiles(function (f) {
            return f instanceof Folder && /^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(f.name);
        });
        if (child.length === 0) {
            alert("No timestamped sub-folders in " + basePath);
            return null;
        }
        child.sort(function (a, b) { return b.name.localeCompare(a.name); });
        return child[0];
    }

    // =====================================================================
    // Resolve workspace root and recent Download/Output paths
    // =====================================================================
    var scriptFile = new File($.fileName);
    var scriptDir = scriptFile.parent;             // .../Scripts
    var workspaceRoot = scriptDir.parent;          // repo root

    var downloadFolder = getMostRecentFolder(workspaceRoot + "/Download");
    var outputFolder   = getMostRecentFolder(workspaceRoot + "/Output");

    if (!downloadFolder || !outputFolder) {
        return; // alerts already shown
    }

    // PSD template locations (relative to workspace root) - FIXED: Use Bags & Tissues folder
    var bagTemplatePaths = [
        workspaceRoot + "/Bags & Tissues/Bag 1.psd", // 0 – Bag 1
        workspaceRoot + "/Bags & Tissues/Bag 2.psd", // 1 – Bag 2
        workspaceRoot + "/Bags & Tissues/Bag 3.psd"  // 2 – Bag 3
    ];

    // =====================================================================
    // Locate pattern PNGs
    // =====================================================================
    var patternFiles = Folder(downloadFolder).getFiles("*.png");

    // ------------------------------------------------------------------
    // Utility – recursive layer search (case-insensitive)
    // ------------------------------------------------------------------
    function findLayerRecursive(container, name) {
        if (!container.layers) return null;
        for (var i = 0; i < container.layers.length; i++) {
            var lyr = container.layers[i];
            if (lyr.name.toUpperCase() === name.toUpperCase()) return lyr;
            if (lyr.typename === "LayerSet") {
                var found = findLayerRecursive(lyr, name);
                if (found) return found;
            }
        }
        return null;
    }

    // ------------------------------------------------------------------
    // Core – inject pattern into PSD and export PNG
    // ------------------------------------------------------------------
    function processBag(templatePath, patternPath, outFolder, basename, tag) {
        var tpl = new File(templatePath);
        if (!tpl.exists) {
            alert("Missing template: " + templatePath);
            return;
        }
        var doc = app.open(tpl);
        var targetLayer;

        if (tag === "bag1") {
            targetLayer = findLayerRecursive(doc, "CHANGE DESIGN HERE");
        } else if (tag === "bag2") {
            var grp = findLayerRecursive(doc, "Bag 2");
            if (grp) targetLayer = findLayerRecursive(grp, "CHANGE DESIGN HERE");
        } else if (tag === "bag3") {
            var grp3 = findLayerRecursive(doc, "Bag 3");
            if (grp3) targetLayer = findLayerRecursive(grp3, "CHANGE DESIGN");
        }
        if (!targetLayer) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            alert("Layer not found for " + tag);
            return;
        }

        var visState = targetLayer.visible;
        targetLayer.visible = true;
        doc.activeLayer = targetLayer;

        var idEdit = stringIDToTypeID("placedLayerEditContents");
        executeAction(idEdit, new ActionDescriptor(), DialogModes.NO);

        var soDoc = app.activeDocument;
        var patFile = new File(patternPath);
        var patDoc = app.open(patFile);
        patDoc.selection.selectAll();
        patDoc.selection.copy();
        patDoc.close(SaveOptions.DONOTSAVECHANGES);

        app.activeDocument = soDoc;
        
        // FIXED: Safer method to clear existing content without using selection.clear()
        try {
            // Remove all layers except the background layer
            while (soDoc.artLayers.length > 1) {
                soDoc.artLayers[0].remove();
            }
        } catch (removeError) {
            // If we can't remove layers, try selecting all and filling with white
            try {
                soDoc.selection.selectAll();
                var fillColor = new SolidColor();
                fillColor.rgb.red = 255;
                fillColor.rgb.green = 255;
                fillColor.rgb.blue = 255;
                soDoc.selection.fill(fillColor);
            } catch (fillError) {
                // If that fails too, just proceed with paste (will overlay)
            }
        }
        
        soDoc.paste();
        var lay = soDoc.activeLayer;

        // --- Transform values (copied from Python scripts) -------------
        var cfg = {
            bag1: {w:1554,h:1440,x:-187,y:-583},
            bag2: {w:1897,h:1897,x:-151,y:-391},
            bag3: {w:1250,h:1250,x:-128,y:-481}
        }[tag];

        var curW = lay.bounds[2] - lay.bounds[0];
        var curH = lay.bounds[3] - lay.bounds[1];
        lay.resize(cfg.w / curW * 100, cfg.h / curH * 100, AnchorPosition.TOPLEFT);
        lay.translate(-lay.bounds[0] + cfg.x, -lay.bounds[1] + cfg.y);

        soDoc.save();
        soDoc.close(SaveOptions.SAVECHANGES);
        targetLayer.visible = visState;

        // Special layer hide for Bag 3 background paper
        if (tag === "bag3") {
            var paper = findLayerRecursive(doc, "midsummer-grovepainted-paper-524010 copia");
            if (paper) paper.visible = false;
        }

        // Export PNG
        var outFile = new File(outFolder + "/" + basename + "_" + tag + ".png");
        var opts = new ExportOptionsSaveForWeb();
        opts.format = SaveDocumentType.PNG;
        opts.PNG8 = false;
        opts.quality = 100;
        doc.exportDocument(outFile, ExportType.SAVEFORWEB, opts);
        doc.close(SaveOptions.DONOTSAVECHANGES);
    }

    // =================================================================
    // Iterate PNGs – decide which templates to process for each file
    // =================================================================
    for (var i = 0; i < patternFiles.length; i++) {
        var f = patternFiles[i];
        var nameNoExt = f.name.replace(/\.png$/i, "");

        if (nameNoExt.slice(-2) === "_6") {
            // Bag 2 uses 6×6 tile
            processBag(bagTemplatePaths[1], f.fsName, outputFolder.fsName, nameNoExt, "bag2");

            // Look for matching *_3.png* tile for Bag 1 & Bag 3
            var match3 = new File(f.parent + "/" + nameNoExt.replace("_6", "_3") + ".png");
            if (match3.exists) {
                processBag(bagTemplatePaths[0], match3.fsName, outputFolder.fsName, match3.name.replace(/\.png$/i, ""), "bag1");
                processBag(bagTemplatePaths[2], match3.fsName, outputFolder.fsName, match3.name.replace(/\.png$/i, ""), "bag3");
            }
        }
    }

    // Exit Photoshop when complete so the calling Python script regains control
    executeAction(charIDToTypeID("quit"), undefined, DialogModes.ALL);
})(); 