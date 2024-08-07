# this script has implementations of
# 1 dominators
# 2 dom tree
# 3 dom frontiers
# 4 post dominators
# 5 verifying dominators
# 6 back edges
# example usage: bril2json < tests/my_testcase2.bril | python3 global_analysis.py 3

import sys
import json
import copy

TERMINATORS = "jmp", "br", "ret"
JMP_OR_BRANCH = "jmp", "br"
COMMUTATIVE_OPS = "add", "mul", "sub", "and", "or"
OPERATORS_WHICH_EVALUATE = "add", "mul", "sub", "div", "gt", "lt",\
        "ge", "le", "eq", "and", "or", "not"


DUMMY_ENTRY_BLOCK = "dummy_entry_block"
DUMMY_EXIT_BLOCK = "dummy_exit_block"
DOMINATORS = "1"
DOM_TREE = "2"
DOM_FRONTIERS = "3"
POST_DOMINATORS = "4"
VERIFY_DOMINATORS = "5"
BACK_EDGES = "6"

def form_blocks(function, output_json, index_func):
    body = function["instrs"]
    func_name = function["name"]
    all_blocks = []
    curr_block = []
    block_count = 0
    for instr in body:
        if len(curr_block) == 0 and "label" not in instr:
            curr_block = [{"name":"__b"+str(block_count)}]
            block_count = block_count + 1

        if "op" in instr:
            curr_block.append(instr)
            if instr["op"] in TERMINATORS:
                all_blocks.append(curr_block)
                curr_block = []
        else:
            if len(curr_block) != 0:
               all_blocks.append(curr_block)
               curr_block = [{"name":instr["label"]}]
            else:
               curr_block = [{"name":instr["label"]}]
            curr_block.append(instr)

    if len(curr_block) != 0:
        all_blocks.append(curr_block)

    #create_successors(all_blocks)

    list_of_blocks = copy.deepcopy(all_blocks)

    for block in all_blocks:
        for instr in block:
            if "name" not in instr:
                output_json["functions"][index_func]["instrs"].append(instr)
            else:
                if instr["name"].startswith("__b"):
                    del instr["name"]

    output_json["functions"][index_func]["name"] = func_name
    if "args" in function:
        output_json["functions"][index_func]["args"] = function["args"]
    if "type" in function:
        output_json["functions"][index_func]["type"] = function["type"]
    return list_of_blocks

def print_all_instrs(all_blocks):
    for index, block in enumerate(all_blocks):
        print(index)
        for instr in block:
            print(instr)
        print("\n")

def set_union(setA, setB):
    union_list = []
    for element in setA:
        if element not in union_list:
            union_list.append(element)
    for element in setB:
        if element not in union_list:
            union_list.append(element)
    return union_list

def set_difference(setA, setB):
    set_diff_list = list(setA)
    for element in setB:
        if element in set_diff_list:
            set_diff_list.remove(element)
    return set_diff_list

def set_intersection(setA, setB):
    intersection_list = []
    for element in setA:
        if element in setB:
            intersection_list.append(element)
    return intersection_list

def intersection_of_successors_in_data(curr_block_name, all_blocks, in_data):
    successors = get_block_successors(curr_block_name, all_blocks)
    print("successors", successors)
    intersection_successors_result = []

    if successors:
        #init intersection_successors_result with in_data of first successor
        intersection_successors_result = in_data[successors[0]]
        #iterate over all the successors and take intersection of in[suc]
        for succ in successors[1:]:
            intersection_successors_result = set_intersection(intersection_successors_result, in_data[succ])
    return intersection_successors_result

def intersection_of_predecessors_out_data(curr_block_name, all_blocks, out_data):
    predecessors = get_block_predecessors(curr_block_name, all_blocks)
    intersection_predecessors_result = []
    print("predecessors", predecessors)

    if predecessors:
        #init intersection_predecessors_result with out_data of first predecesor
        intersection_predecessors_result = out_data[predecessors[0]]
        #iterate over all the predecessors and take intersection of out[pred]
        for pred in predecessors[1:]:
            intersection_predecessors_result = set_intersection(intersection_predecessors_result, out_data[pred])
    print("intersection_predecessors_result", intersection_predecessors_result)
    return intersection_predecessors_result

def add_predecessors_curr_block_worklist(worklist, curr_block_name, all_blocks):
    predecessors = get_block_predecessors(curr_block_name, all_blocks)

    #if pred is not in predecessors only then add to worklist
    for pred in predecessors:
        if pred not in worklist and pred != DUMMY_ENTRY_BLOCK and pred != DUMMY_EXIT_BLOCK:
            worklist.append(pred)

def add_successors_curr_block_worklist(worklist, curr_block_name, all_blocks):
    successors = get_block_successors(curr_block_name, all_blocks)

    #if succ is not in successors only then add to worklist
    for succ in successors:
        if succ not in worklist and succ != DUMMY_ENTRY_BLOCK and succ != DUMMY_EXIT_BLOCK:
            worklist.append(succ)

def get_names_of_all_blocks(all_blocks):
    list_of_all_blocks = []
    for block in all_blocks:
        list_of_all_blocks.append(block[0]["name"])
    return list_of_all_blocks

def create_dom_tree(all_blocks):
    dom = dominators(all_blocks)
    dom_tree = {}

    #init dom tree
    for block in all_blocks:
        dom_tree[block[0]["name"]] = []

    for block in all_blocks:
        curr_dom = copy.copy(dom[block[0]["name"]])
        if len(curr_dom) > 0:
            curr_dom.remove(block[0]["name"])
        
        for entry in curr_dom:
            if len(curr_dom) == len(dom[entry]) and \
                    not set_difference(curr_dom, dom[entry]):
                    dom_tree[entry].append(block[0]["name"])
                    break

    print("dom tree")
    for key, node in dom_tree.items():
        print(key, node)

def dom_frontier(all_blocks):
    dom = dominators(all_blocks)
    dom_frontier = {}

    for block in all_blocks:
        dom_frontier[block[0]["name"]] = []

    for block in all_blocks:
        curr_block_name = block[0]["name"]
        #print("curr_block_name", curr_block_name)
        for dom_key, dom_value in dom.items():
            if curr_block_name != dom_key and curr_block_name in dom_value:
                successors = get_block_successors(dom_key, all_blocks)
                #print("successors dom_key dom_value", successors, dom_key, dom_value)
                for succ in successors:
                    if succ != DUMMY_EXIT_BLOCK and curr_block_name not in dom[succ]:
                        #print("succ dom[succ]", succ, dom[succ])
                        dom_frontier[curr_block_name].append(succ)

    print("---------dom_frontier-------")
    for key, value in dom_frontier.items():
        print(key, value)

def all_visited(visited):
    for key, value in visited.items():
        if value == False:
            return False
    return True

def get_all_paths_from_entry(all_blocks, destination):
    curr_path = []
    visited = {}

    for block in all_blocks:
        visited[block[0]["name"]] = False
    
    visited[all_blocks[0][0]["name"]] = True
    curr_path.append(all_blocks[0][0]["name"])
    result = []
    get_path(curr_path, all_blocks, destination, visited, result)
    return result

def get_path(curr_path, all_blocks, destination, visited, result):
    if len(curr_path) == 0:
        return
    if curr_path[-1] == destination:
        curr_path_clone = curr_path[:]
        result.append(curr_path_clone)
        return

    curr_path_copy = curr_path[:]
    if (not all_visited(visited) and len(curr_path) != 0):
        top_block = curr_path_copy[-1]
        successors = get_block_successors(top_block, all_blocks)
        if len(successors) > 0:
            for succ in successors:
                if succ != DUMMY_EXIT_BLOCK and visited[succ] == False:
                    visited[succ] = True
                    curr_path_copy.append(succ)
                    get_path(curr_path_copy, all_blocks, destination, visited, result)
                    curr_path_copy.pop()
                    visited[succ] = False
        return

def intersection_of_paths(all_paths):
    intersection_paths = []
    if len(all_paths) == 1:
        return all_paths[0]
    else:
        intersection_paths = all_paths[0]
        for path in all_paths[1:]:
            intersection_paths = set_intersection(intersection_paths, path)
    return intersection_paths

def check_if_doms_are_equal(list1, list2):
    if len(list1) == len(list2):
        if len(set_difference(list1, list2)) == 0:
            return True
    return False

def verify_dominators(all_blocks):
    dom = dominators(all_blocks)
    for block in all_blocks:
        curr_block_name = block[0]["name"]
        all_paths_from_entry = get_all_paths_from_entry(all_blocks, curr_block_name)
        actual_doms_are = intersection_of_paths(all_paths_from_entry)
        print("actual_doms_are - dom[curr_block_name]", actual_doms_are, dom[curr_block_name])
        if not check_if_doms_are_equal(actual_doms_are, dom[curr_block_name]):
            return False
    return True
            
def back_edges(all_blocks):
    dom = dominators(all_blocks)
    #a->b, b dominates a => a->b is a back edge
    back_edges = []

    for block in all_blocks:
        curr_block_name = block[0]["name"]
        successors = get_block_successors(curr_block_name, all_blocks)
        for succ in successors: 
            if succ in dom[curr_block_name]:
                back_edges.append([curr_block_name, succ])
    print("back_edges")
    for edge in back_edges:
        print(edge)

def post_dominators(all_blocks):
    #init out[entry] = 0, out[*] = U
    in_data = {}
    out_data = {}
    N = get_names_of_all_blocks(all_blocks) #list of all block names
    print("N", N)

    for block in all_blocks:
        in_data[block[0]["name"]] = N
    in_data[DUMMY_EXIT_BLOCK] = []

    #init worklist
    worklist = list(in_data.keys())
    worklist.remove(DUMMY_EXIT_BLOCK)

    #iterate over worklist till not empty
    while worklist:
        #get first block from worklist
        curr_block_name = worklist.pop(0)

        in_data_copy = list(in_data[curr_block_name])

        #out[B] = intersection of p, predecessor of B IN[P]
        out_data[curr_block_name] = intersection_of_successors_in_data(curr_block_name, all_blocks, in_data)
        #in[B] = B U out[B]
        in_data[curr_block_name] = set_union([curr_block_name], out_data[curr_block_name])

        #if out_data changed add its successors to worklist
        #as IN[succ] will change
        if in_data[curr_block_name] != in_data_copy:
            add_predecessors_curr_block_worklist(worklist, curr_block_name, all_blocks)

    print("----------post dominators analysis-----------")
    print("\n-------------in_data------------")
    for in_info in in_data:
        print(in_info, in_data[in_info])
    print("\n-----------out_data-----------")
    for out_info in out_data:
        print(out_info, out_data[out_info])
    print("\n\n")
    return out_data

def dominators(all_blocks):
    #init out[entry] = 0, out[*] = U
    in_data = {}
    out_data = {}
    N = get_names_of_all_blocks(all_blocks) #list of all block names
    print("N", N)

    for block in all_blocks:
        out_data[block[0]["name"]] = N
    out_data[DUMMY_ENTRY_BLOCK] = []

    #init worklist
    worklist = list(out_data.keys())
    worklist.remove(DUMMY_ENTRY_BLOCK)

    #iterate over worklist till not empty
    while worklist:
        #get first block from worklist
        curr_block_name = worklist.pop(0)

        out_data_copy = list(out_data[curr_block_name])

        #in[B] = intersection of p, predecessor of B OUT[P]
        in_data[curr_block_name] = intersection_of_predecessors_out_data(curr_block_name, all_blocks, out_data)
        #out[B] = B U in[B]
        out_data[curr_block_name] = set_union([curr_block_name], in_data[curr_block_name])

        #if out_data changed add its successors to worklist
        #as IN[succ] will change
        if out_data[curr_block_name] != out_data_copy:
            add_successors_curr_block_worklist(worklist, curr_block_name, all_blocks)

    print("----------dominators analysis-----------")
    print("\n-------------in_data------------")
    for in_info in in_data:
        print(in_info, in_data[in_info])
    print("\n-----------out_data-----------")
    for out_info in out_data:
        print(out_info, out_data[out_info])
    print("\n\n")
    return out_data

def get_block_successors(curr_block_name, all_blocks):
    successors = []
    last_block_name = all_blocks[-1][0]["name"]
    last_block_last_instr = all_blocks[-1][-1]
    #if its last block, if last instr is ret or last instr is not (ret, jmp, br) fall through to exit, succ is exit
    if curr_block_name == last_block_name:
        if "op" not in last_block_last_instr or\
        last_block_last_instr["op"] == "ret" or last_block_last_instr["op"] not in TERMINATORS:
            successors.append(DUMMY_EXIT_BLOCK)
            return successors

    #calc curr_block index
    curr_block_index = -1
    for index, block in enumerate(all_blocks):
        if curr_block_name == block[0]["name"]:
            curr_block_index = index
            break

    #if last instr of curr_block is ret, succ is exit
    if all_blocks[curr_block_index][-1]["op"] == "ret":
        successors.append(DUMMY_EXIT_BLOCK)
        return successors

    #if last statement of block is jmp or br then use that successors
    if "op" in all_blocks[curr_block_index][-1] \
            and all_blocks[curr_block_index][-1]["op"] in JMP_OR_BRANCH: #if last is terminator then extract labels
        successors = all_blocks[curr_block_index][-1]["labels"]
    else:
        #if not the last block, add next block as successor
        if curr_block_index != len(all_blocks) - 1:
            successors.append(all_blocks[curr_block_index + 1][0]["name"])
    return successors

def get_block_predecessors(block_name, all_blocks):
    predecessors = []
    if block_name == all_blocks[0][0]["name"]:
        predecessors.append(DUMMY_ENTRY_BLOCK)
        return predecessors
    block_name_index = 0
    for index, block in enumerate(all_blocks):
        if block_name == block[0]["name"]:
            block_name_index = index
        #check if block_name in the last instruction of a block
        #part of jmp or branch instr
        if "op" in block[-1] and block[-1]["op"] in JMP_OR_BRANCH: #if last is terminator then extract labels
            labels = block[-1]["labels"]
            if block_name in labels:
                #print("in loop: " , block[0]["name"])
                predecessors.append(block[0]["name"])

    #check if block_name is fallback of a block before it
    if block_name_index != 0:
        if not ("op" in all_blocks[block_name_index - 1][-1] and \
                all_blocks[block_name_index-1][-1]["op"] in TERMINATORS): #if last is terminator then extract labels
            predecessors.append(all_blocks[block_name_index-1][0]["name"])
    return predecessors

def create_successors(blocks):
    successors = []
    for index, block in enumerate(blocks):
        if "op" in block[-1] and block[-1]["op"] in JMP_OR_BRANCH: #if last is terminator then extract labels
            successors.append({block[0]["name"]:block[-1]["labels"]})
        else:
            if index != len(blocks) - 1:
                successors.append({block[0]["name"]:blocks[index+1][0]["name"]})
            else:
                successors.append({block[0]["name"]:""})

def create_cfg():
    prog = json.load(sys.stdin);
    output_json = {
            "functions" : [
                {
                "instrs": [],
                }
            ]
        }
    for index, func in enumerate(prog["functions"]):
        all_blocks = form_blocks(func, output_json, index)
    output_json = json.dumps(output_json, indent=4)

    if sys.argv[1] == DOMINATORS:
        dominators(all_blocks)
    if sys.argv[1] == DOM_TREE:
        create_dom_tree(all_blocks)
    if sys.argv[1] == DOM_FRONTIERS:
        dom_frontier(all_blocks)
    if sys.argv[1] == POST_DOMINATORS:
        post_dominators(all_blocks)
    if sys.argv[1] == VERIFY_DOMINATORS:
        verify_dominators(all_blocks)
    if sys.argv[1] == BACK_EDGES:
        back_edges(all_blocks)

if __name__ == "__main__":
    create_cfg()
