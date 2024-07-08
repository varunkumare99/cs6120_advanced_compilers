#script to lvn on all input tests and save output with same file anme with my_out ext
import os
import subprocess
import argparse

def process_bril_files(directory):
    # Iterate over all files in the given directory
    for filename in os.listdir(directory):
        if filename.endswith(".bril"):
            input_file = os.path.join(directory, filename)
            output_file = os.path.join(directory, filename.replace(".bril", ".my_out"))
            
            # Construct the command
            command = f"bril2json < {input_file} | python3 lvn.py | bril2txt"
            
            # Run the command and capture the output
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
                # Write the output to the output file
                with open(output_file, 'w') as f:
                    f.write(result.stdout)
                print(f"Processed {input_file} successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Error processing {input_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process .bril files in a directory.")
    parser.add_argument("directory", type=str, help="The directory containing .bril files")
    args = parser.parse_args()
    
    process_bril_files(args.directory)

