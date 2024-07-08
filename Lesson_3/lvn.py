# this script runs
# lvn
# CSE
# commutative CSE
# copy propagation
# constant propagation
# constant folding
# dce
import sys
import json
import copy

TERMINATORS = "jmp", "br", "ret"
JMP_OR_BRANCH = "jmp", "br"
COMMUTATIVE_OPS = "add", "mul", "sub", "and", "or"
OPERATORS_WHICH_EVALUATE = "add", "mul", "sub", "div", "gt", "lt",\
        "ge", "le", "eq", "and", "or", "not"

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

    create_successors(all_blocks)

    #call lvn
    initiate_lvn(all_blocks)

    # call dce
    initiate_dce(all_blocks)

    # call constant folding
    initiate_constant_folding(all_blocks)

    # call dce
    initiate_dce(all_blocks)

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


def initiate_dce(blocks):
    if len(blocks) == 1:
        dce(blocks[0], True)
    else:
        index = 0
        while index < len(blocks):
            dce(blocks[index], False)
            index += 1

def initiate_lvn(blocks):
    index = 0
    while index < len(blocks):
        lvn(blocks[index])
        index += 1

def initiate_constant_folding(blocks):
    index = 0
    while index < len(blocks):
        constant_folding(blocks[index])
        index += 1

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

def can_delete_var_multi_blocks(var_name, start, block):
    for instr in block[start:]:
        if "dest" in instr:
            #if var is being used, ie in rhs don't delete
            if "args" in instr and var_name in instr["args"]:
                return False
            #redefinition delete, but dont delete for a = a + 1
            #taken care above
            if var_name == instr["dest"]:
                return True
    return False

def can_delete_var_single_block(var_name, start, block):
    for instr in block[start:]:
        #if var is being used, ie in rhs don't delete
        if "args" in instr and var_name in instr["args"]:
                return False
        #if var is redefined delete it
        if "dest" in instr and var_name == instr["dest"]:
                return True
    #var is neither in rhs or lhs hence can be deleted
    return True

def check_if_expr_in_lvn_table(table, expr):
    for element in table:
        if expr == element[1]:
            return True
    return False

def return_index_from_lvn_table(table, expr):
    for index, element in enumerate(table[::-1]):
        if expr == element[1]:
            return len(table) - 1 - index

def get_env_to_lvn_index(env_table, var):
    #print("get_env_to_lvn_index_table")
    for index, element in enumerate(reversed(env_table)):
        #print(len(env_table) - 1 - index, element)
        if element[0] == var:
            return len(env_table) - 1 - index
    return -1

def check_if_var_in_env(env_table, var):
    for index, element in enumerate(env_table):
        if element[0] == var:
            return True
    return False

def replace_var_with_new_name(block, new_name, orig_name, end, start):
    index = end
    while index >= start:
        if "dest" in block[index] and "const" !=  block[index]["op"]:
            args = block[index]["args"]
            if len(args) == 1 and block[index]["args"][0] == orig_name:
                block[index]["args"] = [new_name]
            elif len(args) == 2:
                new_arg1 = args[0]
                new_arg2 = args[1]
                if block[index]["args"][0] == orig_name:
                    new_arg1 = new_name
                if block[index]["args"][1] == orig_name:
                    new_arg2 = new_name
                block[index]["args"] = [new_arg1, new_arg2]
        index -= 1

def both_args_are_not_defined_in_block(block, index, env_to_lvn):
    if (len(block[index]["args"]) == 2) and \
            ((get_env_to_lvn_index(env_to_lvn, block[index]["args"][0])) == -1) \
            and ((get_env_to_lvn_index(env_to_lvn, block[index]["args"][1])) == -1):
                return True
    return False

def one_arg_is_defined_in_block(block, index, env_to_lvn):
    if (len(block[index]["args"]) == 2) and \
            (((get_env_to_lvn_index(env_to_lvn, block[index]["args"][0])) == -1) or
                    ((get_env_to_lvn_index(env_to_lvn, block[index]["args"][1])) == -1)):
                return True
    return False

def is_arg_defined_in_block(env_table, instr, arg_num):
    if get_env_to_lvn_index(env_table, instr["args"][arg_num]) != -1:
            return True
    return False

def get_tag_id_env_to_lvn(env_to_lvn, first_arg):
    for index, element in enumerate(reversed(env_to_lvn)):
        if element[0] == first_arg:
            return element[1]
    return -1
    
def lvn(block):
    lvn_table = []
    env_to_lvn = []
    tag_id = 0
    var_prefix = "lvn."
    var_count = 0
    for index, instr in enumerate(block):
       if "dest" in instr:
            cannonical_form = instr["dest"]
            #if we are reassigning a variable then first rename it
            #so that we can save its value
            if check_if_var_in_env(env_to_lvn, cannonical_form):
                get_env_index = get_env_to_lvn_index(env_to_lvn, cannonical_form)
                new_var_name = var_prefix + str(var_count)
                var_count += 1
                env_to_lvn[get_env_index][0] = new_var_name

                #if var name is present in lvn table then replace it with new name
                var_tag_id = env_to_lvn[get_env_index][1]
                if lvn_table[var_tag_id][2] == cannonical_form:
                    lvn_table[var_tag_id][2] = new_var_name

                #replace old var name with new name in the instruction
                block[env_to_lvn[get_env_index][2]]["dest"] = new_var_name
                start_index = env_to_lvn[get_env_index][2]

                #replace old var name with new name in other instruction where it is in args
                replace_var_with_new_name(block, new_var_name, cannonical_form, index, start_index)


            #handle call(with dest) instr, do copy propation if possible for args
            if "op" in instr and "call" == instr["op"]:
              if "args" in instr:
                args = instr["args"]
                args_list = []
                newExpr = [instr["op"]] #creating expr for lvn_table
                for each_arg in args:
                    env_to_lvn_index = get_env_to_lvn_index(env_to_lvn, each_arg)
                    if (env_to_lvn_index != -1):
                        arg_tag_id = env_to_lvn[env_to_lvn_index][1]
                        args_list.append(lvn_table[arg_tag_id][2]) #cannonical form
                        newExpr.append(lvn_table[arg_tag_id][2])
                    else:
                        args_list.append(each_arg)
                        newExpr.append(each_arg)
                    block[index]["args"] = args_list #cannonical home
               #expr for inserting in lvn_table
               #if newExpr is in lvn_table, copy propagate and replace call with id instr
                if check_if_expr_in_lvn_table(lvn_table, newExpr):
                    block[index]["op"] = "id"
                    existing_index = return_index_from_lvn_table(lvn_table, newExpr)
                    block[index]["args"] = [lvn_table[existing_index][2]] #get cannonical from
                    env_to_lvn.append([cannonical_form, existing_index, index])
                    del block[index]["funcs"]
                else:
                    lvn_table.append([tag_id, newExpr, instr["dest"], index])
                    env_to_lvn.append([instr["dest"], tag_id, index])
                    tag_id += 1

            #handle const instruction
            elif "const" == instr["op"]:
                expr = ["const", instr["value"]]

                #check if expr is in lvn table, only update env_to_lvn table
                if check_if_expr_in_lvn_table(lvn_table, expr):
                    lvn_index = return_index_from_lvn_table(lvn_table, expr)
                    env_to_lvn.append([cannonical_form, lvn_index, index])
                else:
                    lvn_table.append([tag_id, expr, cannonical_form, index])
                    env_to_lvn.append([cannonical_form, tag_id, index])
                    tag_id += 1

            #handle id operation
            elif "id" == instr["op"]:
                arg = instr["args"]
                env_to_lvn_index = get_env_to_lvn_index(env_to_lvn, arg[0])

                #local value is already present in lvn
                #hence only update env_to_lvn table
                if (env_to_lvn_index != -1):
                    arg_tag_id = env_to_lvn[env_to_lvn_index][1]
                    env_to_lvn.append([instr["dest"], arg_tag_id, index])
                    new_arg = ""
                    #if it is arg_tag_id is an id expr, new_arg is arg of id expr
                    #propagate that only if it is not defined in the block
                    if lvn_table[arg_tag_id][1][0] == "id" and not check_if_var_in_env(env_to_lvn, lvn_table[arg_tag_id][1][1][0]):
                        new_arg = lvn_table[arg_tag_id][1][1]#arg for id
                    #else take the cannonical form
                    else:
                        new_arg = lvn_table[arg_tag_id][2] #canonical form for const
                    new_arg_index = lvn_table[arg_tag_id][3] #canonical form instr index

                    #if block[new_arg_index] instr is a constant do constant propogation(const instr)
                    #else do copy propagation (id instr)
                    if "value" in block[new_arg_index]:
                        block[index]["op"] = "const"
                        block[index]["value"] = block[new_arg_index]["value"]
                        del block[index]["args"]
                    else:
                        block[index]["args"] = new_arg
                else:
                    lvn_table.append([tag_id, ["id", arg], instr["dest"], index])
                    env_to_lvn.append([instr["dest"], tag_id, index])
                    tag_id += 1
            #handle not instr, for copy propagation
            elif "not" == instr["op"]:
                arg = instr["args"]
                newExpr = [instr["op"], arg]

                #if newExpr is in lvn table perform copy propagation, only update env_to_lvn table
                #copy propagation, replace inst with "id" instruction
                if check_if_expr_in_lvn_table(lvn_table, newExpr):
                     block[index]["op"] = "id"
                     existing_index = return_index_from_lvn_table(lvn_table, newExpr)
                     block[index]["args"] = [lvn_table[existing_index][2]] #get cannonical from
                     env_to_lvn.append([cannonical_form, existing_index, index])
                else:
                     lvn_table.append([tag_id, newExpr, instr["dest"], index])
                     env_to_lvn.append([instr["dest"], tag_id, index])
                #print("lvn", lvn_table)

            elif both_args_are_not_defined_in_block(block, index, env_to_lvn):
                    #variables which are not defined we use their name itself instead of their tag id
                    #everywhere else we must use tag id
                    newExpr = [instr["op"], instr["args"][0], instr["args"][1]]

                    #sorting the args to handle commutative CSE for commutative_ops
                    if instr["op"] in COMMUTATIVE_OPS:
                        sublist = newExpr[1:]
                        sublist.sort()
                        newExpr[1:] = sublist

                    #if newExpr is in lvn table perform copy propagation, only update env_to_lvn table
                    #copy propagation, replace inst with "id" instruction
                    if check_if_expr_in_lvn_table(lvn_table, newExpr):
                        block[index]["op"] = "id"
                        existing_index = return_index_from_lvn_table(lvn_table, newExpr)
                        block[index]["args"] = [lvn_table[existing_index][2]] #get cannonical from
                        env_to_lvn.append([cannonical_form, existing_index, index])
                    else:
                        lvn_table.append([tag_id, newExpr, instr["dest"], index])
                        env_to_lvn.append([instr["dest"], tag_id, index])
                        tag_id += 1
            elif one_arg_is_defined_in_block(block, index, env_to_lvn):
                    #first arg defined in block
                    if is_arg_defined_in_block(env_to_lvn, instr, 0):
                        first_arg = instr["args"][0]
                        first_arg_tag_id = get_tag_id_env_to_lvn(env_to_lvn, first_arg)
                        #ex: newExpr = ["add", b, tag_id]
                        newExpr = [instr["op"], str(first_arg_tag_id), instr["args"][1]]

                        #sorting the args to handle commutative CSE for commutative_ops
                        if instr["op"] in COMMUTATIVE_OPS:
                            sublist = newExpr[1:]
                            sublist.sort()
                            newExpr[1:] = sublist

                        #if expr in lvn table do copy propagation, only update env_to_lvn table
                        #else update both lvn and env table
                        if check_if_expr_in_lvn_table(lvn_table, newExpr):
                            block[index]["op"] = "id"
                            existing_index = return_index_from_lvn_table(lvn_table, newExpr)
                            instrt["args"] = [lvn_table[existing_index][2]] #get cannonical from
                            env_to_lvn.append([cannonical_form, existing_index, index])
                        else:
                            lvn_table.append([tag_id, newExpr, instr["dest"], index])
                            env_to_lvn.append([instr["dest"], tag_id, index])
                            tag_id += 1
                    #second arg defined in block
                    else:
                        second_arg = instr["args"][1]
                        second_arg_tag_id = get_tag_id_env_to_lvn(env_to_lvn, second_arg)
                        #ex: newExpr = ["add", b, tag_id]
                        #newExpr = [block[index]["op"], block[index]["args"][0], str(env_to_lvn[get_env_to_lvn_index(env_to_lvn, block[index]["args"][1])][1])]
                        newExpr = [instr["op"], instr["args"][0], str(second_arg_tag_id)]

                        #sorting the args to handle commutative CSE for commutative_ops
                        if instr["op"] in COMMUTATIVE_OPS:
                            sublist = newExpr[1:]
                            sublist.sort()
                            newExpr[1:] = sublist

                        #if expr in lvn table do copy propagation, only update env_to_lvn table
                        #else update both lvn and env table
                        if check_if_expr_in_lvn_table(lvn_table, newExpr):
                            block[index]["op"] = "id"
                            existing_index = return_index_from_lvn_table(lvn_table, newExpr)
                            block[index]["args"] = [lvn_table[existing_index][2]] #get cannonical from
                            env_to_lvn.append([cannonical_form, existing_index, index])
                        else:
                            lvn_table.append([tag_id, newExpr, instr["dest"], index])
                            env_to_lvn.append([instr["dest"], tag_id, index])
                            tag_id += 1
            elif len(instr["args"]) == 2:
                arg1 = instr["args"][0]
                arg2 = instr["args"][1]
                arg1_tag_id = get_tag_id_env_to_lvn(env_to_lvn, arg1)
                arg2_tag_id = get_tag_id_env_to_lvn(env_to_lvn, arg2)
                #newExpr = [block[index]['op'], env_to_lvn[get_env_to_lvn_index(env_to_lvn, arg1)][1], env_to_lvn[get_env_to_lvn_index(env_to_lvn, arg2)][1]]
                #newExr = [add, 5, 4]
                newExpr = [instr["op"], arg1_tag_id, arg2_tag_id]

                #sorting the args to handle commutative CSE for commutative_ops
                if instr["op"] in COMMUTATIVE_OPS:
                    sublist = newExpr[1:]
                    sublist.sort()
                    newExpr[1:] = sublist

                #if expr in lvn, do copy progapation
                if check_if_expr_in_lvn_table(lvn_table, newExpr):
                    existing_index = return_index_from_lvn_table(lvn_table, newExpr)
                    env_to_lvn.append([cannonical_form, existing_index, index])
                    block[index]["op"] = "id" #change operation to id, we are doing CSE
                    block[index]["args"] = [lvn_table[existing_index][2]] #get cannonical from
                else:
                    #if different arguments but point to same const value
                    #then we use one variable instead, save registers 
                    if arg1 != arg2 and newExpr[1] == newExpr[2]:
                        arg2_env_index = newExpr[2]
                        cannonical_expr_val = lvn_table[arg2_tag_id][2]
                        newArgs = [cannonical_expr_val, cannonical_expr_val]
                        block[index]["args"] = newArgs
                        newExpr = [instr["op"], newExpr[1], newExpr[1]]
                        lvn_table.append([tag_id, newExpr, cannonical_form, index])
                    else:
                        lvn_table.append([tag_id, newExpr, cannonical_form, index])
                    env_to_lvn.append([cannonical_form, tag_id, index])
                    tag_id += 1

       #handle br instr, do copy propagation if possible
       elif "op" in instr and "br" == instr["op"]:
            arg = instr["args"]
            env_to_lvn_index = get_env_to_lvn_index(env_to_lvn, arg[0])
            if (env_to_lvn_index != -1):
                arg_tag_id = env_to_lvn[env_to_lvn_index][1]
                #if it is arg_tag_id is an id expr, new_arg is arg of id expr
                #propagate that only if it is not defined in the block
                if lvn_table[arg_tag_id][1][0] == "id" and not check_if_var_in_env(env_to_lvn, lvn_table[arg_tag_id][1][1][0]):
                    block[index]["args"] = lvn_table[arg_tag_id][1][1]#arg for id
                else:
                   block[index]["args"] = [lvn_table[arg_tag_id][2]] #cannonical home

       #handle ret instr, do copy propation if possible
       elif "op" in instr and "ret" == instr["op"]:
           if "args" in instr:
              arg = instr["args"]
              env_to_lvn_index = get_env_to_lvn_index(env_to_lvn, arg)
              if (env_to_lvn_index != -1):
                 arg_tag_id = env_to_lvn[env_to_lvn_index][1]
                 block[index]["args"] = lvn_table[arg_tag_id][2] #cannonical home

       #handle call(without dest) instr, print instr, do copy propation if possible for args
       elif "op" in instr and ("call" == instr["op"] or "print" == instr["op"]):
           if "args" in instr:
              args = instr["args"]
              args_list = []
              for each_arg in args:
                env_to_lvn_index = get_env_to_lvn_index(env_to_lvn, each_arg)
                if (env_to_lvn_index != -1):
                    arg_tag_id = env_to_lvn[env_to_lvn_index][1]
                    #if it is arg_tag_id is an id expr, new_arg is arg of id expr
                    #propagate that only if it is not defined in the block
                    if lvn_table[arg_tag_id][1][0] == "id" and not check_if_var_in_env(env_to_lvn, lvn_table[arg_tag_id][1][1][0]):
                        args_list.append(lvn_table[arg_tag_id][1][1][0])#arg for id
                    else:
                        args_list.append(lvn_table[arg_tag_id][2]) #cannonical home
                else:
                    args_list.append(each_arg)
              block[index]["args"] = args_list #cannonical home


def constant_folding(block):
    index = 0
    var_value_map = []
    for index, instr in enumerate(block):
       if "dest" in instr:
            if "const" == instr["op"]:
                entry = [instr["dest"], instr["value"]]
                add_var_map(var_value_map, entry)
            elif "id" == instr["op"] and (get_arg_val(var_value_map, instr["args"]) != -1):
                arg = instr["args"]
                instr["value"] = get_arg_val(var_value_map, arg)
                instr["op"] = "const"
            else:
                args = instr["args"]
                #evaluate the operation if both args in defined in block
                if (len(args) == 2) and get_arg_val(var_value_map, args[0]) != -1 \
                        and get_arg_val(var_value_map, args[1]) != -1 and \
                        can_evaluate(instr["op"], get_arg_val(var_value_map, args[0]), \
                        get_arg_val(var_value_map, args[1])):
                    arg1_val = get_arg_val(var_value_map, args[0])
                    arg2_val = get_arg_val(var_value_map, args[1])
                    result = calc_result(instr["op"], arg1_val, arg2_val)
                    block[index]["value"] = result
                    block[index]["op"] = "const"
                    del block[index]["args"]
                    entry = [instr["dest"], result]
                    add_var_map(var_value_map, entry)
                #calc not operation
                elif (len(args) == 1) and get_arg_val(var_value_map, args[0]) != -1:
                    arg1_val = get_arg_val(var_value_map, args[0])
                    result = calc_result(instr["op"], arg1_val, "")
                    block[index]["value"] = result
                    block[index]["op"] = "const"
                    del block[index]["args"]
                    entry = [instr["dest"], result]
                    add_var_map(var_value_map, entry)
       index += 1

def print_var_map(var_value_map):
    for index, var_val in enumerate(var_value_map):
        print(index, var_val)

def add_var_map(var_value_map, entry):
    for index, var_val in enumerate(var_value_map):
        if entry[0] == var_val[0]:
            del var_value_map[index]
            break
    var_value_map.append(entry)

def get_arg_val(var_value_map, arg):
    for var_val in var_value_map:
        if var_val[0] == arg:
            return var_val[1]
    return -1

def can_evaluate(op, arg1, arg2):
    if op in OPERATORS_WHICH_EVALUATE:
        if op == "div" and arg2 != 0:
            return True
        else:
            return False
        return True
    return False

def calc_result(op, arg1, arg2):
    if op == "add":
        return arg1 + arg2
    elif op == "sub":
        return arg1 - arg2
    elif op == "mul":
        return arg1 * arg2
    elif op == "div":
        return arg1 / arg2
    elif op == "eq":
        return arg1 == arg2
    elif op == "lt":
        return arg1 < arg2
    elif op == "gt":
        return arg1 > arg2
    elif op == "le":
        return arg1 <= arg2
    elif op == "ge":
        return arg1 >= arg2
    elif op == "not":
        return not arg1
    else:
        return -1



def dce(block, is_single):
    #single BB
    if is_single:
        while True:
            orig_block = copy.deepcopy(block)
            index = 0
            while index < len(block):
                if "dest" in block[index]:
                    var_name = block[index]["dest"]
                    if can_delete_var_single_block(var_name, index+1, block):
                        del block[index]
                index += 1
            if orig_block == block:
                break
    #multiple basic blocks
    else:
        while True:
            orig_block = copy.deepcopy(block)
            index = 0
            while index < len(block):
                if "dest" in block[index]:
                    var_name = block[index]["dest"]
                    if can_delete_var_multi_blocks(var_name, index+1, block):
                        del block[index]
                index += 1
            if orig_block == block:
                break

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
