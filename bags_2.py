from PIL import Image
import os
import time
import subprocess
import json
import csv
import requests
from pathlib import Path
import logging
import datetime
import traceback
from config import BASE_FOLDER, OUTPUT_BASE_FOLDER, BAGS_FOLDER

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / "Downloads" / "bags_log.txt"),
        logging.StreamHandler()
    ]
)

def create_tiled_image(original_img, tile_size):
    """Create a tiled image with specified tile size (e.g., 3x3 or 6x6)"""
    try:
        # Get the dimensions of the original image
        width, height = original_img.size
        
        # Create a new image that is tile_size times as large in both dimensions
        tiled_img = Image.new(original_img.mode, (width * tile_size, height * tile_size))
        
        # Paste the original image into a tile_size x tile_size grid
        for i in range(tile_size):
            for j in range(tile_size):
                tiled_img.paste(original_img, (i * width, j * height))
        
        return tiled_img
    except Exception as e:
        logging.error(f"Error creating tiled image: {e}")
        logging.exception("Exception details:")
        return None

def download_image(url, save_path, max_retries=3):
    """Download an image from a URL and save it to the specified path with retry logic"""
    for attempt in range(max_retries):
        try:
            logging.info(f"Downloading image from {url} (attempt {attempt+1}/{max_retries})")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify the file exists and is a valid image
            try:
                with Image.open(save_path) as img:
                    # Just accessing img.format will validate it's an image
                    logging.info(f"Downloaded valid image: {save_path}, format: {img.format}")
                return True
            except Exception as e:
                logging.error(f"Downloaded file is not a valid image: {e}")
                if os.path.exists(save_path):
                    os.remove(save_path)
                raise ValueError("Downloaded file is not a valid image")
                
        except Exception as e:
            logging.error(f"Error downloading image from {url} (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logging.info(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                logging.error(f"Failed to download after {max_retries} attempts")
                return False
    
    return False

def process_single_image(file_path, output_dir, max_retries=2):
    """Process a single image: create 3x3 and 6x6 tiled versions with retry logic"""
    for attempt in range(max_retries):
        try:
            file_path = Path(file_path)
            
            # Check if file exists
            if not file_path.exists():
                error_msg = f"Error: Image file not found at {file_path}"
                logging.error(error_msg)
                print(error_msg)
                return None, None
            
            logging.info(f"Processing image: {file_path} (attempt {attempt+1}/{max_retries})")
                
            # Open the original image
            logging.info("Opening original image...")
            original_img = Image.open(file_path)
            logging.info(f"Original image size: {original_img.size}, mode: {original_img.mode}")
            
            # Get the original filename without extension
            original_filename = file_path.name
            filename_without_ext = file_path.stem
            file_extension = file_path.suffix
            
            # Create 3x3 tiled image
            logging.info("Creating 3x3 tiled image...")
            tiled_img_3x3 = create_tiled_image(original_img, 3)
            if not tiled_img_3x3:
                raise Exception("Failed to create 3x3 tiled image")
            
            # Create 6x6 tiled image
            logging.info("Creating 6x6 tiled image...")
            tiled_img_6x6 = create_tiled_image(original_img, 6)
            if not tiled_img_6x6:
                raise Exception("Failed to create 6x6 tiled image")
            
            # Create filenames - without the 3x3 and 6x6 in the names
            tiled_3x3_filename = f"{filename_without_ext}_tiled{file_extension}"
            tiled_6x6_filename = f"{filename_without_ext}_tiled2{file_extension}"
            
            # Create full save paths
            save_path_3x3 = output_dir / tiled_3x3_filename
            save_path_6x6 = output_dir / tiled_6x6_filename
            
            # Save the tiled images
            logging.info(f"Saving tiled image for Bag 1 and Bag 3 to: {save_path_3x3}")
            tiled_img_3x3.save(save_path_3x3)
            
            logging.info(f"Saving tiled image for Bag 2 to: {save_path_6x6}")
            tiled_img_6x6.save(save_path_6x6)
            
            logging.info("Tiled images saved successfully")
            
            # Verify the files exist
            if os.path.exists(save_path_3x3) and os.path.exists(save_path_6x6):
                return str(save_path_3x3), str(save_path_6x6)
            else:
                raise FileNotFoundError("Saved files not found on disk")
            
        except Exception as e:
            error_msg = f"Error processing image {file_path} (attempt {attempt+1}): {e}"
            logging.error(error_msg)
            logging.exception("Exception details:")
            
            if attempt < max_retries - 1:
                logging.info(f"Retrying image processing... (attempt {attempt+2})")
                time.sleep(2)  # Wait before retrying
            else:
                logging.error(f"Failed to process image after {max_retries} attempts")
                print(error_msg)
        
    return None, None

def create_jsx_script(image_data, main_output_dir, timestamp):
    """Create a JSX script that processes images with Bag 1, Bag 2, and Bag 3 templates"""
    try:
        # Create a JSX script that can be directly run by Photoshop
        jsx_path = main_output_dir / f"Batch_Bags_{timestamp}.jsx"
        logging.info(f"Creating batch JSX file at: {jsx_path}")
        
        # Extract all paths for templates
        bag1_paths = [item['tiled_3x3_path'] for item in image_data if 'tiled_3x3_path' in item and item['tiled_3x3_path'] is not None]
        bag2_paths = [item['tiled_6x6_path'] for item in image_data if 'tiled_6x6_path' in item and item['tiled_6x6_path'] is not None]
        # Bag 3 uses the same 3x3 tiled images as Bag 1
        bag3_paths = bag1_paths
        
        # Validate we have valid paths
        if not bag1_paths:
            logging.error("No valid tiled_3x3_path found in image_data")
            return None
            
        if not bag2_paths:
            logging.error("No valid tiled_6x6_path found in image_data")
            return None
        
        # Create the JSX content 
        jsx_content = f'''// Bag Templates Image Processor (Batch Version)
// Generated by Bags_1.py on {time.ctime()}

// File paths configuration
var BAG1_IMAGE_PATHS = [
{", ".join([f'    "{path.replace("\\", "\\\\")}"' for path in bag1_paths])}
];

var BAG2_IMAGE_PATHS = [
{", ".join([f'    "{path.replace("\\", "\\\\")}"' for path in bag2_paths])}
];

var BAG3_IMAGE_PATHS = [
{", ".join([f'    "{path.replace("\\", "\\\\")}"' for path in bag3_paths])}
];

var BAG1_TEMPLATE_FILE_PATH = "C:\\\\Users\\\\john\\\\OneDrive\\\\Desktop\\\\aa-auto\\\\Bags & Tissues\\\\Bag 1.psd"; 
var BAG2_TEMPLATE_FILE_PATH = "C:\\\\Users\\\\john\\\\OneDrive\\\\Desktop\\\\aa-auto\\\\Bags & Tissues\\\\Bag 2.psd";
var BAG3_TEMPLATE_FILE_PATH = "C:\\\\Users\\\\john\\\\OneDrive\\\\Desktop\\\\aa-auto\\\\Bags & Tissues\\\\Bag 3.psd";

// Function to get filename without extension and path
function getFileNameWithoutExtension(filePath) {{
    var fileName = filePath.split("\\\\").pop();
    return fileName.substring(0, fileName.lastIndexOf("."));
}}

// Function to get directory part of a file path
function getDirectoryPath(filePath) {{
    var lastBackslash = filePath.lastIndexOf("\\\\");
    return filePath.substring(0, lastBackslash);
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

// Function to process an image with Bag 1 template
function processBag1Image(imagePath) {{
    try {{
        // Open the template file
        var templateFile = new File(BAG1_TEMPLATE_FILE_PATH);
        if (!templateFile.exists) {{
            return false;
        }}
        
        app.open(templateFile);
        var doc = app.activeDocument;
        
        // Find the "CHANGE DESIGN HERE" layer using recursive search
        var targetLayer = findLayerRecursive(doc, "CHANGE DESIGN HERE");
        
        if (!targetLayer) {{
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }}
        
        // Store the original visibility state
        var originalVisibility = targetLayer.visible;
        
        // Make sure the layer is visible for editing
        targetLayer.visible = true;
        
        // Activate the target layer and edit its contents
        doc.activeLayer = targetLayer;
        
        // Open the Smart Object
        var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
        var desc = new ActionDescriptor();
        executeAction(idplacedLayerEditContents, desc, DialogModes.NO);
        
        // We are now inside the Smart Object
        var smartObjectDoc = app.activeDocument;
        
        // Check if the image exists
        var imageFile = new File(imagePath);
        if (!imageFile.exists) {{
            smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES);
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }}
        
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
        while (smartObjectDoc.artLayers.length > 1) {{
            smartObjectDoc.artLayers[0].remove();
        }}
        
        // Paste the copied image
        smartObjectDoc.paste();
        
        // Get the active layer (pasted image)
        var currentLayer = smartObjectDoc.activeLayer;
        
        // Calculate current dimensions
        var width = currentLayer.bounds[2] - currentLayer.bounds[0];
        var height = currentLayer.bounds[3] - currentLayer.bounds[1];
        
        // Get target dimensions from screenshot
        var targetWidth = 1554;
        var targetHeight = 1440;
        
        // Calculate scale factors
        var widthRatio = targetWidth / width * 100;
        var heightRatio = targetHeight / height * 100;
        
        // Resize the layer
        currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
        
        // Position the layer at exact X and Y coordinates from screenshot
        // The values are -187 for X and -583 for Y
        currentLayer.translate(-currentLayer.bounds[0] - 187, -currentLayer.bounds[1] - 583);
        
        // Save and close the Smart Object
        smartObjectDoc.save();
        smartObjectDoc.close(SaveOptions.SAVECHANGES);
        
        // Restore the original visibility state
        targetLayer.visible = originalVisibility;
        
        // Generate output filename
        var outputBaseName = getFileNameWithoutExtension(imagePath);
        var outputFilePath = getDirectoryPath(imagePath) + "\\\\" + outputBaseName + "_bag.png";
        
        // Save as PNG
        var saveOptions = new PNGSaveOptions();
        saveOptions.compression = 0; // 0-9, where 0 is no compression
        saveOptions.interlaced = false;
        
        var outputFile = new File(outputFilePath);
        doc.saveAs(outputFile, saveOptions, true, Extension.LOWERCASE);
        
        // Close the template document
        doc.close(SaveOptions.DONOTSAVECHANGES);
        
        return true;
    }} catch (e) {{
        return false;
    }}
}}

// Function to process an image with Bag 2 template
function processBag2Image(imagePath) {{
    try {{
        // Open the template file
        var templateFile = new File(BAG2_TEMPLATE_FILE_PATH);
        if (!templateFile.exists) {{
            return false;
        }}
        
        app.open(templateFile);
        var doc = app.activeDocument;
        
        // Find the "Bag 2" layer set first
        var bag2Layer = findLayerRecursive(doc, "Bag 2");
        if (!bag2Layer) {{
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }}
        
        // Then find the "CHANGE DESIGN HERE" layer within the Bag 2 layer set
        var targetLayer = findLayerRecursive(bag2Layer, "CHANGE DESIGN HERE");
        if (!targetLayer) {{
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }}
        
        // Store the original visibility state
        var originalVisibility = targetLayer.visible;
        
        // Make sure the layer is visible for editing
        targetLayer.visible = true;
        
        // Activate the target layer and edit its contents
        doc.activeLayer = targetLayer;
        
        // Open the Smart Object
        var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
        var desc = new ActionDescriptor();
        executeAction(idplacedLayerEditContents, desc, DialogModes.NO);
        
        // We are now inside the Smart Object
        var smartObjectDoc = app.activeDocument;
        
        // Check if the image exists
        var imageFile = new File(imagePath);
        if (!imageFile.exists) {{
            smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES);
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }}
        
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
        while (smartObjectDoc.artLayers.length > 1) {{
            smartObjectDoc.artLayers[0].remove();
        }}
        
        // Paste the copied image
        smartObjectDoc.paste();
        
        // Get the active layer (pasted image)
        var currentLayer = smartObjectDoc.activeLayer;
        
        // Calculate current dimensions
        var width = currentLayer.bounds[2] - currentLayer.bounds[0];
        var height = currentLayer.bounds[3] - currentLayer.bounds[1];
        
        // Get target dimensions from screenshot
        var targetWidth = 1897;  // As seen in the Transform panel
        var targetHeight = 1897; // As seen in the Transform panel
        
        // Calculate scale factors
        var widthRatio = targetWidth / width * 100;
        var heightRatio = targetHeight / height * 100;
        
        // Resize the layer
        currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
        
        // Position the layer at exact X and Y coordinates from screenshot
        // The values are -151 for X and -391 for Y as shown in Transform panel
        currentLayer.translate(-currentLayer.bounds[0] - 151, -currentLayer.bounds[1] - 391);
        
        // Save and close the Smart Object
        smartObjectDoc.save();
        smartObjectDoc.close(SaveOptions.SAVECHANGES);
        
        // Restore the original visibility state
        targetLayer.visible = originalVisibility;
        
        // Generate output filename
        var outputBaseName = getFileNameWithoutExtension(imagePath);
        var outputFilePath = getDirectoryPath(imagePath) + "\\\\" + outputBaseName + "_bag2.png";
        
        // Save as PNG
        var saveOptions = new PNGSaveOptions();
        saveOptions.compression = 0; // 0-9, where 0 is no compression
        saveOptions.interlaced = false;
        
        var outputFile = new File(outputFilePath);
        doc.saveAs(outputFile, saveOptions, true, Extension.LOWERCASE);
        
        // Close the template document
        doc.close(SaveOptions.DONOTSAVECHANGES);
        
        return true;
    }} catch (e) {{
        return false;
    }}
}}

// Function to process an image with Bag 3 template
function processBag3Image(imagePath) {{
    try {{
        // Open the template file
        var templateFile = new File(BAG3_TEMPLATE_FILE_PATH);
        if (!templateFile.exists) {{
            return false;
        }}
        
        app.open(templateFile);
        var doc = app.activeDocument;
        
        // Find the "Bag 3" layer set
        var bag3Layer = findLayerRecursive(doc, "Bag 3");
        if (!bag3Layer) {{
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }}
        
        // Find the "CHANGE DESIGN" layer (note: no "HERE" in the name)
        var targetLayer = findLayerRecursive(bag3Layer, "CHANGE DESIGN");
        if (!targetLayer) {{
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }}
        
        // Hide the "midsummer-grovepainted-paper-524010 copia" layer
        var paperLayer = findLayerRecursive(doc, "midsummer-grovepainted-paper-524010 copia");
        if (paperLayer) {{
            paperLayer.visible = false;
        }}
        
        // Store the original visibility state of target layer
        var originalVisibility = targetLayer.visible;
        
        // Make sure the layer is visible for editing
        targetLayer.visible = true;
        
        // Activate the target layer and edit its contents
        doc.activeLayer = targetLayer;
        
        // Open the Smart Object
        var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
        var desc = new ActionDescriptor();
        executeAction(idplacedLayerEditContents, desc, DialogModes.NO);
        
        // We are now inside the Smart Object
        var smartObjectDoc = app.activeDocument;
        
        // Check if the image exists
        var imageFile = new File(imagePath);
        if (!imageFile.exists) {{
            smartObjectDoc.close(SaveOptions.DONOTSAVECHANGES);
            doc.close(SaveOptions.DONOTSAVECHANGES);
            return false;
        }}
        
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
        while (smartObjectDoc.artLayers.length > 1) {{
            smartObjectDoc.artLayers[0].remove();
        }}
        
        // Paste the copied image
        smartObjectDoc.paste();
        
        // Get the active layer (pasted image)
        var currentLayer = smartObjectDoc.activeLayer;
        
        // Calculate current dimensions
        var width = currentLayer.bounds[2] - currentLayer.bounds[0];
        var height = currentLayer.bounds[3] - currentLayer.bounds[1];
        
        // Get target dimensions from the screenshot
        var targetWidth = 1250;  // As seen in the Transform panel
        var targetHeight = 1250; // As seen in the Transform panel
        
        // Calculate scale factors
        var widthRatio = targetWidth / width * 100;
        var heightRatio = targetHeight / height * 100;
        
        // Resize the layer
        currentLayer.resize(widthRatio, heightRatio, AnchorPosition.TOPLEFT);
        
        // Position the layer at X and Y coordinates from the screenshot
        // The values are -128 for X and -481 for Y as shown in Transform panel
        currentLayer.translate(-currentLayer.bounds[0] - 128, -currentLayer.bounds[1] - 481);
        
        // Save and close the Smart Object
        smartObjectDoc.save();
        smartObjectDoc.close(SaveOptions.SAVECHANGES);
        
        // Restore the original visibility state
        targetLayer.visible = originalVisibility;
        
        // Generate output filename
        var outputBaseName = getFileNameWithoutExtension(imagePath);
        var outputFilePath = getDirectoryPath(imagePath) + "\\\\" + outputBaseName + "_bag3.png";
        
        // Save as PNG
        var saveOptions = new PNGSaveOptions();
        saveOptions.compression = 0; // 0-9, where 0 is no compression
        saveOptions.interlaced = false;
        
        var outputFile = new File(outputFilePath);
        doc.saveAs(outputFile, saveOptions, true, Extension.LOWERCASE);
        
        // Close the template document
        doc.close(SaveOptions.DONOTSAVECHANGES);
        
        return true;
    }} catch (e) {{
        return false;
    }}
}}

// Function to safely close all open documents
function closeAllDocuments() {{
    try {{
        while (app.documents.length) {{
            app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
        }}
    }} catch (e) {{
        // Silently ignore any errors during document closing
    }}
}}

// Main execution
function main() {{
    try {{
        // Process images with Bag 1 template
        for (var i = 0; i < BAG1_IMAGE_PATHS.length; i++) {{
            var imagePath = BAG1_IMAGE_PATHS[i];
            processBag1Image(imagePath);
            
            // Close any remaining open documents
            closeAllDocuments();
        }}
        
        // Process images with Bag 2 template
        for (var i = 0; i < BAG2_IMAGE_PATHS.length; i++) {{
            var imagePath = BAG2_IMAGE_PATHS[i];
            processBag2Image(imagePath);
            
            // Close any remaining open documents
            closeAllDocuments();
        }}
        
        // Process images with Bag 3 template
        for (var i = 0; i < BAG3_IMAGE_PATHS.length; i++) {{
            var imagePath = BAG3_IMAGE_PATHS[i];
            processBag3Image(imagePath);
            
            // Close any remaining open documents
            closeAllDocuments();
        }}
    }} catch (e) {{
        // Silent error handling
        closeAllDocuments();
    }}
}}

// Run the script
main();
'''
        
        # Write the JSX content to file
        with open(jsx_path, 'w', encoding='utf-8') as f:
            f.write(jsx_content)
        
        logging.info(f"Created batch JSX file with {len(bag1_paths)} Bag 1 images, {len(bag2_paths)} Bag 2 images, and {len(bag3_paths)} Bag 3 images")
        return jsx_path
    except Exception as e:
        logging.error(f"Error creating JSX script: {e}")
        logging.exception("Exception details:")
        return None

def process_all_bag_templates(input_image_path):
    """Process an image with all bag templates."""
    # ... existing code ...

if __name__ == "__main__":
    # Input image path
    input_image_path = os.path.join(OUTPUT_BASE_FOLDER, "2025-04-07_11-36-15/Sleigh Ball.png")
    
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
