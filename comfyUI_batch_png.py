import json
import os
import zlib
from PIL import Image
import time # 確保有導入 time 模組

# --- Configuration Parameters ---
PNG_DIR = "D:\\comfyUI" # Directory containing PNG files
OUTPUT_DIR = "D:\\comfyUI" # Output directory for modified PNG files

# Keywords to replace
OLD_TEXT = "toki (blue archive)"
NEW_TEXT = "rio (blue archive)"

# --- Helper Functions ---
def find_and_replace_in_json(obj, old_str, new_str):
    """Recursively finds and replaces strings within a JSON object."""
    if isinstance(obj, dict):
        return {k: find_and_replace_in_json(v, old_str, new_str) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [find_and_replace_in_json(elem, old_str, new_str) for elem in obj]
    elif isinstance(obj, str):
        return obj.replace(old_str, new_str)
    else:
        return obj

def process_png_file(filepath):
    """
    Reads a PNG file, attempts to find and modify its ComfyUI workflow JSON in metadata,
    and saves a new file if successful.
    """
    filename = os.path.basename(filepath)
    print(f"\n--- Processing file: {filename} ---")
    
    try:
        img = Image.open(filepath)
        
        # # --- dubug info ---
        # print(f"--- img.info for {filename} ---")
        # if img.info:
        #     for key, value in img.info.items():
        #         print(f"Key: {key}")
        #         if isinstance(value, bytes):
        #             print(f"  Value (bytes, length {len(value)}): {value[:100]}...")
        #         elif isinstance(value, str):
        #             print(f"  Value (string, length {len(value)}): {value[:500]}...")
        #         else:
        #             print(f"  Value: {value}")
                
        #         if key in ["parameters", "workflow", "prompt"]:
        #             try:
        #                 if isinstance(value, bytes):
        #                     decompressed_value = zlib.decompress(value).decode('utf-8')
        #                     print(f"  --- Decompressed '{key}' (first 500 chars): {decompressed_value[:500]}...")
        #                     json_data = json.loads(decompressed_value)
        #                 else:
        #                     json_data = json.loads(value)
        #                 print(f"  --- Parsed JSON from '{key}':")
        #                 # print(json.dumps(json_data, indent=2, ensure_ascii=False)) # 避免輸出過多
        #             except json.JSONDecodeError:
        #                 print(f"  --- ERROR: '{key}' content is NOT valid JSON.")
        #             except zlib.error as ze:
        #                 print(f"  --- ERROR: Zlib decompression failed for '{key}': {ze}")
        #             except Exception as ee:
        #                 print(f"  --- ERROR: Unexpected error parsing '{key}': {ee}")
        #     if not img.info:
        #         print("  No info dictionary found.")
        # print(f"--- End img.info for {filename} ---\n")
        # # --- dubug info end ---

        metadata_found = False
        workflow_json_str = None
        workflow_data = None # This will hold the parsed JSON object
        json_key_to_update = None # Track which key to update when saving

        # 核心修改點: 優先檢查 'prompt'，然後是 'workflow'，最後是其他文本塊
        
        # Priority 1: Check for 'prompt' key
        if "prompt" in img.info:
            try:
                workflow_json_str = img.info["prompt"]
                workflow_data = json.loads(workflow_json_str)
                metadata_found = True
                json_key_to_update = "prompt"
                print(f"Found ComfyUI workflow JSON in 'prompt' for {filename}.")
            except json.JSONDecodeError:
                print(f"Warning: 'prompt' chunk in {filename} is not a valid JSON string.")
            except Exception as e:
                print(f"An unexpected error occurred while processing 'prompt' chunk in {filename}: {e}")

        # Priority 2: If not found in 'prompt', check for 'workflow' key
        if not metadata_found and "workflow" in img.info:
            try:
                workflow_json_str = img.info["workflow"]
                workflow_data = json.loads(workflow_json_str)
                metadata_found = True
                json_key_to_update = "workflow" # We will save back to 'workflow' if found here
                print(f"Found ComfyUI workflow JSON in 'workflow' for {filename}.")
            except json.JSONDecodeError:
                print(f"Warning: 'workflow' chunk in {filename} is not a valid JSON string.")
            except Exception as e:
                print(f"An unexpected error occurred while processing 'workflow' chunk in {filename}: {e}")

        # Priority 3: Fallback to tEXt or zTXt if still not found
        if not metadata_found:
            for key, value in img.info.items():
                if key in ["tEXt", "zTXt"]: # You can add 'parameters' here if you expect it in some cases
                    try:
                        if key == "tEXt":
                            workflow_json_str = value
                        elif key == "zTXt":
                            workflow_json_str = zlib.decompress(value).decode('utf-8')
                        
                        temp_json = json.loads(workflow_json_str)
                        
                        # ComfyUI's workflow JSON can be under a "prompt" key or be the entire workflow structure
                        if "prompt" in temp_json:
                            workflow_data = temp_json["prompt"]
                            metadata_found = True
                            json_key_to_update = key # Save back to original text chunk type
                            print(f"Found workflow JSON under '{key}' and 'prompt' for {filename}.")
                            break
                        elif isinstance(temp_json, dict) and any(isinstance(v, dict) and "class_type" in v for v in temp_json.values()):
                            workflow_data = temp_json
                            metadata_found = True
                            json_key_to_update = key # Save back to original text chunk type
                            print(f"Found direct workflow JSON under '{key}' for {filename}.")
                            break
                        else:
                            print(f"Warning: Found a '{key}' chunk in {filename} but it doesn't appear to be a ComfyUI workflow JSON structure.")
                            workflow_json_str = None

                    except json.JSONDecodeError:
                        print(f"Warning: Found a '{key}' chunk in {filename}, but its content is not a valid JSON string.")
                        workflow_json_str = None
                    except zlib.error as ze:
                        print(f"Warning: Found a 'zTXt' chunk in {filename}, but failed to decompress its content: {ze}")
                        workflow_json_str = None
                    except Exception as ee:
                        print(f"An unexpected error occurred while processing '{key}' chunk in {filename}: {ee}")
                        workflow_json_str = None

        if not metadata_found or workflow_data is None:
            print(f"Error: ComfyUI workflow JSON cannot be found or parsed for {filename}.")
            return # Skip to next file
        
        # At this point, workflow_data should contain the parsed JSON structure
        # Now, check if the old text exists in the JSON data
        original_workflow_str = json.dumps(workflow_data, ensure_ascii=False) # Convert back to string for checking
        if OLD_TEXT not in original_workflow_str:
            print(f"Info: '{OLD_TEXT}' not found in the workflow JSON for {filename}. Skipping replacement.")
            return # Skip to next file

        # Perform the replacement
        modified_workflow_data = find_and_replace_in_json(workflow_data, OLD_TEXT, NEW_TEXT)
        
        # Convert the final JSON to a string to be saved back
        final_metadata_str = json.dumps(modified_workflow_data, ensure_ascii=False)

        # Create a new Image object from the old one to preserve other data
        new_img = img.copy()

        # Update the metadata using the key where it was originally found
        if json_key_to_update:
            new_img.info[json_key_to_update] = final_metadata_str
            print(f"Updated '{json_key_to_update}' key with modified JSON.")
        else:
            # Fallback if for some reason the key wasn't tracked (shouldn't happen with current logic)
            new_img.info["prompt"] = final_metadata_str # Default to 'prompt' if unsure
            print(f"Warning: JSON key to update not tracked. Defaulting to update 'prompt'.")

        # (Optional) You can also update or add a generic tEXt chunk if you want,
        # but the specific keys ('prompt', 'workflow', or original tEXt/zTXt) are what ComfyUI expects.
        # new_img.info["ComfyUI_workflow_modified"] = final_metadata_str 

        # Generate a unique filename for the new image
        original_name_without_ext = os.path.splitext(filename)[0]
        timestamp = int(time.time()) # Correct usage for time.time()
        new_filename = f"{original_name_without_ext}_modified_{timestamp}.png"
        new_filepath = os.path.join(OUTPUT_DIR, new_filename)

        # Save the new image with updated metadata
        new_img.save(new_filepath)
        print(f"Successfully modified and saved to: {new_filepath}")

    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
    except Exception as e:
        print(f"An unexpected error occurred while processing {filename}: {e}")

# --- Main Execution Logic ---
def main():
    print(f"--- Starting PNG Metadata Modifier ---")
    print(f"Looking for PNGs in: {PNG_DIR}")
    print(f"Replacing '{OLD_TEXT}' with '{NEW_TEXT}' in metadata JSON.")

    if not os.path.exists(PNG_DIR):
        print(f"Error: Source directory '{PNG_DIR}' does not exist.")
        return
    if not os.path.exists(OUTPUT_DIR):
        print(f"Creating output directory: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR)

    png_files = [f for f in os.listdir(PNG_DIR) if f.lower().endswith('.png')]

    if not png_files:
        print(f"No PNG files found in '{PNG_DIR}'.")
        return

    for png_file in png_files:
        filepath = os.path.join(PNG_DIR, png_file)
        process_png_file(filepath)

    print("\n--- PNG Metadata Modification Completed ---")

if __name__ == "__main__":
    main()