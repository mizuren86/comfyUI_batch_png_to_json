import os
import json
from PIL import Image

def extract_comfyui_metadata_to_json(input_dir, output_dir, replacements=None):
    """
    Batch extracts metadata (JSON) from ComfyUI-generated PNG/JPG images and saves them as JSON files.
    Optionally performs string replacements on the metadata before saving.

    Args:
        input_dir (str): Path to the directory containing ComfyUI PNG/JPG files (e.g., D:\comfyUI).
        output_dir (str): Path to the directory where the extracted JSON files will be saved.
        replacements (dict, optional): A dictionary where keys are old strings to be replaced
                                      and values are new strings to replace them with.
                                      E.g., {"old_string": "new_string"}. Defaults to None.
    """

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    for filename in os.listdir(input_dir):
        # Process both .png and .jpg files
        if filename.lower().endswith(".png") or filename.lower().endswith(".jpg"):
            file_path = os.path.join(input_dir, filename)
            try:
                with Image.open(file_path) as img:
                    metadata_key_found = None
                    metadata_json_str = None

                    # Prioritize 'prompt' as it's the most common for full workflow JSON in ComfyUI
                    if "prompt" in img.info:
                        metadata_json_str = img.info["prompt"]
                        metadata_key_found = "prompt"
                    # Fallback to 'workflow' if 'prompt' is not found (some versions/setups might use this)
                    elif "workflow" in img.info:
                        metadata_json_str = img.info["workflow"]
                        metadata_key_found = "workflow"
                    # Fallback to 'parameters' (less common for full workflow JSON, but might contain some info)
                    elif "parameters" in img.info:
                        metadata_json_str = img.info["parameters"]
                        metadata_key_found = "parameters"
                    
                    if metadata_json_str:
                        try:
                            # Attempt to parse the extracted string as a JSON object
                            metadata_json_obj = json.loads(metadata_json_str)

                            # --- New string replacement functionality ---
                            if replacements:
                                modified_count = 0
                                # Convert the entire JSON object back to a string for replacement
                                # We assume the replacement primarily targets text within the 'prompt' field
                                # ComfyUI's metadata usually stores the entire workflow as a large JSON string
                                # under the 'prompt' key, so we operate directly on this string.
                                # For precise replacement of values within specific JSON keys, more complex
                                # recursive traversal would be needed.
                                
                                temp_json_str = json.dumps(metadata_json_obj, ensure_ascii=False)
                                
                                for old_str, new_str in replacements.items():
                                    if old_str in temp_json_str:
                                        temp_json_str = temp_json_str.replace(old_str, new_str)
                                        modified_count += 1
                                
                                # Parse the modified string back into a JSON object
                                if modified_count > 0:
                                    metadata_json_obj = json.loads(temp_json_str)
                                    print(f"  Performed {modified_count} string replacements in {filename}.")
                            # --- End of string replacement functionality ---

                            # Construct the output JSON filename
                            json_filename = os.path.splitext(filename)[0] + ".json"
                            output_json_path = os.path.join(output_dir, json_filename)

                            with open(output_json_path, 'w', encoding='utf-8') as f:
                                json.dump(metadata_json_obj, f, indent=4, ensure_ascii=False)
                            print(f"Successfully extracted and saved metadata from key '{metadata_key_found}' to {json_filename}")

                        except json.JSONDecodeError:
                            # If the string isn't valid JSON, print a warning and part of the string for debugging
                            print(f"Warning: Metadata from key '{metadata_key_found}' in {filename} could not be parsed as valid JSON. Raw string (first 200 chars): {metadata_json_str[:200]}...")
                    else:
                        # If no known metadata key is found, print a warning and list all available keys
                        print(f"Warning: No ComfyUI workflow metadata key (prompt, workflow, or parameters) found in {filename}. Available keys: {list(img.info.keys())}")
            except Exception as e:
                print(f"An error occurred while processing {filename}: {e}")

# Set input and output directories
input_directory = r"D:\comfyUI"  # Use raw string to avoid backslash escape issues
output_directory = r"D:\comfyUI" # Ensure the path is correct

# Define your string replacement rules
# Key is the old string to be replaced, value is the new string
string_replacements = {
    "toki (blue archive), blue archive": "rio (blue archive), blue archive",
    # Add more replacement rules here if needed
    # "old_string_2": "new_string_2",
    # "another_prompt_part": "new_prompt_part"
}


if __name__ == "__main__":
    extract_comfyui_metadata_to_json(input_directory, output_directory, replacements=string_replacements)
    print("\nBatch extraction and modification complete!")
