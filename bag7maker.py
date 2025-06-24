from PIL import Image
import os
import time
import subprocess
import logging
import datetime
import traceback
from pathlib import Path
from config import BASE_FOLDER, OUTPUT_BASE_FOLDER, BAGS_FOLDER

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / "Downloads" / "design_template_log.txt"),
        logging.StreamHandler()
    ]
)

def create_image_tile(input_image_path, width_count, height_count, output_filename):
    """
    Creates a tiled image by repeating the input image in a grid pattern.
    
    Args:
        input_image_path: Path to the original image
        width_count: Number of times to repeat the image horizontally
        height_count: Number of times to repeat the image vertically
        output_filename: Filename for the output tiled image
    """
    # Open the original image
    try:
        original_img = Image.open(input_image_path)
        logging.info(f"Opened original image: {input_image_path}, size: {original_img.size}")
    except Exception as e:
        logging.error(f"Error opening image: {e}")
        return None
    
    # Get original image dimensions
    orig_width, orig_height = original_img.size
    
    # Calculate the dimensions for the new tiled image
    new_width = orig_width * width_count
    new_height = orig_height * height_count
    
    # Create a new blank image with the calculated dimensions
    tiled_img = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
    
    # Paste the original image multiple times to create the tile pattern
    for y in range(height_count):
        for x in range(width_count):
            tiled_img.paste(original_img, (x * orig_width, y * orig_height))
    
    # Save the resulting image
    tiled_img.save(output_filename)
    logging.info(f"Created tiled image: {output_filename}, size: {tiled_img.size}")
    return output_filename

def create_jsx_script(image_3x3_path, output_dir, input_basename, template_file_path):
    """Create a JSX script that processes images with the template file"""
    try:
        # Create a JSX script that can be directly run by Photoshop
        jsx_path = os.path.join(output_dir, f"Batch_Designs_{int(time.time())}.jsx")
        logging.info(f"Creating batch JSX file at: {jsx_path}")
        
        # Format paths for JSX
        image_3x3_path_jsx = image_3x3_path.replace("\\", "\\\\")
        output_dir_jsx = output_dir.replace("\\", "\\\\")
        template_file_path_jsx = template_file_path.replace("\\", "\\\\")
        
        # Create the JSX content
        jsx_content = '''#target photoshop
// Multiple Design Template Image Processor
// Generated on ''' + time.ctime() + '''

// Ensure we're targeting Photoshop
if (typeof app !== "undefined" && app.name !== "Adobe Photoshop") {
    throw new Error("This script requires Adobe Photoshop!");
}

// File paths configuration
var IMAGE_3X3_PATH = "''' + image_3x3_path_jsx + '''";
var OUTPUT_DIR = "''' + output_dir_jsx + '''";
var INPUT_BASENAME = "''' + input_basename + '''";
var TEMPLATE_FILE_PATH = "''' + template_file_path_jsx + '''";

// Target layers to apply design to
var TARGET_LAYERS = [
    "BAG 3 DESIGN",
    "BAG 3 DESIGN 2",
    "BAG 3 DESIGN 3",
    "BAG 2 DESIGN",
    "BAG 1 DESIGN",
    "BAG 1 DESIGN 2"
];

// Transform properties from screenshot
var TRANSFORM_X = -48;
var TRANSFORM_Y = -4;
var TRANSFORM_WIDTH = 408;
var TRANSFORM_HEIGHT = 408;
var TRANSFORM_ANGLE = 0.0;

// Recursive function to find a layer by name, even in layer sets (folders)
function findLayerRecursive(layerSet, layerName) {
    for (var i = 0; i < layerSet.layers.length; i++) {
        var layer = layerSet.layers[i];
        
        // Check if this is the layer we're looking for (case insensitive)
        if (layer.name.toUpperCase() === layerName.toUpperCase()) {
            return layer;
        }
        
        // If this is a layer set (folder), search inside it
        if (layer.typename === "LayerSet") {
            var foundLayer = findLayerRecursive(layer, layerName);
            if (foundLayer) return foundLayer;
        }
    }
    return null;
}

// Function to process a layer with a specific image
function processLayerWithImage(targetLayer, imagePath) {
    try {
        // Store the original visibility state
        var originalVisibility = targetLayer.visible;
        
        // Make sure the layer is visible for editing
        targetLayer.visible = true;
        
        // Activate the target layer and edit its contents
        app.activeDocument.activeLayer = targetLayer;
        
        // Check if the layer is a Smart Object
        var isSmartObject = false;
        try {
            var ref = new ActionReference();
            ref.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
            var desc = executeActionGet(ref);
            isSmartObject = desc.getBoolean(stringIDToTypeID("smartObject"));
        } catch(e) {
            isSmartObject = false;
        }
        
        // If it's not already a Smart Object, convert it
        if (!isSmartObject) {
            var idnewPlacedLayer = stringIDToTypeID("newPlacedLayer");
            executeAction(idnewPlacedLayer, undefined, DialogModes.NO);
        }
        
        // Open the Smart Object
        var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
        var desc = new ActionDescriptor();
        executeAction(idplacedLayerEditContents, desc, DialogModes.NO);
        
        // We are now inside the Smart Object
        var smartObjectDoc = app.activeDocument;
        
        // Check if the image exists
        var imageFile = new File(imagePath);
        if (!imageFile.exists) {
            smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // Open the image file
        var imageDoc = app.open(imageFile);
        
        // Select all and copy
        imageDoc.selection.selectAll();
        imageDoc.selection.copy();
        
        // Close the image document
        imageDoc.close(SaveOptions.DONOTSAVECHANGES);
        
        // Switch back to the Smart Object document
        app.activeDocument = smartObjectDoc;
        
        // Clear any existing content
        smartObjectDoc.selection.selectAll();
        smartObjectDoc.selection.clear();
        
        // Paste the copied image
        smartObjectDoc.paste();
        
        // Get the active layer (pasted image)
        var currentLayer = smartObjectDoc.activeLayer;
        
        // Apply transform properties
        // Calculate dimensions
        var originalWidth = currentLayer.bounds[2] - currentLayer.bounds[0];
        var originalHeight = currentLayer.bounds[3] - currentLayer.bounds[1];
        
        // Calculate scale percentages
        var scaleX = (TRANSFORM_WIDTH / originalWidth) * 100;
        var scaleY = (TRANSFORM_HEIGHT / originalHeight) * 100;
        
        // Resize to match dimensions
        currentLayer.resize(scaleX, scaleY, AnchorPosition.TOPLEFT);
        
        // Position at the specified coordinates
        currentLayer.translate(TRANSFORM_X - currentLayer.bounds[0], TRANSFORM_Y - currentLayer.bounds[1]);
        
        // Save and close the Smart Object
        smartObjectDoc.save();
        smartObjectDoc.close(SaveOptions.SAVECHANGES);
        
        // Restore the original visibility state
        targetLayer.visible = originalVisibility;
        
        return true;
    } catch (e) {
        alert("Error processing layer: " + e);
        return false;
    }
}

// Function to process the template
function processTemplate() {
    try {
        // Open the template file
        var templateFile = new File(TEMPLATE_FILE_PATH);
        if (!templateFile.exists) {
            alert("Template file not found: " + TEMPLATE_FILE_PATH);
            return false;
        }
        
        app.open(templateFile);
        var doc = app.activeDocument;
        
        // Process each target layer
        var successCount = 0;
        for (var i = 0; i < TARGET_LAYERS.length; i++) {
            var layerName = TARGET_LAYERS[i];
            var targetLayer = findLayerRecursive(doc, layerName);
            
            if (targetLayer) {
                var success = processLayerWithImage(targetLayer, IMAGE_3X3_PATH);
                if (success) {
                    successCount++;
                }
            } else {
                alert("Layer not found: " + layerName);
            }
        }
        
        // Save only as PNG (no PSD)
        var outputPNGPath = OUTPUT_DIR + "\\\\" + INPUT_BASENAME + "_design.png";
        var pngSaveOptions = new PNGSaveOptions();
        pngSaveOptions.compression = 0;
        pngSaveOptions.interlaced = false;
        
        // Save PNG only
        var outputPNGFile = new File(outputPNGPath);
        doc.saveAs(outputPNGFile, pngSaveOptions, true, Extension.LOWERCASE);
        
        // Close the template document WITHOUT saving any changes to the template
        doc.close(SaveOptions.DONOTSAVECHANGES);
        
        return successCount > 0;
    } catch (e) {
        alert("Error processing template: " + e);
        return false;
    }
}

// Function to safely close all open documents
function closeAllDocuments() {
    try {
        while (app.documents.length) {
            app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
        }
    } catch (e) {
        // Silently ignore any errors during document closing
    }
}

// Main execution
function main() {
    try {
        // Process the template
        var success = processTemplate();
        
        if (success) {
            alert("Successfully processed " + TARGET_LAYERS.length + " layers with design.");
        } else {
            alert("Failed to process design template.");
        }
        
        // Close any remaining open documents
        closeAllDocuments();
    } catch (e) {
        alert("Error executing script: " + e);
        closeAllDocuments();
    }
}

// Function to quit Photoshop after a delay
function quitPhotoshop() {
    $.sleep(2000); // 2 second delay to ensure files are saved
    var idquit = stringIDToTypeID("quit");
    executeAction(idquit, undefined, DialogModes.NO);
}

// Run the main function
main();

// IMPORTANT: Quit Photoshop after processing
quitPhotoshop();
'''
        
        # Write the JSX content to file
        with open(jsx_path, 'w', encoding='utf-8') as f:
            f.write(jsx_content)
        
        logging.info(f"Created batch JSX file for processing design template")
        return jsx_path
    except Exception as e:
        logging.error(f"Error creating JSX script: {e}")
        logging.exception("Exception details:")
        return None

def process_design_template(input_image_path, template_file_path):
    """Process a given image with the design template.
    
    Args:
        input_image_path: Path to the original image
        template_file_path: Path to the Photoshop template
        
    Returns:
        List of paths to the generated output images
    """
    try:
        logging.info(f"Processing image: {input_image_path}")
        
        # Get the directory and filename parts
        input_dir = os.path.dirname(input_image_path)
        input_basename = os.path.basename(input_image_path)
        filename_without_ext = os.path.splitext(input_basename)[0]
        
        # Generate path for the tiled image
        image_3x3_path = os.path.join(input_dir, f"{filename_without_ext}_3x3_tile.png")
        
        # Generate path for the output PNG image only
        output_png_path = os.path.join(input_dir, f"{filename_without_ext}_design.png")
        
        # Create the tiled image (3x3)
        logging.info("Creating 3x3 tiled image...")
        create_image_tile(input_image_path, 3, 3, image_3x3_path)
        
        # Create JSX script
        jsx_script = create_jsx_script(image_3x3_path, input_dir, filename_without_ext, template_file_path)
        
        if not jsx_script:
            logging.error("Failed to create JSX script")
            return []
            
        # Execute the JSX script with Photoshop
        try:
            # Find Photoshop executable
            photoshop_exe = r"C:\Program Files\Adobe\Adobe Photoshop 2025\Photoshop.exe"
            if not os.path.exists(photoshop_exe):
                photoshop_exe = r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe"
            if not os.path.exists(photoshop_exe):
                photoshop_exe = r"C:\Program Files\Adobe\Adobe Photoshop 2023\Photoshop.exe"
            
            if os.path.exists(photoshop_exe):
                logging.info(f"Executing JSX script with Photoshop: {photoshop_exe}")
                
                # Run the script
                process = subprocess.Popen([photoshop_exe, "-r", str(jsx_script)])
                
                # Wait for Photoshop to finish
                try:
                    process.wait(timeout=600)  # 10-minute timeout
                    logging.info(f"Photoshop finished with return code: {process.returncode}")
                    
                    # Wait a moment for files to be saved
                    time.sleep(5)
                    
                    # Make sure Photoshop is closed
                    try:
                        os.system("taskkill /f /im Photoshop.exe")
                        logging.info("Sent additional kill command to ensure Photoshop is closed")
                    except Exception as e:
                        logging.warning(f"Error while attempting to kill Photoshop: {e}")
                    
                    # Check for output files
                    result_paths = []
                    expected_paths = [output_png_path]  # Only checking for PNG output
                    
                    for path in expected_paths:
                        if os.path.exists(path):
                            logging.info(f"Found output file: {path}")
                            result_paths.append(path)
                        else:
                            logging.warning(f"Expected output file not found: {path}")
                    
                    return result_paths
                    
                except subprocess.TimeoutExpired:
                    logging.error("Photoshop process timed out after 10 minutes")
                    # Kill Photoshop if it's still running
                    process.kill()
                    try:
                        os.system("taskkill /f /im Photoshop.exe")
                    except:
                        pass
            else:
                logging.error("Photoshop executable not found")
        except Exception as e:
            logging.error(f"Error executing JSX script: {e}")
            # Make sure to kill Photoshop even if there's an error
            try:
                os.system("taskkill /f /im Photoshop.exe")
            except:
                pass
            
        return []
    except Exception as e:
        logging.error(f"Error in process_design_template: {e}")
        logging.exception("Exception details:")
        # Final attempt to make sure Photoshop is closed
        try:
            os.system("taskkill /f /im Photoshop.exe")
        except:
            pass
        return []

if __name__ == "__main__":
    # Input paths with your specific file locations
    input_image_path = os.path.join(OUTPUT_BASE_FOLDER, "2025-04-07_11-36-15/Sleigh Ball.png")
    template_file_path = os.path.join(BAGS_FOLDER, "Bag 7.psd")
    
    print(f"Processing image: {input_image_path}")
    print(f"Using template: {template_file_path}")
    
    # Process the image with the template
    output_paths = process_design_template(input_image_path, template_file_path)
    
    if output_paths:
        print(f"Successfully processed image with template:")
        for path in output_paths:
            print(f"- {path}")
    else:
        print("Failed to process image with template")
    
    # Final verification that Photoshop is closed
    print("Ensuring Photoshop is closed...")
    try:
        os.system("taskkill /f /im Photoshop.exe")
    except Exception as e:
        print(f"Error while trying to verify Photoshop is closed: {e}")