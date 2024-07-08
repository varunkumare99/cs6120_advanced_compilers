#script to run bench marking
import os
import subprocess
import argparse

def process_files(directory):
    # Iterate over all files in the given directory
    for filename in os.listdir(directory):
        if filename.endswith(".bril"):
            base_filename = filename[:-5]
            bril_file = os.path.join(directory, f"{base_filename}.bril")
            my_out_file = os.path.join(directory, f"{base_filename}.my_out")

            if os.path.exists(my_out_file):
                # Construct the commands based on special cases
                if base_filename == "fold-comparisons":
                    command_bril = f"bril2json < {bril_file} | brili -p 1 2"
                    command_my_out = f"bril2json < {my_out_file} | brili -p 1 2"
                elif base_filename == "logical-operators":
                    command_bril = f"bril2json < {bril_file} | brili -p true false"
                    command_my_out = f"bril2json < {my_out_file} | brili -p true false"
                else:
                    command_bril = f"bril2json < {bril_file} | brili -p"
                    command_my_out = f"bril2json < {my_out_file} | brili -p"

                # Run the commands and capture the outputs
                try:
                    result_bril = subprocess.run(command_bril, shell=True, capture_output=True, text=True, check=True)
                    result_my_out = subprocess.run(command_my_out, shell=True, capture_output=True, text=True, check=True)

                    # Print the results
                    print("******************************")
                    print(f"Results for {bril_file}:")
                    print(result_bril.stdout)
                    print(result_bril.stderr)
                    print(f"Results for {my_out_file}:")
                    print(result_my_out.stdout)
                    print(result_my_out.stderr)
                except subprocess.CalledProcessError as e:
                    print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process .bril and .my_out files in a directory.")
    parser.add_argument("directory", type=str, help="The directory containing the files")
    args = parser.parse_args()
    
    process_files(args.directory)

