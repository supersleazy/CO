import sys

def sign_extend(bin_str, bits):
    """Converts a binary string in two's complement to a signed integer."""
    if bin_str[0] == '1':
        return int(bin_str, 2) - (1 << len(bin_str))
    else:
        return int(bin_str, 2)

# Global state
REGISTERS = [0] * 32        # 32 registers; x0 is always 0
MEMORY = [0] * 32           # Data memory: 32 words (each 32 bits)
INSTR_MEM = []              # Instruction memory: list of 32-bit binary strings
PC = 0                      # Program Counter (in bytes)

def update_x0():
    """Ensure x0 remains 0."""
    REGISTERS[0] = 0

# --- Decode Functions ---

def decode_R(inst):
    funct7 = inst[0:7]
    rs2 = int(inst[7:12], 2)
    rs1 = int(inst[12:17], 2)
    funct3 = inst[17:20]
    rd   = int(inst[20:25], 2)
    return funct7, rs1, rs2, funct3, rd

def decode_I(inst):
    imm = inst[0:12]
    rs1 = int(inst[12:17], 2)
    funct3 = inst[17:20]
    rd   = int(inst[20:25], 2)
    return imm, rs1, funct3, rd

def decode_S(inst):
    imm_hi = inst[0:7]
    rs2 = int(inst[7:12], 2)
    rs1 = int(inst[12:17], 2)
    funct3 = inst[17:20]
    imm_lo = inst[20:25]
    imm = imm_hi + imm_lo
    return imm, rs1, rs2, funct3

def decode_B(inst):
    # B-type: [31] imm[12], [30:25] imm[10:5],
    # [24:20] rs2, [19:15] rs1, [14:12] funct3, [11:8] imm[4:1], [7] imm[11]
    imm12   = inst[0]
    imm10_5 = inst[1:7]
    rs2     = int(inst[7:12], 2)
    rs1     = int(inst[12:17], 2)
    funct3  = inst[17:20]
    imm4_1  = inst[20:24]
    imm11   = inst[24]
    # Reassemble immediate with an appended 0 as LSB
    imm_bin = imm12 + imm11 + imm10_5 + imm4_1 + '0'
    return imm_bin, rs1, rs2, funct3

def decode_J(inst):
    # J-type: [31] imm[20], [30:21] imm[10:1], [20] imm[11], [19:12] imm[19:12], [11:7] rd
    imm20   = inst[0]
    imm10_1 = inst[1:11]
    imm11   = inst[11]
    imm19_12 = inst[12:20]
    rd = int(inst[20:25], 2)
    # Reassemble immediate and append a 0 as LSB
    imm_bin = imm20 + imm19_12 + imm11 + imm10_1 + '0'
    return imm_bin, rd

# --- Execute Functions ---

def execute_R(inst):
    funct7, rs1, rs2, funct3, rd = decode_R(inst)
    op1 = REGISTERS[rs1]
    op2 = REGISTERS[rs2]
    if funct3 == '000':
        if funct7 == '0000000':  # add
            REGISTERS[rd] = (op1 + op2) & 0xFFFFFFFF
        elif funct7 == '0100000':  # sub
            REGISTERS[rd] = (op1 - op2) & 0xFFFFFFFF
    elif funct3 == '010':         # slt
        REGISTERS[rd] = 1 if op1 < op2 else 0
    elif funct3 == '101':         # srl
        shamt = op2 & 0x1F
        REGISTERS[rd] = (op1 & 0xFFFFFFFF) >> shamt
    elif funct3 == '110':         # or
        REGISTERS[rd] = op1 | op2
    elif funct3 == '111':         # and
        REGISTERS[rd] = op1 & op2

def execute_I(inst, opcode):
    imm, rs1, funct3, rd = decode_I(inst)
    imm_val = sign_extend(imm, 12)
    op1 = REGISTERS[rs1]
    if opcode == "0010011":   # addi
        REGISTERS[rd] = (op1 + imm_val) & 0xFFFFFFFF
    elif opcode == "0000011":   # lw
        addr = op1 + imm_val
        index = addr // 4
        if 0 <= index < len(MEMORY):
            REGISTERS[rd] = MEMORY[index]
        else:
            REGISTERS[rd] = 0
    elif opcode == "1100111":   # jalr
        next_pc = PC + 4
        REGISTERS[rd] = next_pc
        target = (op1 + imm_val) & 0xFFFFFFFE
        return target
    return None

def execute_S(inst):
    imm, rs1, rs2, funct3 = decode_S(inst)
    imm_val = sign_extend(imm, 12)
    addr = REGISTERS[rs1] + imm_val
    index = addr // 4
    if 0 <= index < len(MEMORY):
        MEMORY[index] = REGISTERS[rs2]

def execute_B(inst):
    imm_bin, rs1, rs2, funct3 = decode_B(inst)
    imm_val = sign_extend(imm_bin, 13)
    branch = False
    op1 = REGISTERS[rs1]
    op2 = REGISTERS[rs2]
    if funct3 == '000':  # beq
        branch = (op1 == op2)
    elif funct3 == '001':  # bne
        branch = (op1 != op2)
    elif funct3 == '100':  # blt
        branch = (op1 < op2)
    return branch, imm_val

def execute_J(inst):
    imm_bin, rd = decode_J(inst)
    imm_val = sign_extend(imm_bin, 21)
    REGISTERS[rd] = (PC + 4) & 0xFFFFFFFF
    return imm_val

# --- Simulation Loop ---

def simulate(binary_file, trace_file):
    global PC, REGISTERS, MEMORY, INSTR_MEM
    REGISTERS = [0] * 32
    MEMORY = [0] * 32
    PC = 0
    # Read the machine code file (each line is a 32-bit binary string)
    with open(binary_file, 'r') as f:
        INSTR_MEM = [line.strip() for line in f if line.strip()]

    trace_lines = []
    # Execute instructions and record the state AFTER each instruction execution.
    while True:
        index = PC // 4
        if index < 0 or index >= len(INSTR_MEM):
            break
        inst = INSTR_MEM[index]
        opcode = inst[25:32]

        # Check for Virtual Halt (beq x0,x0,0)
        if opcode == "1100011":
            imm_bin, rs1, rs2, funct3 = decode_B(inst)
            imm_val = sign_extend(imm_bin, 13)
            if funct3 == "000" and rs1 == 0 and rs2 == 0 and imm_val == 0:
                PC += 4
                update_x0()
                trace_lines.append(f"{PC} " + " ".join(str(reg) for reg in REGISTERS))
                break

        new_pc = None
        if opcode == "0110011":
            execute_R(inst)
        elif opcode in ["0010011", "0000011", "1100111"]:
            new_pc = execute_I(inst, opcode)
        elif opcode == "0100011":
            execute_S(inst)
        elif opcode == "1100011":
            branch, imm_val = execute_B(inst)
            if branch:
                new_pc = PC + imm_val
        elif opcode == "1101111":
            imm_val = execute_J(inst)
            new_pc = PC + imm_val

        update_x0()
        if new_pc is not None:
            PC = new_pc
        else:
            PC += 4
        # Record state after instruction execution: PC and registers (in decimal)
        trace_lines.append(f"{PC} " + " ".join(str(reg) for reg in REGISTERS))

    # Write trace lines to output file
    with open(trace_file, 'w') as f:
        for line in trace_lines:
            f.write(line + "\n")
        # Memory dump: print addresses (starting at 0x00010000) and memory words in decimal.
        mem_addr = 0x00010000
        for word in MEMORY:
            f.write(f"0x{mem_addr:08X}:{word}\n")
            mem_addr += 4

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 Simulator.py <input_machine_code_file.txt> <output_trace_file.txt>")
        sys.exit(1)
    binary_file = sys.argv[1]
    trace_file = sys.argv[2]
    simulate(binary_file, trace_file)
