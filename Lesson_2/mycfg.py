import sys
import json

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



def mycfg():
    prog = json.load(sys.stdin);
    for func in prog['functions']:
        form_blocks(func['instrs'])
    #print(prog)

if __name__ == '__main__':
    mycfg()
