import os
import subprocess

def normalized_file_content(filepath):
    with open(filepath, 'r') as f:
        # Remove trailing whitespace (including newline characters) from each line
        return [line.rstrip() for line in f.readlines()]

def run_test(test_dir, expected_dir, output_dir, assembler_cmd):
    test_files = [f for f in os.listdir(test_dir) if f.endswith('.txt')]
    passed = 0
    total = len(test_files)
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    for test_file in test_files:
        input_path = os.path.join(test_dir, test_file)
        expected_path = os.path.join(expected_dir, test_file)
        output_path = os.path.join(output_dir, test_file)
        
        # Run the assembler with the current test case
        result = subprocess.run(assembler_cmd + [input_path, output_path],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"{test_file}: FAIL (Assembler error)")
            continue
        
        # Normalize both expected and output file contents
        expected_lines = normalized_file_content(expected_path)
        output_lines = normalized_file_content(output_path)
        
        if expected_lines == output_lines:
            print(f"{test_file}: PASS")
            passed += 1
        else:
            print(f"{test_file}: FAIL")
    
    print(f"\nPassed {passed} out of {total} tests.")

if __name__ == "__main__":
    # Define paths for simple and hard tests as described in your project readme
    simple_input = 'tests/assembly/simpleBin'
    simple_expected = 'tests/assembly/bin_s'
    simple_output = 'tests/assembly/user_bin_s'
    
    hard_input = 'tests/assembly/hardBin'
    hard_expected = 'tests/assembly/bin_h'
    hard_output = 'tests/assembly/user_bin_h'
    
    # Define the assembler command (adjust if needed)
    assembler_cmd = ['python3', 'Assembler.py']
    
    print("Running simple tests:")
    run_test(simple_input, simple_expected, simple_output, assembler_cmd)
    
    print("\nRunning hard tests:")
    run_test(hard_input, hard_expected, hard_output, assembler_cmd)
