# this script runs
# data flow analysis
# supported analysis
# 1 - reaching definitions
# 2 - liveness analysis
# 3 - available expressions
# 4 - very busy expressions

import sys
import json
import copy


TERMINATORS = "jmp", "br", "ret"
JMP_OR_BRANCH = "jmp", "br"
COMMUTATIVE_OPS = "add", "mul", "sub", "and", "or"
OPERATORS_WHICH_EVALUATE = "add", "mul", "sub", "div", "gt", "lt",\
        "ge", "le", "eq", "and", "or", "not"

FORWARD = "forward"
BACKWARD = "backward"
INTERSECTION = "intersection"
UNION = "union"
REACHING_DEFINITIONS = "1" 
LIVENESS = "2"
AVAILABLE_EXPRS = "3"
VERY_BUSY_EXPRS = "4"

DEF_COUNT = 1
def_to_instr = []

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

    #needed for reaching definitions
    all_def_num_to_instrs(all_blocks)
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

def all_def_num_to_instrs(all_blocks):
    global DEF_COUNT
    global def_to_instr
    for block in all_blocks:
        for index, instr in enumerate(block):
            if "dest" in instr:
                def_to_instr.append({"d_" + str(DEF_COUNT) : instr})
                block[index]["def_num"] = "d_" + str(DEF_COUNT)
                DEF_COUNT += 1

def print_all_instrs(all_blocks):
    for index, block in enumerate(all_blocks):
        print(index)
        for instr in block:
            print(instr)
        print("\n")

def var_not_redefined(dest_var, index, block):
    while index < len(block):
        if "dest" in block[index] and block[index]["dest"] == dest_var:
            return False
        index += 1
    return True

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

def union_of_successors_in_data(curr_block_name, all_blocks, out_data):
    successors = get_block_successors(curr_block_name, all_blocks)
    union_successors_result = []

    if successors:
        #init union_successors_result with out_data of first predecesor
        union_successors_result = out_data[successors[0]]
        #iterate over all the successors and take union of out[succ]
        for succ in successors[1:]:
            union_successors_result = set_union(union_successors_result, out_data[succ])
    return union_successors_result

def intersection_of_successors_in_data(curr_block_name, all_blocks, in_data):
    successors = get_block_successors(curr_block_name, all_blocks)
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

    if predecessors:
        #init intersection_predecessors_result with out_data of first predecesor
        intersection_predecessors_result = out_data[predecessors[0]]
        #iterate over all the predecessors and take intersection of out[pred]
        for pred in predecessors[1:]:
            intersection_predecessors_result = set_intersection(intersection_predecessors_result, out_data[pred])
    return intersection_predecessors_result

def union_of_predecessors_out_data(curr_block_name, all_blocks, out_data):
    predecessors = get_block_predecessors(curr_block_name, all_blocks)
    print(curr_block_name, predecessors)
    union_predecessors_result = []

    if predecessors:
        #init union_predecessors_result with out_data of first predecesor
        union_predecessors_result = out_data[predecessors[0]]
        #iterate over all the predecessors and take union of out[pred]
        for pred in predecessors[1:]:
            union_predecessors_result = set_union(union_predecessors_result, out_data[pred])
    return union_predecessors_result

def add_predecessors_curr_block_worklist(worklist, curr_block_name, all_blocks):
    predecessors = get_block_predecessors(curr_block_name, all_blocks)

    #if pred is not in predecessors only then add to worklist
    for pred in predecessors:
        if pred not in worklist and pred != "entry" and pred != "exit":
            worklist.append(pred)

def add_successors_curr_block_worklist(worklist, curr_block_name, all_blocks):
    successors = get_block_successors(curr_block_name, all_blocks)

    #if succ is not in successors only then add to worklist
    for succ in successors:
        if succ not in worklist and succ != "exit" and succ != "entry":
            worklist.append(succ)

#list all the expressions being evaulated in the program
def get_universal_set_exprs(all_blocks):
    expr_list = []
    for block in all_blocks:
        for instr in block:
            if "op" in instr and instr["op"] in OPERATORS_WHICH_EVALUATE \
                    and [instr["op"], instr["args"]] not in expr_list:
                expr_list.append([instr["op"], instr["args"]])
    return expr_list

def call_worklist_algo (all_blocks, analysis):
    in_data = {}
    out_data = {}

    if analysis == REACHING_DEFINITIONS:
       print("REACHING_DEFINITIONS")
       #OUT[ENTRY] = 0, OUT[*] = 0
       out_data["entry"] = []
       for block in all_blocks:
           out_data[block[0]["name"]] = []
       #kill and gen set
       kill_set = {}
       gen_set = {}
       create_gen_kill_set(gen_set, kill_set, all_blocks)
       worklist_algo(all_blocks, gen_set, kill_set, in_data, out_data, FORWARD, UNION)
    elif analysis == LIVENESS:
       print("LIVENESS")
       #IN[EXIT] = 0, OUT[*] = 0
       in_data["exit"] = []
       for block in all_blocks:
           in_data[block[0]["name"]] = []
       #use set and def set
       use_set = {}
       def_set = {}
       create_use_def_set(use_set, def_set, all_blocks)
       worklist_algo(all_blocks, use_set, def_set, in_data, out_data, BACKWARD, UNION)
    elif analysis == AVAILABLE_EXPRS:
       print("AVAILABLE_EXPRS")
       #OUT[ENTRY] = 0, OUT[*] = U
       out_data["entry"] = []
       U = get_universal_set_exprs(all_blocks)
       for block in all_blocks:
          out_data[block[0]["name"]] = U
        #kill and gen set
       e_gen_set = {}
       e_kill_set = {}
       create_e_gen_e_kill_set(e_gen_set, e_kill_set, all_blocks)
       worklist_algo(all_blocks, e_gen_set, e_kill_set, in_data, out_data, FORWARD, INTERSECTION)
    elif analysis == VERY_BUSY_EXPRS:
       print("VERY_BUSY_EXPRS")
       #in[EXIT] = 0, IN[*] = U
       in_data["exit"] = []
       U = get_universal_set_exprs(all_blocks)
       for block in all_blocks:
           in_data[block[0]["name"]] = U
       #kill and gen set
       kill_set = {}
       gen_set = {}
       create_gen_kill_set_verybusy_expr(gen_set, kill_set, all_blocks)
       worklist_algo(all_blocks, gen_set, kill_set, in_data, out_data, BACKWARD, INTERSECTION)

#general worklist_algo
def worklist_algo(all_blocks, gen_set, kill_set, in_data, out_data, direction, meet_operator):

     #init worklist
     if direction == FORWARD:
        worklist = list(out_data.keys())
        worklist.remove("entry")
     else:
        worklist = list(in_data.keys())
        worklist.remove("exit")

     #iterate over worklist till not empty
     while worklist:
         #get first block from worklist
         curr_block_name = worklist.pop(0)

         if direction == FORWARD:
            out_data_copy = list(out_data[curr_block_name])
         else:
             in_data_copy = list(in_data[curr_block_name])

         #apply meet operator
         if direction == FORWARD and meet_operator == UNION:
            #reaching definitions
            #in[B] = U p a predecessor of B OUT[p], performing meet operation
            in_data[curr_block_name] = union_of_predecessors_out_data(curr_block_name, all_blocks, out_data)
         elif direction == FORWARD and meet_operator == INTERSECTION:
            #available expressions
            #in[B] = intersection of p, predecessor of B OUT[P]
            in_data[curr_block_name] = intersection_of_predecessors_out_data(curr_block_name, all_blocks, out_data)
         elif direction == BACKWARD and meet_operator == UNION:
            #liveness analysis
            #out[B] = U s a successor of B IN[S]
            out_data[curr_block_name] = union_of_successors_in_data(curr_block_name, all_blocks, in_data)

         elif direction == BACKWARD and meet_operator == INTERSECTION:
            #very busy expressions
            #out[B] = ⋂ s a successor of B IN[S]
            out_data[curr_block_name] = intersection_of_successors_in_data(curr_block_name, all_blocks, in_data)

         #apply transfer function
         if direction == FORWARD:
            #reaching definitions and available expressions
            #out[B] = gen(B) U (IN[B] - kill(B))
            out_data[curr_block_name] = set_union(gen_set[curr_block_name], set_difference(in_data[curr_block_name], kill_set[curr_block_name]))
         else:
            #liveness and very busy expressions
            #in[B] = use(B) U (out[B] - def(B))
            in_data[curr_block_name] = set_union(gen_set[curr_block_name], set_difference(out_data[curr_block_name], kill_set[curr_block_name]))

         #forward, outchanges update sucessors
         #backward, inchange update predecessors
         if direction == FORWARD:
           if out_data[curr_block_name] != out_data_copy:
             add_successors_curr_block_worklist(worklist, curr_block_name, all_blocks)
         else:
           if in_data[curr_block_name] != in_data_copy:
             add_predecessors_curr_block_worklist(worklist, curr_block_name, all_blocks)

     print("*******WORKLIST-ALGO**********")
     print("\n********IN-DATA**********")
     for key, value in in_data.items():
        print(key, value)
     print("\n********OUT-DATA********")
     for key, value in out_data.items():
        print(key, value)

def available_exprs(all_blocks):
    #kill and gen set
    e_gen_set = {}
    e_kill_set = {}
    create_e_gen_e_kill_set(e_gen_set, e_kill_set, all_blocks)

    #init out[entry] = 0, out[*] = U
    exit_block_name = all_blocks[-1][0]["name"]
    in_data = {}
    out_data = {}
    U = get_universal_set_exprs(all_blocks)

    for block in all_blocks:
        out_data[block[0]["name"]] = U
    out_data[exit_block_name] = []

    #init worklist
    worklist = list(out_data.keys())

    #iterate over worklist till not empty
    while worklist:
        #get first block from worklist
        curr_block_name = worklist.pop(0)

        out_data_copy = list(out_data[curr_block_name])

        #in[B] = intersection of p, predecessor of B OUT[P]
        in_data[curr_block_name] = intersection_of_predecessors_out_data(curr_block_name, all_blocks, out_data)
        #out[B] = e_genB U (IN[B] - e_killB)
        out_data[curr_block_name] = set_union(e_gen_set[curr_block_name], set_difference(in_data[curr_block_name], e_kill_set[curr_block_name]))

        #if out_data changed add its successors to worklist
        #as IN[succ] will change
        if out_data[curr_block_name] != out_data_copy:
            add_successors_curr_block_worklist(worklist, curr_block_name, all_blocks)

    print("----------available expression analysis-----------")
    print("\n-------------in_data------------")
    for in_info in in_data:
        print(in_info, in_data[in_info])
    print("\n-----------out_data-----------")
    for out_info in out_data:
        print(out_info, out_data[out_info])
    print("\n\n")

#very_busy_expressions implementation
def very_busy_expressions_algo(all_blocks):

    #kill and gen set
    kill_set = {}
    gen_set = {}
    create_gen_kill_set_verybusy_expr(gen_set, kill_set, all_blocks)

    in_data = {}
    out_data = {}

    #universal set of expressions
    U = get_universal_set_exprs(all_blocks)

    #since intersection is meet operator we initialise in_data with U except for entry
    #at entry everything is 0 since no expressions are evaluated.
    #IN[ENTRY] = 0, IN[*] = U
    for block in all_blocks:
        in_data[block[0]["name"]] = U
    in_data[all_blocks[0][0]["name"]] = []

    #init worklist
    worklist = list(in_data.keys())

    #iterate over worklist till not empty
    while worklist:
        #get first block from worklist
        curr_block_name = worklist.pop(0)

        in_data_copy = list(in_data[curr_block_name])

        #out[B] = ⋂ s a successor of B IN[S]
        out_data[curr_block_name] = intersection_of_successors_in_data(curr_block_name, all_blocks, in_data)
        #in[B] = gen(B) U (out[B] - kill(B))
        in_data[curr_block_name] = set_union(gen_set[curr_block_name], set_difference(out_data[curr_block_name], kill_set[curr_block_name]))

        #if in_data changed add its predecessors to worklist
        #as out[predesscors] will change
        if in_data[curr_block_name] != in_data_copy:
            add_predecessors_curr_block_worklist(worklist, curr_block_name, all_blocks)

    print("----------result of very_busy_expressions analysis-----------")
    print("\n-------------in_data------------")
    for in_info in in_data:
        print(in_info, in_data[in_info])
    print("\n-----------out_data-----------")
    for out_info in out_data:
        print(out_info, out_data[out_info])
    print("\n\n")

def liveness_algo(all_blocks):
    #kill and gen set
    use_set = {}
    def_set = {}
    create_use_def_set(use_set, def_set, all_blocks)

    #init in[exit] = empty, out[*] = empty
    exit_block_name = all_blocks[-1][0]["name"]
    in_data = {}
    out_data = {}
    #all variables are dead after the last bb
    in_data[exit_block_name] = []
    for block in all_blocks:
        in_data[block[0]["name"]] = []

    #init worklist
    worklist = list(in_data.keys())

    #iterate over worklist till not empty
    while worklist:
        #get first block from worklist
        curr_block_name = worklist.pop(0)

        in_data_copy = list(in_data[curr_block_name])

        #out[B] = U s a successor of B IN[S]
        out_data[curr_block_name] = union_of_successors_in_data(curr_block_name, all_blocks, in_data)
        #in[B] = use(B) U (out[B] - def(B))
        in_data[curr_block_name] = set_union(use_set[curr_block_name], set_difference(out_data[curr_block_name], def_set[curr_block_name]))

        #if in_data changed add its predecessors to worklist
        #as out[predesscors] will change
        if in_data[curr_block_name] != in_data_copy:
            add_predecessors_curr_block_worklist(worklist, curr_block_name, all_blocks)

    print("----------result of liveness analysis-----------")
    print("\n-------------in_data------------")
    for in_info in in_data:
        print(in_info, in_data[in_info])
    print("\n-----------out_data-----------")
    for out_info in out_data:
        print(out_info, out_data[out_info])
    print("\n\n")

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
    out_data[entry_block_name] = []
    for block in all_blocks:
        out_data[block[0]["name"]] = []

    #init worklist
    worklist = list(out_data.keys())

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

    print("----------result of reaching definition-----------")
    print("\n-------------in_data------------")
    for in_info in in_data:
        print(in_info, in_data[in_info])
    print("\n-----------out_data-----------")
    for out_info in out_data:
        print(out_info, out_data[out_info])

def get_block_successors(curr_block_name, all_blocks):
    successors = []
    last_block_name = all_blocks[-1][0]["name"]
    last_block_last_instr = all_blocks[-1][-1]
    #if its last block, if last instr is ret or last instr is not (ret, jmp, br) fall through to exit, succ is exit
    if curr_block_name == last_block_name:
        if "op" not in last_block_last_instr or\
        last_block_last_instr["op"] == "ret" or last_block_last_instr["op"] not in TERMINATORS:
            successors.append("exit")
            return successors


    #calc curr_block index
    curr_block_index = -1
    for index, block in enumerate(all_blocks):
        if curr_block_name == block[0]["name"]:
            curr_block_index = index
            break

    #if last instr of curr_block is ret, succ is exit
    if all_blocks[curr_block_index][-1]["op"] == "ret":
        successors.append("exit")
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
        predecessors.append("entry")
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

#used for liveness analysis
def create_use_def_set(use_set, def_set, all_blocks):
    #calc def_set
    for block_num, block in enumerate(all_blocks):
        defs_list = []
        for index, instr in enumerate(block):
            if "dest" in instr:
                defs_list.append(instr["dest"])
        def_set[block[0]["name"]] = defs_list
    
    #calc use_set
    #used in B before definition in B
    for block_num, block in enumerate(all_blocks):
        use_list = []
        defs_list = []
        for index, instr in enumerate(block):
            #check if args was used before definition 
            if "args" in instr:
                args_list = instr["args"]
                for arg in args_list:
                    if arg not in defs_list and arg not in use_list:
                        use_list.append(arg)
            if "dest" in instr:
                defs_list.append(instr["dest"])
        use_set[block[0]["name"]] = use_list

    print("---------use_list---------")
    print(use_set)
    print("---------def_list---------")
    print(def_set)

#used for available expression, if expresion is valid outside the bb
#ie args of expression is changed in bb
def args_not_redefined_in_bb(index, block):
    args = block[index]["args"]
    for instr in block[index:]:
        if "dest" in instr and instr["dest"] in args:
            return False
    return True

#used for very busy expression, if expresion is evaulated and args
# are not modified before the evalation then expr can be hoisted before
# to the beginning of the block
def args_not_defined_before_expr(index, block):
    args = block[index]["args"]
    index -= 1
    while index >= 0:
        if "dest" in block[index] and block[index]["dest"] in args:
            return False
        index -= 1
    return True

#used for available expressions
#for calc kill_list
def check_in_uni(dest, universal_set):
    for expr in universal_set:
        if dest in expr[1]:
            return True
    return False

#used for available expressions
#for calc kill_list
def get_expr_killed_in_U(dest, universal_set):
    kill_list = []
    for expr in universal_set:
        if dest in expr[1]:
            kill_list.append(expr)
    return kill_list

#used for available expressions
#generate e_gen and e_kill set
def create_e_gen_e_kill_set(e_gen_set, e_kill_set, all_blocks):

    #e_gen_set to be the expressions generatd by B and args not modified within b after experssion
    # x = a + b, doest follow instrs likes a = etc, b = ... etc
    universal_set = get_universal_set_exprs(all_blocks)

    for block in all_blocks:
        expr_list = []
        kill_list = []
        for index, instr in enumerate(block):
            #add expression into gen_set if it the arguments are not changed
            #after calc of expression within the same basic block
            if "op" in instr and instr["op"] in OPERATORS_WHICH_EVALUATE \
                    and "dest" in instr and args_not_redefined_in_bb(index, block):
                expr_list.append([instr["op"], instr["args"]])

            if "dest" in instr and instr["op"] in OPERATORS_WHICH_EVALUATE:
                dest = instr["dest"]
                if check_in_uni(dest, universal_set):
                    #delete from universal all exprs which have dest arg
                    kill_list = set_union(kill_list, get_expr_killed_in_U(dest, universal_set))
        e_gen_set[block[0]["name"]] = expr_list
        e_kill_set[block[0]["name"]] = kill_list


#used for very busy expr
#calc gen and kill set
def create_gen_kill_set_verybusy_expr(gen_set, kill_set, all_blocks):

    universal_set = get_universal_set_exprs(all_blocks)

    #for gen set expressions a + b is evaulated before a, b are modified in the basic block
    for block_index, block in enumerate(all_blocks):
        gen_list = []
        kill_list = []
        for index, instr in enumerate(block):
            #add expr to gen_list is arg are not modified before expr is evaluated
            if "dest" in instr and instr["op"] in OPERATORS_WHICH_EVALUATE\
                    and args_not_defined_before_expr(index, block):
                gen_list.append([instr["op"], instr["args"]])


            #for a dest, check if this exists as an arg in U, if yes add that expr to kill set
            if "dest" in instr and instr["op"] in OPERATORS_WHICH_EVALUATE:
                dest = instr["dest"]
                if check_in_uni(dest, universal_set):
                    #delete from universal all exprs which have dest arg
                    kill_list = set_union(kill_list, get_expr_killed_in_U(dest, universal_set))    
        gen_set[block[0]["name"]] = gen_list
        kill_set[block[0]["name"]] = kill_list

    print("very_busy_expr, gen-kill-sets")
    print("gen_set", gen_set)
    print("kill_set", kill_set)

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

    if sys.argv[1] == REACHING_DEFINITIONS:
       call_worklist_algo(all_blocks, REACHING_DEFINITIONS)
    elif sys.argv[1] == LIVENESS:
       call_worklist_algo(all_blocks, LIVENESS)
    elif sys.argv[1] == AVAILABLE_EXPRS:
       call_worklist_algo(all_blocks, AVAILABLE_EXPRS)
    elif sys.argv[1] == VERY_BUSY_EXPRS:
       call_worklist_algo(all_blocks, VERY_BUSY_EXPRS)


if __name__ == "__main__":
    create_cfg()
