import sys

INSTRUCTION_TYPES = {
    'add': 'R', 'sub': 'R', 'slt': 'R', 'srl': 'R', 'or': 'R', 'and': 'R',
    'lw': 'I', 'addi': 'I', 'jalr': 'I',
    'sw': 'S',
    'beq': 'B', 'bne': 'B', 'blt': 'B',
    'jal': 'J'
}

OPCODES = {
    'add': '0110011', 'sub': '0110011', 'slt': '0110011', 'srl': '0110011',
    'or': '0110011', 'and': '0110011',
    'lw': '0000011', 'addi': '0010011', 'jalr': '1100111',
    'sw': '0100011',
    'beq': '1100011', 'bne': '1100011', 'blt': '1100011',
    'jal': '1101111'
}

REGISTERS = {
    'zero': '00000', 'ra': '00001', 'sp': '00010', 'gp': '00011',
    'tp': '00100', 't0': '00101', 't1': '00110', 't2': '00111',
    's0': '01000', 'fp': '01000', 's1': '01001', 'a0': '01010',
    'a1': '01011', 'a2': '01100', 'a3': '01101', 'a4': '01110',
    'a5': '01111', 'a6': '10000', 'a7': '10001', 's2': '10010',
    's3': '10011', 's4': '10100', 's5': '10101', 's6': '10110',
    's7': '10111', 's8': '11000', 's9': '11001', 's10': '11010',
    's11': '11011', 't3': '11100', 't4': '11101', 't5': '11110',
    't6': '11111'
}

# Global dictionary for labels.
LABELS = {}

def sext(value, bits):
    value = int(value)
    if value < 0:
        value = (1 << bits) + value
    return format(value, f'0{bits}b')

def tokenize(line):
    # Remove commas and parentheses.
    line = line.replace(',', ' ').replace('(', ' ').replace(')', ' ')
    words = [x for x in line.split()]
    return words if words else None

def remove_label_from_line(line, pc):
    # If a label is present, store it with its byte address (pc).
    label, sep, rest = line.partition(':')
    if sep:
        LABELS[label.strip()] = pc
        return rest.strip()
    return line

def instruction_type_R(words, opcode):
    FUNCT3 = {'add': '000', 'sub': '000', 'slt': '010', 'srl': '101', 'or': '110', 'and': '111'}
    FUNCT7 = {'add': '0000000', 'sub': '0100000', 'slt': '0000000', 'srl': '0000000', 'or': '0000000', 'and': '0000000'}
    funct3 = FUNCT3[words[0]]
    funct7 = FUNCT7[words[0]]
    rd = REGISTERS[words[1]]
    rs1 = REGISTERS[words[2]]
    rs2 = REGISTERS[words[3]]
    return f'{funct7}{rs2}{rs1}{funct3}{rd}{opcode}'

def instruction_type_I(words, opcode):
    FUNCT3 = {'lw': '010', 'addi': '000', 'jalr': '000'}
    funct3 = FUNCT3[words[0]]
    rd = REGISTERS[words[1]]
    if words[0] == "lw":
        offset, base_reg = words[2], words[3]
        rs1 = REGISTERS[base_reg]
        imm = sext(int(offset), 12)
    else:
        rs1 = REGISTERS[words[2]]
        imm = sext(int(words[3]), 12)
    return f'{imm}{rs1}{funct3}{rd}{opcode}'

def instruction_type_S(words, opcode):
    FUNCT3 = {'sw': '010'}
    offset, base_reg = words[2], words[3]
    funct3 = FUNCT3[words[0]]
    rs1 = REGISTERS[base_reg]
    rs2 = REGISTERS[words[1]]
    imm = sext(int(offset), 12)
    return f'{imm[:7]}{rs2}{rs1}{funct3}{imm[7:12]}{opcode}'

def instruction_type_B(words, opcode, pc, LABELS):
    # words: [instruction, rs1, rs2, label_or_immediate]
    # For branch, we use offset = target_address - pc  (not PC+4) per expected output.
    rs1 = REGISTERS.get(words[1])
    rs2 = REGISTERS.get(words[2])
    if rs1 is None or rs2 is None:
        return f"Error: Unknown register in {words}"
    
    if words[3] in LABELS:
        target_address = LABELS[words[3]]  # LABELS now stores byte addresses.
        offset = target_address - pc
    else:
        try:
            offset = int(words[3])
        except ValueError:
            return f"Error: Undefined label '{words[3]}'"
    
    # The branch offset must be even.
    if offset % 2 != 0:
        return f"Error: Branch offset {offset} is not even."

    # Instead of dividing by 2 and using 12 bits, we build a 13-bit field.
    # (Because the actual branch offset is represented as: {imm[12], imm[11], imm[10:5], imm[4:1], 0})
    # We represent the offset in 13 bits (two's complement).
    if offset >= 0:
        imm_field = format(offset, '013b')
    else:
        imm_field = format((1 << 13) + offset, '013b')
    
    # Now extract fields according to:
    # inst[31] (imm[12])   <-- imm_field[0]
    # inst[30:25] (imm[10:5]) <-- imm_field[2:8]   (skip imm_field[1])
    # inst[11:8] (imm[4:1])  <-- imm_field[8:12]
    # inst[7] (imm[11])     <-- imm_field[1]
    imm_12   = imm_field[0]
    imm_11   = imm_field[1]
    imm_10_5 = imm_field[2:8]
    imm_4_1  = imm_field[8:12]
    
    funct3_dict = {'beq': '000', 'bne': '001', 'blt': '100'}
    funct3 = funct3_dict.get(words[0])
    if funct3 is None:
        return f"Error: Unknown B-type instruction '{words[0]}'"
    
    # Build final 32-bit instruction:
    # [imm[12]] [imm[10:5]] [rs2] [rs1] [funct3] [imm[4:1]] [imm[11]] [opcode]
    binary_encoding = imm_12 + imm_10_5 + rs2 + rs1 + funct3 + imm_4_1 + imm_11 + opcode
    return binary_encoding

def instruction_type_J(words, opcode, pc):
    rd = REGISTERS[words[1]]
    if words[2] in LABELS:
        target_address = LABELS[words[2]]
        offset = target_address - pc  # Compute offset in bytes relative to current PC.
    else:
        try:
            offset = int(words[2])
        except ValueError:
            return f"Error: Undefined label '{words[2]}'"
    # The jump immediate stored in the instruction is offset divided by 2.
    imm = offset >> 1
    # Extract fields from the 20-bit immediate using bitwise operations.
    imm_20    = (imm >> 19) & 1        # imm[20]
    imm_10_1  = (imm >> 9) & 0x3FF       # imm[10:1] (10 bits)
    imm_11    = (imm >> 8) & 1           # imm[11]
    imm_19_12 = imm & 0xFF              # imm[19:12] (8 bits)
    # Reassemble the fields according to: imm[20|10:1|11|19:12]
    final = (imm_20 << 19) | (imm_10_1 << 9) | (imm_11 << 8) | imm_19_12
    imm_field = format(final, '020b')
    return f'{imm_field}{rd}{opcode}'

def process_line(line, pc):
    # Remove label (and record it) then tokenize.
    line_no_label = remove_label_from_line(line, pc)
    words = tokenize(line_no_label)
    if not words:
        return None
    instruction = words[0]
    if instruction not in INSTRUCTION_TYPES:
        return f"Error: Unknown instruction '{instruction}'"
    opcode = OPCODES[instruction]
    inst_type = INSTRUCTION_TYPES[instruction]
    if inst_type == 'R':
        return instruction_type_R(words, opcode)
    elif inst_type == 'I':
        return instruction_type_I(words, opcode)
    elif inst_type == 'S':
        return instruction_type_S(words, opcode)
    elif inst_type == 'B':
        return instruction_type_B(words, opcode, pc, LABELS)
    elif inst_type == 'J':
        return instruction_type_J(words, opcode, pc)
    else:
        return f"Error: Unsupported instruction type '{inst_type}'"

def assembler(input_file, output_file):
    global LABELS
    LABELS = {}
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # First pass: record labels.
    pc = 0  # PC now is a byte address.
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        _ = remove_label_from_line(line_stripped, pc)
        pc += 4  # Increment by 4 bytes per instruction.
    
    binary_output = []
    pc = 0
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        binary_line = process_line(line_stripped, pc)
        if binary_line and not binary_line.startswith("Error"):
            binary_output.append(binary_line)
        elif binary_line and binary_line.startswith("Error"):
            print(binary_line)
        pc += 4
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(binary_output))

if __name__ == "__main__":
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    assembler(input_filename, output_filename)
