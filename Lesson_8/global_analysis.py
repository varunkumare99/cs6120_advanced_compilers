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
import itertools

TERMINATORS = "jmp", "br", "ret"
JMP_OR_BRANCH = "jmp", "br"
COMMUTATIVE_OPS = "add", "mul", "sub", "and", "or"
OPERATORS_WHICH_EVALUATE = "add", "mul", "sub", "div", "gt", "lt",\
        "ge", "le", "eq", "and", "or", "not"
PRE_HEADER = "__pre_header"


DUMMY_ENTRY_BLOCK = "dummy_entry_block"
DUMMY_EXIT_BLOCK = "dummy_exit_block"
DOMINATORS = "1"
DOM_TREE = "2"
DOM_FRONTIERS = "3"
POST_DOMINATORS = "4"
VERIFY_DOMINATORS = "5"
BACK_EDGES = "6"
NATURAL_LOOPS = "7"
IDENTIFY_LOOP_INVARIANTS = "8"
loop_found = False
DEF_COUNT = 1
def_to_instr = {}

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
    if sys.argv[1] == NATURAL_LOOPS:
        get_natural_loops(all_blocks)
    if sys.argv[1] == IDENTIFY_LOOP_INVARIANTS:
        identify_loop_invariant_instrs(all_blocks)

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

    for block in all_blocks:
        curr_dom = copy.copy(dom[block[0]["name"]])
        if len(curr_dom) > 0:
            curr_dom.remove(block[0]["name"])
        
        for entry in curr_dom:
            if len(curr_dom) == len(dom[entry]) and \
                    not set_difference(curr_dom, dom[entry]):
                    dom_tree[entry].append(block[0]["name"])
                    break

    #print("dom tree")
    #for key, node in dom_tree.items():
    #    print(key, node)

def dom_frontier(all_blocks):
    dom = dominators(all_blocks)
    dom_frontier = {}

    for block in all_blocks:
        dom_frontier[block[0]["name"]] = []

    for block in all_blocks:
        curr_block_name = block[0]["name"]
        #print("curr_block_name", curr_block_name)
        for block2 in all_blocks:
            curr_block2_name = block2[0]["name"]
            if curr_block_name != curr_block2_name and curr_block_name in dom[curr_block2_name]:
                continue
            predecessors = get_block_predecessors(curr_block2_name, all_blocks)
            #print("curr_block2_name, predecessors", curr_block2_name, predecessors)
            #print("\n")
            for pred in predecessors:
                if curr_block_name in dom[pred]:
                    dom_frontier[curr_block_name].append(curr_block2_name)
                    break

    #print("---------dom_frontier-------")
    #for key, value in dom_frontier.items():
    #    print(key, value)

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
        #print("actual_doms_are - dom[curr_block_name]", actual_doms_are, dom[curr_block_name])
        if not check_if_doms_are_equal(actual_doms_are, dom[curr_block_name]):
            return False
    return True
            
def get_back_edges(all_blocks):
    dom = dominators(all_blocks)
    #a->b, b dominates a => a->b is a back edge
    back_edges = []

    for block in all_blocks:
        curr_block_name = block[0]["name"]
        successors = get_block_successors(curr_block_name, all_blocks)
        for succ in successors: 
            if succ in dom[curr_block_name]:
                back_edges.append([curr_block_name, succ])
    #print("back_edges")
    #for edge in back_edges:
    #    print(edge)
    return back_edges

def get_natural_loops(all_blocks):
    all_def_num_to_instrs(all_blocks)
    #for block in all_blocks:
    #    print(block)
    back_edges = get_back_edges(all_blocks)
    doms = dominators(all_blocks)
    result = []
    #print("back_edges:", back_edges)
    #print("doms:", doms)
    global loop_found

    #if not back_edges:
    #     print("\nno natural loops buddy")

    for edge in back_edges:
        header = edge[1]
    #    print("header:", header)
        dominated_by_header = find_all_nodes_dominated_by_X(header, doms)
        #print("dom by header:", dominated_by_header)
        visited = {}
        for block in all_blocks:
            visited[block[0]["name"]] = False
        loop_found = False
        natural_loop = []
        visited[header] = True
        natural_loop.append(header)
        dfs_find_natural_loops(all_blocks, header, dominated_by_header, visited, header, edge, natural_loop)
        if loop_found:
            #print("\nnatural loop:")
            #print(natural_loop)
            result.append(natural_loop)
            #print("\nnatural loop:")
            #print(natural_loop)
            get_all_instructions_in_natural_loop(natural_loop, all_blocks)
        #else:
        #    print("\nno natural loops buddy")
    return result

def get_block_index_from_name(block_name, blocks):
    for index, block in enumerate(blocks):
        if block_name == block[0]["name"]:
            return index
    return -1 

def are_definitions_outside_loop(reaching_defs_preds, reaching_defs_loop_body, variable):
    rd1_var = get_all_reaching_defs_of_variable(variable, reaching_defs_preds)
    rd2_var = get_all_reaching_defs_of_variable(variable, reaching_defs_loop_body)

    #check if all def reaching loop body for variable is coming from outside the loop
    #print("rd1_var", rd1_var)
    #print("rd2_var", rd2_var)
    for def_var in rd2_var:
        if def_var not in rd1_var:
            return False
    return True

def get_all_reaching_defs_of_variable(variable, reaching_defs):
    all_reaching_defs_of_variable = []
    for curr_def in reaching_defs:
        instr = def_to_instr[curr_def]
        if instr["dest"] == variable:
            all_reaching_defs_of_variable.append(curr_def)
    return all_reaching_defs_of_variable

def get_preds_not_in_natural_loop(loop_header, natural_loop, all_blocks):
    preds = get_block_predecessors(loop_header, all_blocks)
    preds_not_in_natural_loop = [pred for pred in preds if pred not in natural_loop]
    #print("preds, preds_not_in_natural_loop", preds, preds_not_in_natural_loop)
    return preds_not_in_natural_loop
     

def loop_invariant_instr_dominates_uses(li_instr, natural_loop, all_blocks):
    doms = dominators(all_blocks)
    def_block = find_def_block_of_loop_invariant_instr(natural_loop, li_instr, all_blocks)
    uses_block = var_used_block_list_from_loop(natural_loop, li_instr["dest"], all_blocks)

    for block in uses_block:
        if def_block not in doms[block]:
            return False
    return True

def loop_invariant_instr_dominates_all_exits(li_instr, natural_loop, all_blocks):
    doms = dominators(all_blocks)
    def_block = find_def_block_of_loop_invariant_instr(natural_loop, li_instr, all_blocks)
    for node in natural_loop[:-1]:
        if node == def_block:
            continue
        block_index = get_block_index_from_name(node, all_blocks)
        #print("block_index", block_index)
        for block in all_blocks[block_index]:
            #print("block", block)
            if "op" in all_blocks[block_index][-1] and all_blocks[block_index][-1]["op"] in JMP_OR_BRANCH: #if last is terminator then extract labels
                instr = all_blocks[block_index][-1]
                labels = instr["labels"]
                for label in labels:
                    if label not in natural_loop: #exit point from loop
                        #does li_instr does not dominate this block, return False
                        if def_block not in doms[label]:
                            return False
    return True


def var_used_block_list_from_loop(natural_loop, var_name, all_blocks):
    used_blocks_list = []
    for node in natural_loop[:-1]:
        block_index = get_block_index_from_name(node, all_blocks)
        for instr in all_blocks[block_index]:
            if "args" in instr and var_name in instr["args"]:
                if node not in used_blocks_list:
                    used_blocks_list.append(node)
    return used_blocks_list


def find_def_block_of_loop_invariant_instr(natural_loop, li_instr, all_blocks):
    for node in natural_loop[:-1]:
        block_index = get_block_index_from_name(node, all_blocks)
        for instr in all_blocks[block_index]:
            if li_instr == instr:
                return node
    return ""

def does_loop_have_pre_header(natural_loop, all_blocks):
    loop_header = natural_loop[0]
    preds = get_block_predecessors(loop_header, all_blocks)

    for pred in preds:
        if pred not in natural_loop and pred != DUMMY_EXIT_BLOCK and pred != DUMMY_ENTRY_BLOCK:
            return True
    return False

def get_pre_header_basic_block(loop_header):
    pre_header = []
    name_instr = {'name': PRE_HEADER}
    label_instr = {'label': PRE_HEADER}
    jmp_instr = {'labels' : [loop_header], 'op': 'jmp'}
    pre_header.append(name_instr)
    pre_header.append(label_instr)
    pre_header.append(jmp_instr)
    return pre_header

def insert_li_instr_in_block(li_instr, block, all_blocks):
    if block[-1]["op"] in JMP_OR_BRANCH:
        #insert at last but one instr of pred_block
        block.insert(-1, li_instr)
    else:
        block.append(li_instr)

def insert_li_instr_in_pred(li_instr, pred, all_blocks):
    pred_index = get_block_index_from_name(pred, all_blocks)
    pred_block = all_blocks[pred_index]
    #print("pred_block before", pred_block)
    if pred_block[-1]["op"] in JMP_OR_BRANCH:
        #insert at last but one instr of pred_block
        pred_block.insert(-1, li_instr)
    else:
        #insert at end of pred_block
        pred_block.append(li_instr)
    #print("pred_block after", pred_block)

def replace_jmp_header_to_pre_header(header, pre_header, pred, all_blocks):
    pred_index = get_block_index_from_name(pred, all_blocks)
    pred_block = all_blocks[pred_index]
    #edit label from header to pre_header
    labels = pred_block[-1]["labels"]
    for index in range(len(labels)):
        if labels[index] == header:
            labels[index] = pre_header
            break
    #print("pred lol", pred_block[-1])
    pred_block[-1]["labels"] = labels
    #print("pred lol after", pred_block[-1])
    

def get_blocks_part_of_loops(natural_loops):
    blocks_part_of_loops = []
    for loop in natural_loops:
        for block in loop:
            if block not in blocks_part_of_loops:
                blocks_part_of_loops.append(block)
    return blocks_part_of_loops

def insert_loop_invariant_in_pre_header(li_instr, natural_loop, all_natural_loops, all_blocks):
    loop_header = natural_loop[0]
    blocks_part_of_loops = get_blocks_part_of_loops(all_natural_loops)
    if does_loop_have_pre_header(natural_loop, all_blocks):
        preds = get_block_predecessors(loop_header, all_blocks)
        count = 0
        for pred in preds:
            if pred not in blocks_part_of_loops:
                count += 1
        #handle single pre_header, just insert the li_instr
        if count == 1:
            #print("hello")
            insert_li_instr_in_pred(li_instr, preds[0], all_blocks)
        #create a pre_header, with li_instr, and make all preds jump to this pre_header instead
        else:
            #print("varun\n")
            pre_header_basic_block = get_pre_header_basic_block(loop_header)
            #print(pre_header_basic_block)
            #insert_li_insrt in pre_header_basic_block
            insert_li_instr_in_block(li_instr, pre_header_basic_block, all_blocks)
            #print(pre_header_basic_block)

            #replace jmp label from header to pre_header
            for pred in preds:
                if pred not in natural_loop:
                    replace_jmp_header_to_pre_header(loop_header, PRE_HEADER, pred, all_blocks)
            #for block in all_blocks:
            #    print(block)
            #add pre_header_basic_block
            all_blocks.append(pre_header_basic_block)
            #for block in all_blocks:
            #    print(block)
    else:
        pre_header_basic_block = get_pre_header_basic_block(loop_header)
        insert_li_instr_in_block(li_instr, pre_header_basic_block, all_blocks)
        all_blocks.insert(0, pre_header_basic_block)

def delete_li_instr(li_instr, all_blocks):
    i_index = -1
    block_index = get_block_index_from_name(li_instr[1], all_blocks)
    for instr_index, instr in enumerate(all_blocks[block_index]):
        if li_instr[0] == instr:
            i_index = instr_index
            break
    all_blocks[block_index].pop(i_index)
                
def identify_loop_invariant_instrs(all_blocks):
    natural_loops = get_natural_loops(all_blocks)
    #print("natural_loops", natural_loops)
    for loop in natural_loops:
        result = identify_loop_invariants_instrs_per_loop(loop, all_blocks)
        for li_instr in result:
        #    if loop_invariant_instr_dominates_uses(li_instr[0], loop, all_blocks):
        #        print("yes dominates: ", li_instr)
        #    else:
        #        print("no it does not dominates: ", li_instr)
        #    if loop_invariant_instr_dominates_all_exits(li_instr[0], loop, all_blocks):
        #        print("yes dominates all exits: ", li_instr)
        #    else:
        #        print("it does not dominates all exits: ", li_instr)
            if loop_invariant_instr_dominates_uses(li_instr[0], loop, all_blocks) and\
                    loop_invariant_instr_dominates_all_exits(li_instr[0], loop, all_blocks):
    #            print("before all_blocks")
    #            for block in all_blocks:
    #                print(block)
                insert_loop_invariant_in_pre_header(li_instr[0], loop, natural_loops, all_blocks)
                #print("li_instr", li_instr)
                delete_li_instr(li_instr, all_blocks)
    #            print("\nafter all_blocks")
    #            for block in all_blocks:
    #                print(block)
    #print("------all blocks-------\n")
    #for block in all_blocks:
    #    print(block)


def get_all_instructions_in_natural_loop(natural_loop, all_blocks):
    all_instr = []
    for node in natural_loop[:-1]:
        node_index = get_block_index_from_name(node, all_blocks)
        node_block = all_blocks[node_index]
        for instr in node_block:
            if "name" in instr:
                continue
            all_instr.append(instr)
    return all_instr

def only_one_definition_of_arg_in_natural_loop(arg, natural_loop, all_blocks):
    instrs_in_natural_loop = get_all_instructions_in_natural_loop(natural_loop, all_blocks)
    def_arg_count = 0
    for instr in instrs_in_natural_loop:
        if "dest" in instr and arg == instr["dest"]:
            def_arg_count += 1
            single_def_instr = instr

    return def_arg_count == 1, single_def_instr

def check_if_loop_invariant_instr(input_instr, loop_invariant_instrs):
    for li_instr in loop_invariant_instrs:
        if li_instr[0] == input_instr:
            return True
    return False

def identify_loop_invariants_instrs_per_loop(natural_loop, all_blocks):
    loop_header = natural_loop[0]
    all_def_num_to_instrs(all_blocks)
    reaching_defs_in_data, reaching_defs_out_data = reaching_definitions_algo(all_blocks)
    #[li_instr, block_name]
    result_loop_invariant = []

    #preds not in natural loop
    preds_not_in_natural_loop = get_preds_not_in_natural_loop(loop_header, natural_loop, all_blocks)

    #get the reaching defs of all predecessors of preds of loop_header
    defs_pred_loop_header = []
    for pred in preds_not_in_natural_loop:
        defs_pred_loop_header.append(reaching_defs_out_data[pred])

    #flatten list of lists
    defs_pred_loop_header_list = list(set(itertools.chain(*defs_pred_loop_header)))
    #print("defs_pred_loop_header_list:", defs_pred_loop_header_list)

    for block_name in natural_loop[:-1]:
        #if block_name == loop_header:
        #    continue
        block = all_blocks[get_block_index_from_name(block_name, all_blocks)]
        for instr in block:
            loop_invariant = True
            if "dest" not in instr or "args" not in instr:
                continue
            if "dest" in instr:
                args = instr["args"]
                for arg in args:
                    #if definitions are not outside => the instr is not loop invariant
                    #print("instrl: ", instr)
                    if not are_definitions_outside_loop(defs_pred_loop_header_list, reaching_defs_out_data[block_name], arg):
                        #if the definitions of the arguments is not from outside the loop, then we check if there only a single
                        # definition for this loop, and that instr instruction itself is marked LI
                        is_only_one_def, single_def_instr = only_one_definition_of_arg_in_natural_loop(arg, natural_loop, all_blocks)
                        if not (is_only_one_def and check_if_loop_invariant_instr(single_def_instr, result_loop_invariant)):
                            loop_invariant = False
                            break
                
            if loop_invariant:
    #            print("loop_invariant_instr", instr)
                result_loop_invariant.append([instr, block_name])
    return result_loop_invariant

def dfs_find_natural_loops(all_blocks, curr_block, doms, visited, start_name, back_edge, natural_loop):
    global loop_found
    if curr_block == DUMMY_EXIT_BLOCK or curr_block == DUMMY_ENTRY_BLOCK:
        return
    successors = get_block_successors(curr_block, all_blocks)
    #print("curr_block, succ", curr_block, successors)

    for succ in successors:
        if succ == DUMMY_EXIT_BLOCK or succ == DUMMY_ENTRY_BLOCK:
            continue
        #print("visisted[succ: ", succ, visited[succ])
        temp = [curr_block, succ]
        #print("temp, back_edge:", temp, back_edge, natural_loop)
        if [curr_block, succ] == back_edge:
            #natural loop found
            loop_found = True
            natural_loop.append(succ)
            #print("inside temp, back_edge:", temp, back_edge, natural_loop)
            return
        if not visited[succ] and succ in doms:
            #print("visisted[succ], x: ", succ, visited[succ])
            visited[succ] = True
            natural_loop.append(succ)
            #print("natural_loop", natural_loop)
            dfs_find_natural_loops(all_blocks, succ, doms, visited, start_name, back_edge, natural_loop)
            if loop_found:
                return
            natural_loop.remove(succ)
            visited[succ] = False
        
def find_all_nodes_dominated_by_X(x, doms):
    nodes_dominated_by_X = []
    for key, value in doms.items():
        if x in value:
            nodes_dominated_by_X.append(key)
    return nodes_dominated_by_X


def post_dominators(all_blocks):
    #init out[entry] = 0, out[*] = U
    in_data = {}
    out_data = {}
    N = get_names_of_all_blocks(all_blocks) #list of all block names
    #print("N", N)

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

    #print("----------post dominators analysis-----------")
    #print("\n-------------in_data------------")
    #for in_info in in_data:
    #    print(in_info, in_data[in_info])
    #print("\n-----------out_data-----------")
    #for out_info in out_data:
    #    print(out_info, out_data[out_info])
    #print("\n\n")
    return out_data

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

    #print("----------dominators analysis-----------")
    #print("\n-------------in_data------------")
    #for in_info in in_data:
    #    print(in_info, in_data[in_info])
    #print("\n-----------out_data-----------")
    #for out_info in out_data:
    #    print(out_info, out_data[out_info])
    #print("\n\n")
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

def reaching_definitions_algo(all_blocks):
    #kill and gen set
    kill_set = {}
    gen_set = {}
    create_gen_kill_set(gen_set, kill_set, all_blocks)

    #init out[entry] = empty, out[*] = empty
    entry_block_name = all_blocks[0][0]["name"]
    in_data = {}
    out_data = {}
    #no definitions reach the starting bb
    out_data[DUMMY_ENTRY_BLOCK] = []
    for block in all_blocks:
        out_data[block[0]["name"]] = []

    #init worklist
    worklist = list(out_data.keys())
    worklist.remove(DUMMY_ENTRY_BLOCK)

    #iterate over worklist till not empty
    while worklist:
        #get first block from worklist
        curr_block_name = worklist.pop(0)

        out_data_copy = list(out_data[curr_block_name])

        #in[B] = U p a predecessor of B OUT[p], performing meet operation
        in_data[curr_block_name] = union_of_predecessors_out_data(curr_block_name, all_blocks, out_data)
        #out[B] = gen(B) U (IN[B] - kill(B))
        out_data[curr_block_name] = set_union(gen_set[curr_block_name], set_difference(in_data[curr_block_name], kill_set[curr_block_name]))

        #if out_data changed add its successors to worklist
        #as IN[succ] will change
        if out_data[curr_block_name] != out_data_copy:
            add_successors_curr_block_worklist(worklist, curr_block_name, all_blocks)

    #print("----------result of reaching definition-----------")
    #print("\n-------------in_data------------")
    #for in_info in in_data:
    #    print(in_info, in_data[in_info])
    #print("\n-----------out_data-----------")
    #for out_info in out_data:
    #    print(out_info, out_data[out_info])
    return in_data, out_data

def all_def_num_to_instrs(all_blocks):
    global DEF_COUNT
    global def_to_instr
    DEF_COUNT = 1
    for block in all_blocks:
        for index, instr in enumerate(block):
            if "dest" in instr:
                def_to_instr["d_" + str(DEF_COUNT)] = instr
                block[index]["def_num"] = "d_" + str(DEF_COUNT)
                DEF_COUNT += 1
    #for block in all_blocks:
    #    print(block)
    #for state in def_to_instr:
    #    print(state)
    #print("don\n")

def var_not_redefined(dest_var, index, block):
    while index < len(block):
        if "dest" in block[index] and block[index]["dest"] == dest_var:
            return False
        index += 1
    return True

def intersection_of_predecessors_out_data(curr_block_name, all_blocks, out_data):
    predecessors = get_block_predecessors(curr_block_name, all_blocks)
    intersection_predecessors_result = []

    if predecessors:
        #init intersection_predecessors_result with out_data of first predecesor
        intersection_predecessors_result = out_data[predecessors[0]]
        #iterate over all the predecessors and take intersection of out[pred]
        for pred in predecessors[1:]:
            intersection_predecessors_result = set_intersection(intersection_predecessors_result, out_data[pred])
    return intersection_predecessors_result

def union_of_predecessors_out_data(curr_block_name, all_blocks, out_data):
    predecessors = get_block_predecessors(curr_block_name, all_blocks)
    #print(curr_block_name, predecessors)
    union_predecessors_result = []

    if predecessors:
        #init union_predecessors_result with out_data of first predecesor
        union_predecessors_result = out_data[predecessors[0]]
        #iterate over all the predecessors and take union of out[pred]
        for pred in predecessors[1:]:
            union_predecessors_result = set_union(union_predecessors_result, out_data[pred])
    return union_predecessors_result

#used for reaching Definitions
def create_gen_kill_set(gen_set, kill_set, all_blocks):
    gen_set_with_var = {}
    for block_num, block in enumerate(all_blocks):
        defs_list_var = []
        defs_list = []
        for index, instr in enumerate(block):
            if "dest" in instr and var_not_redefined(instr["dest"], index+1, block):
                defs_list_var.append([instr["def_num"], instr["dest"]])
                defs_list.append(instr["def_num"])
        gen_set[block[0]["name"]] = defs_list
        gen_set_with_var[block[0]["name"]] = defs_list_var

    #iterate over gen sets which is block wise
    for gen_set_block_name in gen_set_with_var:
        #iterate over all blocks and instrs exepect the one from where current
        #gen set is being referredk
        killed_list = []
        for gen_def in gen_set_with_var[gen_set_block_name]:
            for block_num, block in enumerate(all_blocks):
                block_name = block[0]["name"]
                if block_name in gen_set_block_name:
                    continue
                #otherwise check if dest is same as the dest in gen
                for index, instr in enumerate(block):
                    if "dest" in instr and instr["dest"] == gen_def[1]:
                        killed_list.append(instr["def_num"])
        kill_set[gen_set_block_name] = killed_list

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
        form_blocks(func, output_json, index)
    output_json = json.dumps(output_json, indent=4)
    print(output_json)


if __name__ == "__main__":
    create_cfg()
