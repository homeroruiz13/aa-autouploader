from PIL import Image
import os

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
    except Exception as e:
        print(f"Error opening image: {e}")
        return
    
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
    print(f"Created tiled image: {output_filename}")

def main():
    # Get the directory of the input image
    input_image_path = r"C:\Users\john\OneDrive\Desktop\aa-auto\Output\2025-04-07_11-36-15\Sleigh Ball.png"
    directory = os.path.dirname(input_image_path)
    
    # Create output filenames
    filename_4x4 = os.path.join(directory, "Sleigh_Ball_4x4_tile.png")
    filename_1x3 = os.path.join(directory, "Sleigh_Ball_1x3_tile.png")
    
    # Create the 4x4 tiled image
    create_image_tile(input_image_path, 4, 4, filename_4x4)
    
    # Create the 1x3 tiled image
    create_image_tile(input_image_path, 1, 3, filename_1x3)
    
    print("All tiling operations completed!")

if __name__ == "__main__":
    main()