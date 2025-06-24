from PIL import Image
import os
import time
import subprocess
import logging
import datetime
from pathlib import Path
from config import BASE_FOLDER, TEMPLATE_IMAGES_FOLDER, OUTPUT_BASE_FOLDER

# Paths configuration
TEMPLATE_PATH = os.path.join(TEMPLATE_IMAGES_FOLDER, "Table Runner 1.psd")
TEST_IMAGE_PATH = os.path.join(OUTPUT_BASE_FOLDER, "2025-04-09_16-11-56/bags/Always the Bride_tiled.png")
OUTPUT_FOLDER = os.path.join(BASE_FOLDER, "New folder (2)")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(OUTPUT_FOLDER, "table_runner_log.txt")),
        logging.StreamHandler()
    ]
)

def create_jsx_script(image_path, output_folder):
    """Create a JSX script that processes the image with the Table Runner template"""
    try:
        # Create a unique filename for the JSX script
        timestamp = int(time.time())
        jsx_path = os.path.join(output_folder, f"TableRunner_{timestamp}.jsx")
        logging.info(f"Creating JSX file at: {jsx_path}")
        
        # Format paths for JSX
        template_path = TEMPLATE_PATH.replace("\\", "\\\\")
        image_path_formatted = image_path.replace("\\", "\\\\")
        
        # Get filename without extension for output file naming
        image_filename = os.path.basename(image_path)
        image_name_without_ext = os.path.splitext(image_filename)[0]
        output_path = os.path.join(output_folder, f"{image_name_without_ext}_tablerunner.png").replace("\\", "\\\\")
        
        # Create the JSX content
        jsx_content = f'''#target photoshop
// Table Runner Template Image Processor
// Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

// Ensure we're targeting Photoshop
if (typeof app !== "undefined" && app.name !== "Adobe Photoshop") {{
    alert("This script requires Adobe Photoshop!");
    throw new Error("This script requires Adobe Photoshop!");
}}

// Wait function to ensure operations complete
function waitForPhotoshop(description, msec) {{
    var waitTime = msec || 300; // Default 300ms
    $.sleep(waitTime);
}}

// Function to verify document is properly open
function verifyDocumentOpen(doc, maxAttempts) {{
    if (!maxAttempts) maxAttempts = 5;
    
    for (var i = 0; i < maxAttempts; i++) {{
        try {{
            if (doc && doc.name) {{
                return true; // Document is open and accessible
            }}
        }} catch (e) {{
            // Document not ready yet
        }}
        $.sleep(100);
    }}
    
    return false; // Failed to verify document
}}

// Recursive function to find a layer by name, even in layer sets (folders)
function findLayerRecursive(layerSet, layerName) {{
    for (var i = 0; i < layerSet.layers.length; i++) {{
        var layer = layerSet.layers[i];
        
        // Check if this is the layer we're looking for (case insensitive)
        if (layer.name.toUpperCase() === layerName.toUpperCase()) {{
            return layer;
        }}
        
        // If this is a layer set (folder), search inside it
        if (layer.typename === "LayerSet") {{
            var foundLayer = findLayerRecursive(layer, layerName);
            if (foundLayer) return foundLayer;
        }}
    }}
    return null;
}}

function processTableRunner() {{
    try {{
        // Open the template file
        var templateFile = new File("{template_path}");
        if (!templateFile.exists) {{
            alert("Template file not found: {template_path}");
            return false;
        }}
        
        app.open(templateFile);
        waitForPhotoshop("Opening Table Runner template", 500);
        
        var doc = app.activeDocument;
        if (!verifyDocumentOpen(doc, 10)) {{
            alert("Failed to open template document");
            return false;
        }}
        
        // Find the "CHANGE DESIGN HERE" layer using recursive search
        var targetLayer = findLayerRecursive(doc, "CHANGE DESIGN HERE");
        
        if (!targetLayer) {{
            alert("Could not find 'CHANGE DESIGN HERE' layer");
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }}
        
        // Store the original visibility state
        var originalVisibility = targetLayer.visible;
        
        // Make sure the layer is visible for editing
        targetLayer.visible = true;
        
        // Activate the target layer and edit its contents
        doc.activeLayer = targetLayer;
        waitForPhotoshop("Setting active layer", 300);
        
        // Open the Smart Object
        var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
        var desc = new ActionDescriptor();
        executeAction(idplacedLayerEditContents, desc, DialogModes.NO);
        waitForPhotoshop("Opening Smart Object", 800);
        
        // We are now inside the Smart Object
        var smartObjectDoc = app.activeDocument;
        if (!verifyDocumentOpen(smartObjectDoc, 10)) {{
            alert("Failed to open Smart Object");
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }}
        
        // Check if the image exists
        var imageFile = new File("{image_path_formatted}");
        if (!imageFile.exists) {{
            alert("Image file not found: {image_path_formatted}");
            smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES);
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }}
        
        // Open the image file
        var imageDoc = app.open(imageFile);
        waitForPhotoshop("Opening pattern image", 500);
        if (!verifyDocumentOpen(imageDoc, 10)) {{
            alert("Failed to open image");
            smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES);
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }}
        
        // Select all and copy
        imageDoc.selection.selectAll();
        imageDoc.selection.copy();
        waitForPhotoshop("Copying pattern", 300);
        
        // Close the image document
        imageDoc.close(SaveOptions.DONOTSAVECHANGES);
        waitForPhotoshop("Closing pattern document", 300);
        
        // Switch back to the Smart Object document
        app.activeDocument = smartObjectDoc;
        waitForPhotoshop("Switching to Smart Object", 300);
        
        // Clear any existing layers except the background if it exists
        while (smartObjectDoc.artLayers.length > 1) {{
            smartObjectDoc.artLayers[0].remove();
        }}
        
        // Paste the copied image
        smartObjectDoc.paste();
        waitForPhotoshop("Pasting pattern", 300);
        
        // Get the active layer (pasted image)
        var currentLayer = smartObjectDoc.activeLayer;
        
        // Calculate current dimensions
        var width = currentLayer.bounds[2] - currentLayer.bounds[0];
        var height = currentLayer.bounds[3] - currentLayer.bounds[1];
        
        // From your screenshot, use the transform values:
        // W: 879 px, H: 1020 px, X: 79 px, Y: 0 px
        var targetWidth = 879;
        var targetHeight = 1020;
        
        // Calculate scale factors
        var widthRatio = targetWidth / width * 100;
        var heightRatio = targetHeight / height * 100;
        
        // Resize the layer
        currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
        waitForPhotoshop("Resizing layer", 300);
        
        // Position the layer at X: 79 px, Y: 0 px from the Transform panel in the screenshot
        currentLayer.translate(-currentLayer.bounds[0] + 79, -currentLayer.bounds[1] + 0);
        waitForPhotoshop("Positioning layer", 300);
        
        // Save and close the Smart Object
        smartObjectDoc.save();
        waitForPhotoshop("Saving Smart Object", 500);
        
        smartObjectDoc.close(SaveOptions.SAVECHANGES);
        waitForPhotoshop("Closing Smart Object", 500);
        
        // Restore the original visibility state
        targetLayer.visible = originalVisibility;
        
        // Save as PNG
        var saveOptions = new PNGSaveOptions();
        saveOptions.compression = 0; // 0-9, where 0 is no compression
        saveOptions.interlaced = false;
        
        var outputFile = new File("{output_path}");
        doc.saveAs(outputFile, saveOptions, true, Extension.LOWERCASE);
        waitForPhotoshop("Saving final PNG", 800);
        
        // Close the template document
        doc.close(SaveOptions.DONOTSAVECHANGES);
        waitForPhotoshop("Closing template document", 500);
        
        return true;
    }} catch (e) {{
        alert("Error: " + e);
        // Try to close any open documents on error
        try {{
            if (app.documents.length > 0) {{
                app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
            }}
        }} catch (closeErr) {{
            // Ignore errors during cleanup
        }}
        return false;
    }}
}}

// Function to safely close all open documents
function closeAllDocuments() {{
    try {{
        while (app.documents.length) {{
            app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
            waitForPhotoshop("Closing document", 300);
        }}
    }} catch (e) {{
        // Silently ignore any errors during document closing
    }}
}}

// Main execution
processTableRunner();
closeAllDocuments();

// Function to quit Photoshop after a delay
function quitPhotoshop() {{
    $.sleep(5000); // 5 second delay to ensure files are saved
    var idquit = stringIDToTypeID("quit");
    executeAction(idquit, undefined, DialogModes.NO);
}}

// Uncomment this line if you want Photoshop to quit after processing
// quitPhotoshop();
'''
        
        # Write the JSX content to file
        with open(jsx_path, 'w', encoding='utf-8') as f:
            f.write(jsx_content)
        
        logging.info(f"Created JSX file successfully: {jsx_path}")
        return jsx_path
    except Exception as e:
        logging.error(f"Error creating JSX script: {e}")
        logging.exception("Exception details:")
        return None

def process_table_runner(image_path, output_folder):
    """Process a single image with the Table Runner template"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Verify input image exists
        if not os.path.exists(image_path):
            logging.error(f"Input image not found: {image_path}")
            return None
            
        logging.info(f"Processing table runner with image: {image_path}")
        
        # Create the JSX script
        jsx_script = create_jsx_script(image_path, output_folder)
        if not jsx_script:
            logging.error("Failed to create JSX script")
            return None
            
        # Execute the JSX script with Photoshop
        try:
            # Find Photoshop executable - check multiple possible locations
            photoshop_exe = r"C:\Program Files\Adobe\Adobe Photoshop 2025\Photoshop.exe"
            if not os.path.exists(photoshop_exe):
                photoshop_exe = r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe"
            if not os.path.exists(photoshop_exe):
                photoshop_exe = r"C:\Program Files\Adobe\Adobe Photoshop 2023\Photoshop.exe"
            
            if os.path.exists(photoshop_exe):
                logging.info(f"Executing JSX script with Photoshop: {photoshop_exe}")
                
                # Run the script
                process = subprocess.Popen([photoshop_exe, "-r", jsx_script])
                
                # Wait for Photoshop to finish with a timeout (5 minutes)
                try:
                    process.wait(timeout=300)
                    logging.info(f"Photoshop finished with return code: {process.returncode}")
                    
                    # Wait a moment for files to be saved
                    time.sleep(3)
                    
                    # Generate the expected output filename
                    image_filename = os.path.basename(image_path)
                    image_name_without_ext = os.path.splitext(image_filename)[0]
                    expected_output = os.path.join(output_folder, f"{image_name_without_ext}_tablerunner.png")
                    
                    # Check if the output file exists
                    if os.path.exists(expected_output):
                        logging.info(f"Successfully created table runner: {expected_output}")
                        return expected_output
                    else:
                        logging.error(f"Output file not found: {expected_output}")
                        return None
                        
                except subprocess.TimeoutExpired:
                    logging.error("Photoshop process timed out after 5 minutes")
                    # Kill Photoshop if it's still running
                    process.kill()
                    try:
                        os.system("taskkill /f /im Photoshop.exe")
                    except:
                        pass
            else:
                logging.error("Photoshop executable not found")
                return None
        except Exception as e:
            logging.error(f"Error executing JSX script: {e}")
            logging.exception("Exception details:")
            return None
    except Exception as e:
        logging.error(f"Error processing table runner: {e}")
        logging.exception("Exception details:")
        return None

if __name__ == "__main__":
    # Process the test image
    output_path = process_table_runner(TEST_IMAGE_PATH, OUTPUT_FOLDER)
    
    if output_path:
        print(f"Success! Table runner created at: {output_path}")
    else:
        print("Failed to create table runner.")