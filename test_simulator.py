import sys
import subprocess
import difflib
import os

def run_test(input_file, expected_file, output_file, cmd):
    """
    Runs the simulator on a single test input file using the provided command,
    writes the output to output_file, and compares it with expected_file.
    """
    full_cmd = cmd + [input_file, output_file]
    result = subprocess.run(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"Error running simulator on {input_file}:")
        print(result.stderr.decode())
        return False

    with open(expected_file, 'r') as f:
        expected_lines = f.readlines()
    with open(output_file, 'r') as f:
        output_lines = f.readlines()

    diff = list(difflib.unified_diff(expected_lines, output_lines,
                                     fromfile='expected', tofile='output', lineterm=''))
    if diff:
        print(f"Test FAILED for {input_file}.")
        return False
    else:
        print(f"Test PASSED for {input_file}.")
        return True

def run_tests_in_directory(input_dir, expected_dir, output_dir, cmd):
    """
    Iterates over each file in the input directory and runs a test.
    The expected and output directories should have matching filenames.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    test_files = sorted([f for f in os.listdir(input_dir)
                         if os.path.isfile(os.path.join(input_dir, f))])
    all_passed = True
    for test_file in test_files:
        input_path = os.path.join(input_dir, test_file)
        expected_path = os.path.join(expected_dir, test_file)
        output_path = os.path.join(output_dir, test_file)
        print(f"Running test for {test_file}:", end=" ")
        passed = run_test(input_path, expected_path, output_path, cmd)
        if not passed:
            all_passed = False
    return all_passed

if __name__ == "__main__":
    # Define paths for simple and hard simulator tests.
    simple_input_dir = 'tests/bin/simple'
    simple_expected_dir = 'tests/traces/simple'
    simple_output_dir = 'tests/user_traces/simple'
    
    hard_input_dir = 'tests/bin/hard'
    hard_expected_dir = 'tests/traces/hard'
    hard_output_dir = 'tests/user_traces/hard'
    
    # Define the simulator command (adjust if needed).
    simulator_cmd = ['python3', 'Simulator.py']
    
    print("Running simple simulator tests:")
    simple_passed = run_tests_in_directory(simple_input_dir, simple_expected_dir, simple_output_dir, simulator_cmd)
    
    print("\nRunning hard simulator tests:")
    hard_passed = run_tests_in_directory(hard_input_dir, hard_expected_dir, hard_output_dir, simulator_cmd)
    
    if simple_passed and hard_passed:
        print("\nAll simulator tests PASSED!")
    else:
        print("\nSome simulator tests FAILED!")
