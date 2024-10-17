# this script has implementations of
# 1 DOMINATOR_FRONTIER_DFS
# 2 DOMINATOR_FRONTIER_EFFICIENT
# 3 SSA_INSERT_PHI
# 4 SSA_RENAME_VARS
# 5 SSA_RESTORE_PHI
# example usage: bril2json < tests/my_testcase2.bril | python3 ssa.py 3

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
DOMINATOR_FRONTIER_DFS = "1"
DOMINATOR_FRONTIER_EFFICIENT = "2"
CONVERT_TO_SSA = "3"
CONVERT_FROM_SSA = "4"
DEF_COUNT = 1
def_to_instr = []
UNDEFINED = "__undefined"

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
               #jmp to fall through block
               jmp_instr = {}
               jmp_instr["op"] = "jmp"
               jmp_instr["labels"] = [instr["label"]]
               curr_block.append(jmp_instr)
               all_blocks.append(curr_block)
               curr_block = [{"name":instr["label"]}]
            else:
               curr_block = [{"name":instr["label"]}]
            curr_block.append(instr)

    if len(curr_block) != 0:
        all_blocks.append(curr_block)

    #create_successors(all_blocks)

    #if the first block has predecessors
    #we add an extra block at the beginning that just jumps to this block
    first_block = all_blocks[0]
    if len(get_block_predecessors(first_block[0]["name"], all_blocks)) > 1:
        entry_block = [{"name": "__entry_block"}]
        entry_block.append({"label":"__entry_block"})
        jmp_instr = {}
        jmp_instr["op"] = "jmp"
        jmp_instr["labels"] = [first_block[0]["name"]]
        entry_block.append(jmp_instr)
        all_blocks.insert(0, entry_block)


    list_of_blocks = copy.deepcopy(all_blocks)

    if sys.argv[1] == DOMINATOR_FRONTIER_DFS:
        dom_frontier_caller(all_blocks)
    if sys.argv[1] == DOMINATOR_FRONTIER_EFFICIENT:
        dom_frontier_level_order(all_blocks)
    if sys.argv[1] == CONVERT_TO_SSA:
        list_of_blocks = convert_to_ssa(all_blocks)
    if sys.argv[1] == CONVERT_FROM_SSA:
        list_of_blocks = convert_to_ssa(all_blocks)
        list_of_blocks = convert_from_ssa(all_blocks)

    for block in list_of_blocks:
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
    #print("successors", successors)
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
    #print("predecessors", predecessors)

    if predecessors:
        #init intersection_predecessors_result with out_data of first predecesor
        intersection_predecessors_result = out_data[predecessors[0]]
        #iterate over all the predecessors and take intersection of out[pred]
        for pred in predecessors[1:]:
            intersection_predecessors_result = set_intersection(intersection_predecessors_result, out_data[pred])
    #print("intersection_predecessors_result", intersection_predecessors_result)
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

    for index, block in enumerate(all_blocks):
        curr_dom = copy.copy(dom[block[0]["name"]])
        if len(curr_dom) > 0:
            curr_dom.remove(block[0]["name"])
        
        for entry in curr_dom:
            if len(curr_dom) == len(dom[entry]) and \
                    not set_difference(curr_dom, dom[entry]):
                    dom_tree[entry].append([index, block[0]["name"]])
                    break

    #print("dom tree")
    #for key, node in dom_tree.items():
    #    print(key, node)
    return dom_tree

def dom_frontier(all_blocks):
    dom = dominators(all_blocks)
    dom_frontier = {}

    for block in all_blocks:
        dom_frontier[block[0]["name"]] = []

    for block in all_blocks:
        curr_block_name = block[0]["name"]
    #    print("curr_block_name", curr_block_name)
        for index, block2 in enumerate(all_blocks):
            curr_block2_name = block2[0]["name"]
            if curr_block_name != curr_block2_name and curr_block_name in dom[curr_block2_name]:
                continue
            predecessors = get_block_predecessors(curr_block2_name, all_blocks)
    #        print("curr_block2_name, predecessors", curr_block2_name, predecessors)
    #        print("\n")
            for pred in predecessors:
                if curr_block_name in dom[pred]:
                    dom_frontier[curr_block_name].append([index, curr_block2_name])
                    break
    return dom_frontier

def dom_frontier_caller(all_blocks):
    visited = {}
    df = {}
    doms = dominators(all_blocks)

    for block in all_blocks:
        df[block[0]["name"]] = []

    for block in all_blocks:
        visited[block[0]["name"]] = False

    for block in all_blocks:
        for block2 in all_blocks:
            visited[block2[0]["name"]] = False
        visited[block[0]["name"]] = True
        #print("start")
        dom_frontier_dfs(all_blocks, block[0]["name"], doms, visited, df, block[0]["name"])
        #print("\n")

    print("---------dom--frontier---------")
    for key, entry in df.items():
        print(key, entry)
    #print("dominators")
    #for key, entry in doms.items():
    #    print(key, entry)
        
#finding dome_frontier_using_dfs
def dom_frontier_dfs(all_blocks, block, doms, visited, df, start_name):
    #print("---", block, start_name)
    #print("visited", visited)
    if block == DUMMY_EXIT_BLOCK or block == DUMMY_ENTRY_BLOCK:
        return
    successors = get_block_successors(block, all_blocks)

    for succ in successors:
        if succ == DUMMY_EXIT_BLOCK or succ == DUMMY_ENTRY_BLOCK:
            continue
        if not visited[succ] and start_name in doms[succ]:
            visited[succ] = True
            dom_frontier_dfs(all_blocks, succ, doms, visited, df, start_name)
            visited[succ] = False
        if start_name == succ or start_name not in doms[succ]:
            if succ not in df[start_name]:
                df[start_name].append(succ)
    return

#Prof bansal dom_frontier implementation
def level_order_traversal_reverse_func(all_blocks):
    dom_tree = create_dom_tree(all_blocks)
    level_order_nodes = []
    visited = {}
    for block in all_blocks:
        visited[block[0]["name"]] = False
    queue_of_nodes = [all_blocks[0][0]["name"]]

    while queue_of_nodes:
        curr_node = queue_of_nodes.pop(0)
        if curr_node == DUMMY_EXIT_BLOCK or curr_node == DUMMY_ENTRY_BLOCK or visited[curr_node]:
            continue
        visited[curr_node] = True
        level_order_nodes.append(curr_node)
        children = dom_tree[curr_node]
        for child in children:
            queue_of_nodes.append(child[1])

    return level_order_nodes

def does_X_idom_Y(node_y, dom_tree_X):
    for entry in dom_tree_X:
        if node_y == entry[1]:
            return True
    return False

def dom_frontier_level_order(all_blocks):
    bottom_up_level_order = level_order_traversal_reverse_func(all_blocks)
    bottom_up_level_order.reverse()
    dom_tree = create_dom_tree(all_blocks)
    df = {}
    for block in all_blocks:
        df[block[0]["name"]] = []

    for node in bottom_up_level_order:
        df[node] = []

        successors_of_node = get_block_successors(node, all_blocks)

        #local
        for succ in successors_of_node:
            if succ != DUMMY_EXIT_BLOCK and succ != DUMMY_ENTRY_BLOCK and not does_X_idom_Y(succ, dom_tree[node]):
                df[node].append(succ)

        #up
        children_dom_tree = dom_tree[node]
        for child in children_dom_tree:
            for df_of_child in df[child[1]]:
                if not does_X_idom_Y(df_of_child, dom_tree[node]):
                    if df_of_child not in df[node]:
                        df[node].append(df_of_child)

    print("efficient df tree\n")
    for key, value in df.items():
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
    #    print("actual_doms_are - dom[curr_block_name]", actual_doms_are, dom[curr_block_name])
        if not check_if_doms_are_equal(actual_doms_are, dom[curr_block_name]):
            return False
    return True
            
def dominators(all_blocks):
    #init out[entry] = 0, out[*] = U
    in_data = {}
    out_data = {}
    N = get_names_of_all_blocks(all_blocks) #list of all block names
    #print("N", N)

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
    if "op" in all_blocks[curr_block_index] and all_blocks[curr_block_index][-1]["op"] == "ret":
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

def get_all_vars(blocks):
    all_vars = []
    for block in blocks:
        for instr in block:
            if "dest" in instr and [instr["dest"], instr["type"]] not in all_vars:
                all_vars.append([instr["dest"], instr["type"]])
            #if "args" in instr:
            #    for arg in instr["args"]:
            #        if arg not in all_vars:
            #            all_vars.append(arg)
    #print("all_vars", all_vars)
    return all_vars

def get_all_defs(variables, blocks):
    all_defs = {}

    for block in blocks:
        for instr in block:
            if "dest" in instr:
                if instr["dest"] not in all_defs:
                    all_defs[instr["dest"]] = [block[0]["name"]]
                else:
                    all_defs[instr["dest"]].append(block[0]["name"])
    return all_defs
  #  print("all_defs")
  #  for key, value in all_defs.items():
  #      print(key, value)

def get_block_index_from_name(block_name, blocks):
    for index, block in enumerate(blocks):
        if block_name == block[0]["name"]:
            return index
    return -1
        
def is_phi_node_present_for_v(v, block):
    for instr in block:
        if "op" in instr:
            if instr["op"] == "phi" and instr["dest"] == v:
                return True
    return False

def convert_from_ssa(blocks):
    for block in blocks[:]:
        for instr in block[:]:
            #print("normal", instr)
            if "op" in instr and instr["op"] == "phi":
                #print("phi -> instr", instr)
                labels = instr["labels"]
                args = instr["args"]
                dest = instr["dest"]
                dest_type = instr["type"]
                for label_index, label in enumerate(labels):
                    #id instr adding in pred to eliminate phi instr
                    temp_instr = {}
                    temp_instr["dest"] = dest
                    temp_instr["op"] = "id"
                    temp_instr["type"] = dest_type
                    temp_instr["args"] = []
                    if args[label_index] != UNDEFINED or args[label_index] == UNDEFINED:
                        temp_instr["args"].append(args[label_index])
                        pred_index = get_block_index_from_name(label, blocks)
                        pred_block = blocks[pred_index]
                        if "op" in pred_block[-1] and pred_block[-1]["op"] in TERMINATORS:
                            blocks[pred_index].insert(-1, temp_instr)
                        else:
                            blocks[pred_index].append(temp_instr)
                #print("phi -> blocks", instr)
                block.remove(instr)
    return blocks

def convert_to_ssa(blocks):
    blocks = insert_phi_nodes(blocks)
    return rename_var_for_ssa(blocks)

def insert_phi_nodes(blocks):
   variables = get_all_vars(blocks)
   df = dom_frontier(blocks)
   defs = get_all_defs(variables, blocks)

   #variable is a pair, [x, 'int] name followed by type
   for variable in variables:
       variable_name = variable[0]
       variable_type = variable[1]
       for definition in defs.get(variable_name, []): # Blocks where v is assigned #block is a pair [1, 'loop'], block index followed by block name
           for block in df[definition]: # Dominance frontier

               #if phi instruction for variable does'nt exist only then add
               current_block = blocks[block[0]]
               if not is_phi_node_present_for_v(variable_name, current_block):
                   instr = {}
                   instr["op"] = "phi"
                   instr["type"] = variable_type 
                   instr["args"] = []
                   instr["labels"] = []
                   instr["dest"] = variable_name
                   #insert after name and label"
                   current_block.insert(2, instr)

               #since we now added phi node to the dom frontier add block to defs[variable]
               #unless it's already in there.
               if block[1] not in defs[variable_name]:
                   defs[variable_name].append(current_block[0]["name"])
   return blocks

def get_prefix_before_dot(s):
    """
    Returns the prefix of a string before the first dot.
    If no dot is found, returns the string as it is.

    :param s: The input string.
    :return: The prefix before the dot or the string itself if no dot is found.
    """
    if '.' in s:
        return s.split('.')[0]
    else:
        return s

def rename_var_for_ssa(all_blocks):
    #this has name and type
    variables = get_all_vars(all_blocks)
    variable_names = []

    #this has only type
    for variable in variables:
        variable_names.append(variable[0])

    dom_tree = create_dom_tree(all_blocks)
    #print("dom_tree", dom_tree)
    stack_of_vars = {}

    #a stack for all variables
    for variable_name in variable_names:
        stack_of_vars[variable_name] = []

    rename(all_blocks[0], dom_tree, stack_of_vars, all_blocks)
    #print("rename of vars")
    #for block in all_blocks:
    #    print(block)

    return all_blocks

def rename(block, dom_tree, stack_of_vars, all_blocks):
    #print("block_name:", block[0]["name"])
    if block[0]["name"] == DUMMY_ENTRY_BLOCK or block[0]["name"] == DUMMY_EXIT_BLOCK:
        return 
    vars_pushed = []
    for index, instr in enumerate(block):
        #replace each argument with stack[old name]
        if "args" in instr:
            all_args = instr["args"]
            for index, arg in enumerate(all_args):
                if arg in stack_of_vars:
                    all_args[index] = stack_of_vars[arg][0][-1]
            instr["args"] = all_args

        #replace instr's destination with a new name
        if "dest" in instr:
            #print("current_block", block[0]["name"])
            #print(block)
            curr_name = instr["dest"]
            #print("stv", stack_of_vars[curr_name])
            if len(stack_of_vars[curr_name]) == 0 or len(stack_of_vars[curr_name][0]) == 0:
                stack_of_vars[curr_name] = [[curr_name + ".0"],  0]
                new_name = stack_of_vars[curr_name][0][-1]
            else:
                #print("curr_name", stack_of_vars[curr_name])
                #print("index, instr", index, instr)
                #print("begin - curr_name", curr_name, stack_of_vars[curr_name])
                new_name = get_new_name_for_var(stack_of_vars[curr_name])
                stack_of_vars[curr_name][0].append(new_name)
                stack_of_vars[curr_name][1] += 1
                #print("after - curr_name", block[0]["name"], curr_name, stack_of_vars[curr_name])
            instr["dest"] = new_name
            #print("b", stack_of_vars[curr_name])
            #block[index] = copy.deepcopy(instr)
            #print("after")
            #print(block)
            #print("block[index] = ", block[index])
            vars_pushed.append(curr_name)

    successors = get_block_successors(block[0]["name"], all_blocks)
    for succ in successors:
        if succ != DUMMY_ENTRY_BLOCK and succ != DUMMY_EXIT_BLOCK:
            #print("successors", successors)
            succ_block = all_blocks[get_block_index_from_name(succ, all_blocks)]
            #print("succ_block", succ_block)
            phi_instr_indexes = get_phi_instr_indexes(succ_block) 
            #print("phi_instr_indexes", phi_instr_indexes)
            if len(phi_instr_indexes) > 0:
                for phi_index in phi_instr_indexes:
                #for each phi instr in block, update the args and labels FIXME
                    phi_instr = succ_block[phi_index]
                    #print("phi_instr", phi_instr)
                    dest = get_prefix_before_dot(phi_instr["dest"])
                    if len(stack_of_vars[dest]) == 0 or len(stack_of_vars[dest][0]) == 0:
                        phi_instr["args"].append(UNDEFINED)
                    else:
                        phi_instr["args"].append(stack_of_vars[dest][0][-1])

                    phi_instr["labels"].append(block[0]["name"])
                    succ_block[phi_index] = phi_instr

    #iterate over children in dom tree
    for b in dom_tree[block[0]["name"]]:
        rename(all_blocks[get_block_index_from_name(b[1], all_blocks)], dom_tree, stack_of_vars, all_blocks)

    #pop all names that we just pushed onto on stack
    for var in vars_pushed:
        stack_of_vars[var][0].pop()


def get_new_name_for_var(old_var_name):
    #print("old_var_name", old_var_name)
    # Split the string at the last occurrence of the dot
    base, num_str = old_var_name[0][-1].rsplit('.', 1)

    count = old_var_name[1]
    count += 1
    
    # Combine the base with the incremented number
    return f"{base}.{count}"

def get_path_label_index(block_name, preds):
    index = 0
    while index < len(preds):
        if block_name == preds[index]:
            return index
        index += 1
    return -1

def has_phi_instr(block):
    for instr in block:
        if "op" in instr and instr["op"] == "phi":
            return True
    return False

def get_phi_instr_indexes(block):
    phi_instr_indexes = []
    for index, instr in enumerate(block):
        if "op" in instr and instr["op"] == "phi":
            phi_instr_indexes.append(index)
    return phi_instr_indexes

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
    if sys.argv[1] == CONVERT_TO_SSA:
        print(output_json)
    if sys.argv[1] == CONVERT_FROM_SSA:
        print(output_json)

if __name__ == "__main__":
    create_cfg()
