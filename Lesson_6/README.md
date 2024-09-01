Static Single Assignment
------------------------
 - It is more convenient if every operation assigned to a unique name, in imperative languages.
 - Conversion from ordinary mutating form of program to single static assignment.
 - A program is defined to be in SSA form if each variable is a target of exactly one assignment
   statement in the program text
 - IR -> SSA -> do optimization -> back to IR

Phi node
--------
 - Selects between nodes.
 - Selects between n arguments and n labels.
 - We need to insert Phi nodes when converting to SSA, when different blocks use the same variable and assigned.

The SSA Philosophy
------------------

 - definitions == variables
   once converted to SSA, the definitions and variables becomes the same thing.
   x = 5; x will be same throughout.
   x = add y z, previously we kept of add y z separately and that it was mapped to x in so and so block
   But now with SSA we can treat x = add y z as one entity.

 - instructions == values
   x = add y z, in LVN, we treated add y z as a value.
   but now that whole x = add y z is nothing but a value.

 - arguments == data flow graph edges
   arguments/values, operators are nodes.
   x
       +    =   z
   y

   x = add y z --- 1
   a = mul x y --- 2 (here argument x can actually point to the whole instruction itself ie 1, in memory in case of llvm,
                      instructions are stored in memory and arguments are just pointers to those locations, without SSA
                      argument x, would refer to address of x. But now we refer to the instruction itself)

Where must phi nodes go?
------------------------
- Wherever there are two distinct paths containing distinct definitions of a variable.
- Generally, yo don't need a phi node in blocks dominated by definition.
  entry ----------> x = 2 ---------------> y = add x z
  x = 2, dominates y = add x z, henec we dont need a phi node here

  entry -----------> x = 2
                            -------------------> y = add x z (x = 2, x = 3 don't dominate y) here we need a phi node.
  entry -------------> x = 3
- at the dominance frontier
  Y is in dominance frontier of X iff
  - X dominates a predecessor of Y
  - X does not strictly dominate Y

An Algorithm For Converting to SSA
----------------------------------
To-do list:
 - Insert phi nodes.
 - Rename variables so every assignment gets a unique name

SSA Book
--------
- A program is defined to be in SSA form if each variable is a target of exactly one assignment
  statement in the program text
- SSA holds Referential Transparency
  ----------------------------------
  - since there is only a single definition of each variable in the program text, a variable's value is independent
    of its position in the program. 
  - since the meaning of an expression depends only on the meaning of its subexpressions and not on the order of evaluation
    or side effects of other expressions, more favorable for optimizations.
    non ssa                 ssa
    x = 1                   x1 = 1
    y = x + 1               y = x1 + 1
    x = 2                   x2 = 2
    z = x + 1               z = x2 + 1

- Phi nodes
  ---------
  The behavior of the φ-function is to select dynamically the value of the parameter associated with the actually executed
  control-flow path into b.
  - φ-functions are not directly executed in software, since the dynamic control-flow path leading to the φ-function is not
    explicitly encoded as an input to φ-function. This is fine, φ-functions are generally only used during static analysis
    of the program.

Dominance Property of SSA Form
------------------------------
 - In strict SSA form programs, definitions of variables dominate their uses:
   - if x is the i'th argument of a phi-function in block n, then the definition of x dominates the i'th predecessor of n.
   - if x is used in a non-phi statement in block n, then the definition of x dominates node n.

Dominance Frontier
------------------
- X strictly dominates Y
  -> x dominates y where y is not equal to x

- X does not strictly dominate Y
  -> x dominates y if y == x
  -> x does not dominate y if y not equals x

Where to insert PHI nodes
-------------------------
-> insert phi nodes wherever a node has multiple predecessors (brute force way)
-> We use dominance frontier, think of node as a magnet and the nodes it dominates like its magnetic field.
   - nodes in the dominance frontier of a node X, are those nodes which lie outside this magnetic field. Which means, nodes
     in the dominace frontier of X, will have mutiple defs reaching from paths apart from X, hence a PHI node needs to be 
     placed there.
   Why did they choose strict dominance for dominance frontier, why not just dominance?
   ------------------------------------------------------------------------------------
   - This is so that the node X itself can be included in the dominance frontier, if it was just dominance X obviously dominates X, 
     say X has multiple predecessors -> x needs PHI node -> but because it dominates itself we wouldn't include X in dominance
     frontier. Hence strictness property came into picture.

Dominance Frontier Criterion
----------------------------
 Dominance-Frontier Criterion
 ----------------------------
 - Whenever node x contains a definition of some variable a, then any node z in the dominance frontier of x needs a phi-function
   for a.
 Iterated dominance frontier
 ---------------------------
 - since a phi-function itself is a kind of a definition, we must iterate the dominance-frontier criterion until there are no nodes
   that need phi-functions.
   say a node has, print a (it has multiple pred, hence with phi node)
   before:
   	node X
   	print a
   later:
       node X
       a3 = phi(a1, a2)
       print a3
       
       Now we need to calculate the dominance frontier of this node, as we have added a new definition of a, ie a3.
       Hence we keep iterating calculating dominance frontier again, we keep adding phi nodes.

Algo for iterated dominance frontier
------------------------------------
 - DF[n] = DF_local[n] U {DF[c] | for all children c of n}
   DF_local[n]: the successors of that not strictly dominated b n
   DF[c]: nodes in the dominace frontier of c that are not strictly dominated by n

   say 
   DF[f] = d, h
   DF[d] = I
   DF[h] = e
   DF[e] = k, I
   add phi nodes as d, h, I, e, k. 
   loop through all nodes:
	find df of node, 
		keep add adding the nodes in successive df's till no more can be added

Inserting phi nodes (SSA-part1):
--------------------
 for v in vars:
   for d in Defs[v]: #blocks where v is assigned
     for block in DF[d]: #dominance frontier
       Add a phi-node to block,
          unless we have done so already,
       add block to Defs[v] (because it now writes to v),
       unless it's already in there

Dominance Property of SSA
-------------------------
- In SSA, definitions dominate uses,
  - If x_i is used in x <- phi(...,x_i...), then BB(x_i) dominates ith predecessor of BB(phi)
  - If x is used in y <- ...x..., the BB(x) dominates BB(y)

Renaming Variables (SSA-part2)
------------------------------

stack[v] is a stack of variables names (for every variable v)

def rename(block):
  for instr in block:
      replace each argument to instr with stack[old name]

      replace instr's destination with a new name
      #a global counter is used for every variable, which is always incremented for a new definition
      push that new name onto stack[old name]

  for s in block's successors:
      for p in s's phi-nodes:
          Assuming p is for a variable v, make it read from stack[v].

  for b in blocks immediately dominated by block:
    # That is, children in the dominance tree.
    rename(b)

  pop all names we just pushed onto the stacks


  - for each variable we maintain a stack for variable defs, why?
    because we are traversion the dom tree in a depth first search manner, hence using stack here.

  - replace each argument to instr with stack[old name] why?
    child needs use defintion in parent of dom tree which can be found in stack[old name]

  - replace instr's desitination with a new name and put it into stack[old_name], why?
    defintion -> give it a new philosopy of ssa hence add it to stack

  - for the blocks successors, if it has a phi instruction we update the var number and label, 
    because this is only place where the var version and path label can be known

  - We iterate over the blocks following the dom tree, why?
    in the dom tree the children are immediately by dominated parents. Hence the defintion in parent needs to used by children.


Prof Sorav Bansal SSA
---------------------

Translation to SSA
------------------
 - versioning values
 - so far in bril we have done versioning only for integer or boolean variables. But versioning can be done on any type. Examples: on array, any time a even a single element of the array is changed it needs to be copied. On I/O devices each state of the printer can be treated as new. Hence SSA can be done on anything.
 - Usually LLVM/GCC version scalars like ints, char etc.
 
 Pruned SSA
 ----------
 - Forego placing a phi function at a convergence point Z if no more uses of V in or after Z

Dominance Frontiers
-------------------
 - dominance frontier of a node X is a set of all nodes Y such that, X does not stricly dominate Y and X dominates some predecessor P os Y.
 - a node with an edge to itself will be in its dom frontier. Because, X does not strictly dominate X, but predecessors of X is X itself which it dominates. hence domF(x) = x.
 - keep going along a path from node X along as you keep dominating the nodes, and the first node you encounter in that path that you don't dominate will be in the dom frontier of X.

Computing Dominance Frontiers
-----------------------------
 - Naive Algorithm
   ---------------
   - To compute domF(x), perform DFS on CFG starting at X and stop at any node that is not strictly dominated by X(since first node enocountered which does not dominate is in domf)
   - Running time: O(n^2)
   
 - If Y belongs to domF(X) then Y _____ domF(idom(x)) (parent of x), we cant say it can be both, depends of CFG.
 - domFup(X) = { Y | Y E domF(X) and Y E domF(idom(X))} idom(X) parent of x
 - domFup(X) are the nodes in domF(X) that are passed up to domF(idom(X))
 - domFup(X) = { Y | Y E domF(x) and idom(x)(parent of x) doest not sdom Y }
 - idom(x) doest not sdom Y, means Y E domF(idom(x))
 - domFup(X) is the dom information that can be passed up.
 - domFlocal(x) = { Y | x sdom Y, and Y E succ(X) }
 - domFlocal are like immediate dominate frontiers of X.
 - domFlocal(X) are the nodes in domF(X) that are successors of X.
 - domFLocal(X) = { Y | X doest not sdom Y and Y E succ(X) }
 - domFlocal(X) is basically, which of my successors are in my dom frontier.
 - domF(X) = domF_local(X) U U domFup(Z), where Z belongs to children of(X) in domTree
 - either the node in domFrontier of X will from its immediate successor or it will come from the domfrrontier of children of
   X in the domTree, (dom info passed onto parent)
 - why children in domTree, since children in domTree we strictly dominate, else it could have been in domFrontier itself.
 - Either the node in the dominance frontier will be an immediate successor (not strictly dominated) or passed up from a node idominated by X(children in dom tree)

 - Efficient Algorithm
   -------------------
   for each X in a bottom up traversal of the dominator tree do
   	DF(X) = 0 //initilization to 0 at the beginning

   	for each Y ∊ Succ(X) do //successors of the CFG
   		if idom(Y) ≠ then X then DF(X) <- DF(X) U {Y} //if X doest not dominate it its successor, then add it to dom frontier or another way, Y is immediate dominated by another node apart from X.
   	end

   	for each Z ∊ children(X) do //why children of dom tree, because of children of dom are immediate dom by X, 
		for each Y ∊ DF(Z) do // Y is in dom frontier of Z, since we coming up in bottom up fashion, the dom frontiers of bottom nodes is already calculated.
			if idom(Y) ≠ X then DF(X) <- DF(X) U {Y} // if X does not immediate Y then add it to dom of X
	end
        // Z is a child of X in dom tree -> X immediate dominates Z, Y  ∊ DF(Z) -> Y is the first node not dominated by Z. to check if X dominates Y, it is enough if X immediately dominates Y, since
        // Z's are child of X in dom tree -> domf of Z, another path to reach Y, apart from Z exists, either Y should be immediately by X for it to dominated by X. else it is not dominated by X.
   end
