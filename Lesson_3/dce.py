import sys
import json
import copy

TERMINATORS = 'jmp', 'br', 'ret'
JMP_OR_BRANCH = 'jmp', 'br'

def form_blocks(body):
    all_blocks = []
    curr_block = []
    block_count = 0
    for instr in body:
        #print(instr)
        #print("varun")

        if len(curr_block) == 0 and 'label' not in instr:
            curr_block = [{"name":"b"+str(block_count)}]
            block_count = block_count + 1

        if 'op' in instr:
            curr_block.append(instr)
            if instr['op'] in TERMINATORS:
                all_blocks.append(curr_block)
                curr_block = []
        else:
           if len(curr_block) != 0:
                all_blocks.append(curr_block)
                curr_block = [{"name":instr['label']}]
           else:
                curr_block = [{"name":instr['label']}]
           #curr_block = [instr]

    if len(curr_block) != 0:
        all_blocks.append(curr_block)

    print("List of blocks:")
    for block in all_blocks:
        #print(block)
        print(block[0]['name'])
        print(block[1:])
        print("\n")
    print("All blocks:")
    print(all_blocks)
    create_successors(all_blocks)

def create_successors(blocks):
    successors = []
    for index, block in enumerate(blocks):
        if block[-1]['op'] in JMP_OR_BRANCH: #if last is terminator then extract labels
            successors.append({block[0]["name"]:block[-1]['labels']})
        else:
            if index != len(blocks) - 1:
                successors.append({block[0]["name"]:blocks[index+1][0]["name"]})
            else:
                successors.append({block[0]["name"]:""})
    print("\nSuccessors:")
    print(successors)

    index = 0
    while index < len(blocks):
        remove_dead_code(blocks[index])
        print(remove_dead_code)
        print(blocks[index])
        index += 1

def check_if_in_args(var_name, start, block):
    mul_def_found = False
    for instr in block[start:]:
        if 'dest' in instr:
            if var_name == instr['dest']:
                return False
        if 'args' in instr:
            if var_name in instr['args']:
                return True
    return False

def remove_dead_code(block):
    print("before dce\n")
    print(block)

    while True:
        orig_block = copy.deepcopy(block)
        index = 0
        while index < len(block):
        #check if instr has destination
        # save the name of the name of the destination
        # now see if this name is present as args in the following instructions.
        # if now delete the instruction, else keep the instruction
            if 'dest' in block[index]:
                var_name = block[index]['dest']
                if not check_if_in_args(var_name, index+1, block):
                    del block[index]
            index += 1
        print("after dce\n")
        print(block)
        if orig_block == block:
            break



def mycfg():
    prog = json.load(sys.stdin);
    for func in prog['functions']:
        form_blocks(func['instrs'])
    #print(prog)

if __name__ == '__main__':
    mycfg()
