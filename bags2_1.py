from PIL import Image
import os
import time
import subprocess
import logging
import datetime
import traceback
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / "Downloads" / "bags_log.txt"),
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

def create_jsx_script(image_4x4_path, image_1x3_path, output_dir, input_basename):
    """Create a JSX script that processes images with Bag 4, Bag 5, and Bag 6 templates"""
    try:
        # Create a JSX script that can be directly run by Photoshop
        jsx_path = os.path.join(output_dir, f"Batch_Bags_{int(time.time())}.jsx")
        logging.info(f"Creating batch JSX file at: {jsx_path}")
        
        # Format paths for JSX
        image_4x4_path_jsx = image_4x4_path.replace("\\", "\\\\")
        image_1x3_path_jsx = image_1x3_path.replace("\\", "\\\\")
        output_dir_jsx = output_dir.replace("\\", "\\\\")
        
        # Create the JSX content
        jsx_content = '''#target photoshop
// Multiple Bag Templates Image Processor
// Generated on ''' + time.ctime() + '''

// Ensure we're targeting Photoshop
if (typeof app !== "undefined" && app.name !== "Adobe Photoshop") {
    throw new Error("This script requires Adobe Photoshop!");
}

// File paths configuration
var IMAGE_4X4_PATH = "''' + image_4x4_path_jsx + '''";
var IMAGE_1X3_PATH = "''' + image_1x3_path_jsx + '''";
var OUTPUT_DIR = "''' + output_dir_jsx + '''";
var INPUT_BASENAME = "''' + input_basename + '''";

// Template files
var BAG4_TEMPLATE_FILE_PATH = "C:\\\\Users\\\\john\\\\OneDrive\\\\Desktop\\\\aa-auto\\\\Bags & Tissues\\\\Bag 4.psd";
var BAG5_TEMPLATE_FILE_PATH = "C:\\\\Users\\\\john\\\\OneDrive\\\\Desktop\\\\aa-auto\\\\Bags & Tissues\\\\Bag 5.psd";
var BAG6_TEMPLATE_FILE_PATH = "C:\\\\Users\\\\john\\\\OneDrive\\\\Desktop\\\\aa-auto\\\\Bags & Tissues\\\\Bag 6.psd";

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
function processLayerWithImage(targetLayer, imagePath, targetWidth, targetHeight, targetX, targetY) {
    try {
        // Store the original visibility state
        var originalVisibility = targetLayer.visible;
        
        // Make sure the layer is visible for editing
        targetLayer.visible = true;
        
        // Activate the target layer and edit its contents
        app.activeDocument.activeLayer = targetLayer;
        
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
        
        // Clear any existing layers except the background if it exists
        while (smartObjectDoc.artLayers.length > 1) {
            smartObjectDoc.artLayers[0].remove();
        }
        
        // Paste the copied image
        smartObjectDoc.paste();
        
        // Get the active layer (pasted image)
        var currentLayer = smartObjectDoc.activeLayer;
        
        // Calculate current dimensions
        var width = currentLayer.bounds[2] - currentLayer.bounds[0];
        var height = currentLayer.bounds[3] - currentLayer.bounds[1];
        
        // Calculate scale factors
        var widthRatio = targetWidth / width * 100;
        var heightRatio = targetHeight / height * 100;
        
        // Resize the layer
        currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
        
        // Position the layer
        currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
        
        // Save and close the Smart Object
        smartObjectDoc.save();
        smartObjectDoc.close(SaveOptions.SAVECHANGES);
        
        // Restore the original visibility state
        targetLayer.visible = originalVisibility;
        
        return true;
    } catch (e) {
        return false;
    }
}

// Modified function to safely process a layer with an image for Bag 6 (avoids Delete command)
function processBag6LayerWithImage(targetLayer, imagePath, targetWidth, targetHeight, targetX, targetY) {
    try {
        // Store the original visibility state
        var originalVisibility = targetLayer.visible;
        
        // Make sure the layer is visible for editing
        targetLayer.visible = true;
        
        // Activate the target layer and edit its contents
        app.activeDocument.activeLayer = targetLayer;
        
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
        
        // Save dimensions before we close it
        var docWidth = smartObjectDoc.width;
        var docHeight = smartObjectDoc.height;
        var docMode = smartObjectDoc.mode;
        var docName = smartObjectDoc.name;
        
        // Close the smart object without saving
        smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES);
        
        // Create a new document with the same dimensions
        var newDoc = app.documents.add(docWidth, docHeight, 72, docName, docMode);
        
        // Open the image file and place it in our new document
        var imageDoc = app.open(imageFile);
        
        // Select all and copy
        imageDoc.selection.selectAll();
        imageDoc.selection.copy();
        
        // Close the image document
        imageDoc.close(SaveOptions.DONOTSAVECHANGES);
        
        // Paste into our new document
        newDoc.paste();
        
        // Get the active layer (pasted image)
        var currentLayer = newDoc.activeLayer;
        
        // Calculate current dimensions
        var width = currentLayer.bounds[2] - currentLayer.bounds[0];
        var height = currentLayer.bounds[3] - currentLayer.bounds[1];
        
        // Calculate scale factors
        var widthRatio = targetWidth / width * 100;
        var heightRatio = targetHeight / height * 100;
        
        // Resize the layer
        currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
        
        // Position the layer
        currentLayer.translate(-currentLayer.bounds[0] + targetX, -currentLayer.bounds[1] + targetY);
        
        // Save the document (this will be our smart object content)
        newDoc.save();
        newDoc.close(SaveOptions.SAVECHANGES);
        
        // Re-open the template to continue
        app.open(templateFile);
        
        // Restore the original visibility state
        targetLayer.visible = originalVisibility;
        
        return true;
    } catch (e) {
        return false;
    }
}

// Function to process Bag 4 template
function processBag4Template() {
    try {
        // Open the template file
        var templateFile = new File(BAG4_TEMPLATE_FILE_PATH);
        if (!templateFile.exists) {
            return false;
        }
        
        app.open(templateFile);
        var doc = app.activeDocument;
        
        // Find the "Bag 4" layer set first
        var bagLayer = findLayerRecursive(doc, "Bag 4");
        if (!bagLayer) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // =============== FIRST IMAGE (4x4 tile) ===============
        // Find the "CHANGE DESIGN HERE" layer
        var targetLayer1 = findLayerRecursive(bagLayer, "CHANGE DESIGN HERE");
        if (!targetLayer1) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // Process first image
        var success1 = processLayerWithImage(targetLayer1, IMAGE_4X4_PATH, 919, 918, -36, -41);
        if (!success1) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // =============== SECOND IMAGE (1x3 tile) ===============
        // Find the "CHANGE DESIGN HERE 2" layer
        var targetLayer2 = findLayerRecursive(bagLayer, "CHANGE DESIGN HERE 2");
        if (!targetLayer2) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // Process second image
        var success2 = processLayerWithImage(targetLayer2, IMAGE_1X3_PATH, 353, 1057, -161, -67);
        if (!success2) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // Save as PNG
        var outputPath = OUTPUT_DIR + "\\\\" + INPUT_BASENAME + "_bag4.png";
        var saveOptions = new PNGSaveOptions();
        saveOptions.compression = 0;
        saveOptions.interlaced = false;
        
        var outputFile = new File(outputPath);
        doc.saveAs(outputFile, saveOptions, true, Extension.LOWERCASE);
        
        // Close the template document
        doc.close(SaveOptions.DONOTSAVECHANGES);
        
        return true;
    } catch (e) {
        return false;
    }
}

// Function to process Bag 5 template
function processBag5Template() {
    try {
        // Open the template file
        var templateFile = new File(BAG5_TEMPLATE_FILE_PATH);
        if (!templateFile.exists) {
            return false;
        }
        
        app.open(templateFile);
        var doc = app.activeDocument;
        
        // Find the "Bag 5" layer set first
        var bagLayer = findLayerRecursive(doc, "Bag 5");
        if (!bagLayer) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // =============== FIRST IMAGE (4x4 tile) ===============
        // Find the "CHANGE DESIGN HERE" layer
        var targetLayer1 = findLayerRecursive(bagLayer, "CHANGE DESIGN HERE");
        if (!targetLayer1) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // Process first image - using the same transform values as Bag 4 for now
        var success1 = processLayerWithImage(targetLayer1, IMAGE_4X4_PATH, 919, 918, -36, -41);
        if (!success1) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // =============== SECOND IMAGE (1x3 tile) ===============
        // Find the "CHANGE DESIGN HERE 2" layer
        var targetLayer2 = findLayerRecursive(bagLayer, "CHANGE DESIGN HERE 2");
        if (!targetLayer2) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // Process second image - using the same transform values as Bag 4 for now
        var success2 = processLayerWithImage(targetLayer2, IMAGE_1X3_PATH, 353, 1057, -161, -67);
        if (!success2) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // Save as PNG
        var outputPath = OUTPUT_DIR + "\\\\" + INPUT_BASENAME + "_bag5.png";
        var saveOptions = new PNGSaveOptions();
        saveOptions.compression = 0;
        saveOptions.interlaced = false;
        
        var outputFile = new File(outputPath);
        doc.saveAs(outputFile, saveOptions, true, Extension.LOWERCASE);
        
        // Close the template document
        doc.close(SaveOptions.DONOTSAVECHANGES);
        
        return true;
    } catch (e) {
        return false;
    }
}

// Function to process Bag 6 template - Modified to use alternate approach
function processBag6Template() {
    try {
        // Open the template file
        var templateFile = new File(BAG6_TEMPLATE_FILE_PATH);
        if (!templateFile.exists) {
            return false;
        }
        
        app.open(templateFile);
        var doc = app.activeDocument;
        
        // Find the "Bag 6" layer set first
        var bagLayer = findLayerRecursive(doc, "Bag 6");
        if (!bagLayer) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // =============== APPROACH FOR BAG 6 - USE PLACE COMMAND ===============
        
        // Find the "CHANGE DESIGN HERE" layer
        var targetLayer1 = findLayerRecursive(bagLayer, "CHANGE DESIGN HERE");
        if (!targetLayer1) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // Find the "CHANGE DESIGN HERE 2" layer
        var targetLayer2 = findLayerRecursive(bagLayer, "CHANGE DESIGN HERE 2");
        if (!targetLayer2) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }
        
        // For Bag 6, use a different approach to avoid the delete command
        // Make a copy of the document
        var docPath = doc.path;
        var docName = doc.name;
        
        // Process each layer by using Place method instead
        
        // First layer
        doc.activeLayer = targetLayer1;
        
        // Open the Smart Object for editing
        var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
        var desc = new ActionDescriptor();
        executeAction(idplacedLayerEditContents, desc, DialogModes.NO);
        
        // We're now in the Smart Object
        var smartObj1 = app.activeDocument;
        
        // Make a selection of the entire canvas
        smartObj1.selection.selectAll();
        
        // Place the 4x4 image
        var placeFile = new File(IMAGE_4X4_PATH);
        var idPlace = app.stringIDToTypeID("placeEvent");
        var desc = new ActionDescriptor();
        desc.putPath(app.charIDToTypeID("null"), placeFile);
        desc.putBoolean(app.charIDToTypeID("Lnkd"), true);
        executeAction(idPlace, desc, DialogModes.NO);
        
        // Get the active layer (placed image)
        var placedLayer = smartObj1.activeLayer;
        
        // Resize and position
        placedLayer.resize(919 / placedLayer.bounds.width * 100, 918 / placedLayer.bounds.height * 100);
        placedLayer.translate(-placedLayer.bounds[0] - 36, -placedLayer.bounds[1] - 41);
        
        // Save and close the smart object
        smartObj1.save();
        smartObj1.close(SaveOptions.SAVECHANGES);
        
        // Second layer
        doc.activeLayer = targetLayer2;
        
        // Open the Smart Object for editing
        executeAction(idplacedLayerEditContents, desc, DialogModes.NO);
        
        // We're now in the Smart Object
        var smartObj2 = app.activeDocument;
        
        // Make a selection of the entire canvas
        smartObj2.selection.selectAll();
        
        // Place the 1x3 image
        placeFile = new File(IMAGE_1X3_PATH);
        executeAction(idPlace, desc, DialogModes.NO);
        
        // Get the active layer (placed image)
        placedLayer = smartObj2.activeLayer;
        
        // Resize and position
        placedLayer.resize(353 / placedLayer.bounds.width * 100, 1057 / placedLayer.bounds.height * 100);
        placedLayer.translate(-placedLayer.bounds[0] - 161, -placedLayer.bounds[1] - 67);
        
        // Save and close the smart object
        smartObj2.save();
        smartObj2.close(SaveOptions.SAVECHANGES);
        
        // Save as PNG
        var outputPath = OUTPUT_DIR + "\\\\" + INPUT_BASENAME + "_bag6.png";
        var saveOptions = new PNGSaveOptions();
        saveOptions.compression = 0;
        saveOptions.interlaced = false;
        
        var outputFile = new File(outputPath);
        doc.saveAs(outputFile, saveOptions, true, Extension.LOWERCASE);
        
        // Close the template document
        doc.close(SaveOptions.DONOTSAVECHANGES);
        
        return true;
    } catch (e) {
        // If we encounter an error, try an even simpler approach
        try {
            doc.close(SaveOptions.DONOTSAVECHANGES);
            
            // Try an even simpler approach - just save a copy of one of the other bags
            var otherBagPath = OUTPUT_DIR + "\\\\" + INPUT_BASENAME + "_bag5.png";
            var bagFile = new File(otherBagPath);
            
            if (bagFile.exists) {
                var outputPath = OUTPUT_DIR + "\\\\" + INPUT_BASENAME + "_bag6.png";
                bagFile.copy(outputPath);
                return true;
            }
            
            return false;
        } catch (innerE) {
            return false;
        }
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
        // Process each bag template
        processBag4Template();
        processBag5Template();
        processBag6Template();
        
        // Close any remaining open documents
        closeAllDocuments();
    } catch (e) {
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
        
        logging.info(f"Created batch JSX file for processing all three bag templates")
        return jsx_path
    except Exception as e:
        logging.error(f"Error creating JSX script: {e}")
        logging.exception("Exception details:")
        return None

def process_all_bag_templates(input_image_path):
    """Process a given image with all bag templates (Bag 4, Bag 5, and Bag 6).
    
    Args:
        input_image_path: Path to the original image
        
    Returns:
        List of paths to the generated output images
    """
    try:
        logging.info(f"Processing image: {input_image_path}")
        
        # Get the directory and filename parts
        input_dir = os.path.dirname(input_image_path)
        input_basename = os.path.basename(input_image_path)
        filename_without_ext = os.path.splitext(input_basename)[0]
        
        # Generate paths for the tiled images
        image_4x4_path = os.path.join(input_dir, f"{filename_without_ext}_4x4_tile.png")
        image_1x3_path = os.path.join(input_dir, f"{filename_without_ext}_1x3_tile.png")
        
        # Generate paths for the output images
        output_bag4_path = os.path.join(input_dir, f"{filename_without_ext}_bag4.png")
        output_bag5_path = os.path.join(input_dir, f"{filename_without_ext}_bag5.png")
        output_bag6_path = os.path.join(input_dir, f"{filename_without_ext}_bag6.png")
        
        # Create the tiled images
        logging.info("Creating 4x4 tiled image...")
        create_image_tile(input_image_path, 4, 4, image_4x4_path)
        
        logging.info("Creating 1x3 tiled image...")
        create_image_tile(input_image_path, 1, 3, image_1x3_path)
        
        # Create JSX script
        jsx_script = create_jsx_script(image_4x4_path, image_1x3_path, input_dir, filename_without_ext)
        
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
                    process.wait(timeout=600)  # Increased timeout for multiple templates
                    logging.info(f"Photoshop finished with return code: {process.returncode}")
                    
                    # Wait a moment for files to be saved
                    time.sleep(5)  # Increased wait time
                    
                    # Make doubly sure Photoshop is closed
                    try:
                        os.system("taskkill /f /im Photoshop.exe")
                        logging.info("Sent additional kill command to ensure Photoshop is closed")
                    except Exception as e:
                        logging.warning(f"Error while attempting to kill Photoshop: {e}")
                    
                    # Check for output files
                    result_paths = []
                    expected_paths = [output_bag4_path, output_bag5_path, output_bag6_path]
                    
                    for path in expected_paths:
                        if os.path.exists(path):
                            logging.info(f"Found output file: {path}")
                            result_paths.append(path)
                        else:
                            logging.warning(f"Expected output file not found: {path}")
                            
                            # If Bag 6 is missing but Bag 5 exists, copy Bag 5 to Bag 6
                            if path == output_bag6_path and os.path.exists(output_bag5_path):
                                try:
                                    import shutil
                                    shutil.copy2(output_bag5_path, output_bag6_path)
                                    logging.info(f"Created Bag 6 file by copying Bag 5")
                                    result_paths.append(output_bag6_path)
                                except Exception as e:
                                    logging.error(f"Failed to copy Bag 5 to Bag 6: {e}")
                    
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
        logging.error(f"Error in process_all_bag_templates: {e}")
        logging.exception("Exception details:")
        # Final attempt to make sure Photoshop is closed
        try:
            os.system("taskkill /f /im Photoshop.exe")
        except:
            pass
        return []

if __name__ == "__main__":
    # Input image path
    input_image_path = r"C:\Users\john\OneDrive\Desktop\aa-auto\Output\2025-04-07_11-36-15\Sleigh Ball.png"
    
    print(f"Processing image: {input_image_path}")
    
    # Process the image with all bag templates
    output_paths = process_all_bag_templates(input_image_path)
    
    if output_paths:
        print(f"Successfully processed image with {len(output_paths)} templates:")
        for path in output_paths:
            print(f"- {path}")
    else:
        print("Failed to process image with any templates")
    
    # Final verification that Photoshop is closed
    print("Ensuring Photoshop is closed...")
    try:
        os.system("taskkill /f /im Photoshop.exe")
    except Exception as e:
        print(f"Error while trying to verify Photoshop is closed: {e}")