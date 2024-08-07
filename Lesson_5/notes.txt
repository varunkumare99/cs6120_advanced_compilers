Lesson 5
--------

Why give importance to analyising loops?
----------------------------------------
 - Loops affect the running time of program analyses. If a program does not contain any loops, we can
   obtain the answers to data-flow problems by making just one pass through the program.
 - eg: a foward data-flow problem can be solved by visiting all the nodes once, in topological order.


Dominators
----------

 - It is a relationship between two basic blocks
 - A CFG vertex A dominates vertex B iff:
   all paths from the entry to B include A.
   (It is impossible to "get to" B without first having run A at some point in the past)
   (A will definitely excute before B)
 - It is reflexive, hence a Block dominates itself.

Properties of the dom Relation
------------------------------
 - A key observation about the dominators is that if we take any acyclic path from the entry node to n,
   then all the dominators of n appear along this path, and moreover, they must appear in the same
   order this path.
   ex: Figure 9.38 of the dragon book
       conside two paths from node 1 to node 7
       path 1: 1->2->3->4->5->7
       doms:   1, 3, 4, 7

       path 2: 1->3->4->6->7
       doms:   1, 3, 4, 7
       
       as we can see above doms visiting order is same

 - Why this is so?
   Suppose there were one acyclic path P1 to n along which dominators a and b appear in that order and
   another path P2 to n, which b precedes a.
   entry...x..y....a..p..q....b..v....n (path p1)
   entry...w..e.......b..p..l....a...c..d....n (path p2)

   entry...x..y....a...c..d....n (we reached entry to n, with passing throught b)
   We could follow P1 to a and P2 to n, thereby avoiding b altogether. Thus, b would not really dominate n.

 - Thus doms are transitive
   if a dom b and b dom c, then a dom c.
 - doms are anti symmetric, it is never possible that a dom b and b dom a, if a not equal to b.
   since a dom b means a comes before b, and b dom a means b comes before a. Both of which are simultaneously 
   not possible.
 - Finally, it follows that each node n except the entry must have a unique immediate dominator, (as entry
   node has no other dominator apart from itself) - the dominator that appears closes to n along any acyclic
   path from the entry to n.


Dominator Tree
--------------

 - a data structure for keeping track of the dominator relation.
 - a node in a dominator tree dominates all the nodes below it.
 - the child of every node are nothing but the ones they immediately dominate.
 - the existence of dominator trees follows from a property of dominators: each node n has a unique immediate
   dominator m that is the last dominator of n on any path from the entry node to n. (it there was multiple 
   immediate dominators, means we could have reached n from either of those immediator dominators, which makes
   then not a dominator by definition)

Strict Dominates
----------------
 - A strictly dominates B iff: A dominates B and A not equals B. Not reflexive
   (that means B becomes below A in that Path)

Immediately Dominates
---------------------
 - A immediately B iff: A dominates B, and A does not strictly dominate any other node that strictly dominates B.
   (A is B's parent in the dominator tree)
   A dominates B -> B is below A
   A does not strictly dominate any other node that strictly dominates B -> There is no node between A and B.
   it is A followed by B.

Dominator Frontier
------------------
 - not dominated by the given node, but one hop away from the CFG
 - A dominance frontier is the set of nodes that are just "one edge away" from being dominated by a given node. Put differently,
   A's dominance frontier contains B iff A does not strictly dominate B, but A does dominate some predecessor of B.
 - A dominace frontier, imagine it like magnetic field of nodes which can be affected by A, nodes in the dominance frontier of A
   are one step away from this.

Post Dominates
--------------
 - A post-dominates B iff all paths from B to the exit include A.
   (impossible to reach from B to exit without passing by A in possible paths)
   (currently I'm executing B, and I know that exit block will executed => Block A will also be executed)


Strict Post-Domination
----------------------
 - A strictly Post-Dominates B iff: A post-dominates B and A not equals B.


An Algorithm For Finding Dominators
-----------------------------------

 dom = {} //map from vertices to sets of vertices (node to set of nodes it dominates)

 while dom is still changing:
    for vertex in CFG:
        dom[vertex] = {vertex} U ( ∩ dom[p] for p which is predecessor of vertex )

 - Worst case complexity of the algo is: O(n^2), outer loop n times and inner loop n times.
 - if we process the nodes in Reverse Post Order that is, if the nodes are in topological sort order
   we can achieve linear time, O(n) -> This is valid only for reducible CFG's

Data - flow algo for Finding Post - Dominators
----------------------------------------------
 - Principle: if s1, s2,.........sk are all successors of n, and d not equal to, then d post-dom n iff
              d post-dom pi, for each pi. (basically d post-dominates all the successors of n)
 - Direction: Backward
 - Data flow value: set of block names
 - Boundata: IN[EXIT] = 0 this is 0, so that the actual last block B, OUT[B] = 0, IN[B] = B U OUT[B] => B U 0 => B, 
             then the usual algo follows, intersection of successors of post-dominators
 - Meet operatior is intersection: (intersection of successors)
 - Initialization, IN[*] = N (all block names) this is required as we are doing intersection, either data
                   values stay the same or they reduce.
 - Equations:
        OUT[B] = ⋂ s which is successors of B, OUT[s]
        IN[B] = f(OUT[B]) = B(current block) U (⋂ s for s is successor of vertex)

Data - flow algo for computing dominators
-----------------------------------------
 - Principle: if p1, p2,......pk are all the predecessors of n, and d not equal to n, then d dom n iff
   d dom pi, for each pi. (basically d dominator all the predecessors of n)
 - Direction: Foward
 - Data flow values: sets of blocks
 - Boundary: OUT[entry] = entry (dominator is reflexive)
 - Meet operator is intersection: (intersection of dominators of predecessors)
 - Initialization, out[*] = all basic blocks
 - Equations: 
	IN[B] = ⋂ p which is predecessor of B, OUT[p]
        OUT[B] = f(IN[B]) = B(current block) U (⋂ p for p is predecessor of vertex)

Natural Loops
-------------
 - are strongly connected components(all blocks in the loop can be reached) 
   in the CFG with a single entry. (no multiple entry)
   eg: can enter for loop body only via for loop header.

Back Edge
---------
 - An edge A(tail) -> B(head)
   Where B dominates A, (any path from entry to A, must pass through B)
   
   Say you do a traversal, where you visit every vertex only once, start from start node. follow its neighbours,
   basically we passing through all forward edges, and once we remove them what we are left with is a back edge.
 - A back edge is a CFG edge whose target dominates its source.
   Ex: loop, 1 -> 2 -> 3 -> 4 -> 1 (this is a natural loop, with 1 as single point of entry)
       dom (1) = {1}
       dom (2) = {1, 2}
       dom (3) = {1, 2, 3}
       dom (4) = {1, 2, 3, 4}

       1 -> 2 (2 does not dominate 1)
       2 -> 3 (3 does not dominate 2)
       3 -> 4 (4 does not dominate 3)
       4 -> 1 (1 does dominates 4, ie target dominates the source, even though 4 -> 1, 1 is already visited before
               4 as 1 dominates 4)
       hence only 4 -> 1 is a backedge

Natural Loops
-------------
 - are strongly connected components(all blocks in the loop can be reached) 
   in the CFG with a single entry. (no multiple entry)
   eg: can enter for loop body only via for loop header.
 - For a backedge A(tail) -> B(header):
 - The smallest set of vertices L, including A and B such that for every v in L, either all the predecessors of
   v are in L (ie in the loop) or v = B (B is header, one entry point to a Natural loop, predecessor of B will be there
   which is not in L)
 - It must have a single-entry node, called the header. This entry node domintes all nodes in the loop, or it would not be the
   sole entry to the loop.
 - There must be a back edge that enters the loop header. Otherwise, it is not possible for the flow control to return to the header
   directly from the "loop" ie there really is no loop.

Reducible Control Flow
----------------------
 - In a reducible CFG, every backedge has a natural loop.

Algo For finding Back Edges
---------------------------
 - Do a dfs, if you are revisiting a node, then that is a back edge.

Reducible CFGs
--------------
 - are the CFG's are get from an imperative programming language for constructs like WHILE/BREAK/CONTINUE/IF
 - you need something like GOTO to make an irreducible CFG.
 - so if your programs doesn't GOTO, then you are CFG's are reducible.

Loop Invariant Code Motion
--------------------------
 - takes code outside the loop. So instead of executing it n times in the loop, it gets executed only once.
 - Natural loop has a single entry point, but that point can be reached by via many predecessors.
 - We can add a preheader, where all the precessors mentioned in above statement, point to preheader
   and preheader points to the single entry point of the loop. We are adding the preheader so that in case
   we find a loop invariant code, then it can be moved to the preheader.

How do you check whether a bril instruction is loop invariant wrt its containing natural loop?
----------------------------------------------------------------------------------------------
 - a statement x = a op b in an invariant in a loop, if a and b are not redefined after used in x.
 - Algo
   ----
   Iterate to convergence:
      For every instruction in a given loop:
            Mark it as loop invariant iff for all arguments x, either:
               1) All reaching definitions of x are outside the loop
                  //this means the arguments are updated/defined only outside the loop, hence it is invariant.
                  ex: outside the loop
                      a = 5
                      b = 10
                      inside the loop
                      a = a * b (this is not a loop invariant, since with reaching defintions , the definition of 'a' is inside thence not considered for loop invariant)
               or
               2) There is exactly one definitions, and it is already marked as loop invariant.
                  ex: a, b are outside loop
                  in loop:
                  x = a * b
                  y = x * b
                  in the first iteration x will be marked as loop invariant.
                  second iteration x is defined only once in loop which it self is invariant, and b is outside
                  y = x * b is also invariant.

                  basically we are treating loop invariant markers as having definitions outside the loop.

When should you move an instruction to the preheader?
-----------------------------------------------------
 - we can move the code which is an invariant in the loop to the preheader, provided all the vars are in scope outside as well(in preheader).
 
 - Algo (to move loop invariant code to preheader)
   ----
   - cond - 1 Definition domiates all its uses
     --------
     say we have in loop
     c = x + d
     x = a * b (which is a loop invariant)
     in the first iteration of the loop the definition of x which reaches c is from outside, while the subsequent are from the inside. Hence
     Hence unless definition x of dominates its (ie definition of x comes before its use, we cannot move it outside)

   - cond - 2 Dominates all loop exists
     --------
     Remember that loop can have many exit points. (ie Natual loop has single entry, but exit can be more than one)

     Domiantes all loop exits, so that it would have been computed anyway.
     ie it would be computed before exiting.

     if the instruction did not dominate all loop exit, means there exists an exit in the loop,
     basically we can get out of the loop with executin that instruction, and if we move it ouside the loop we would be updating that var, 
     which shouldn't be done.


     entry--->x=a*b----->e1--->y = b * c---e2----->entry
                          |                 |
                        exit               exit     
                          |                 |
                        z = y              

     say y = b * c is Loop invariant
     if we move it outside loop, if we exit the loop using e1, z will assigned b * c which is incorrect, since y = b * c will never be executed.
 
  - most loops, while and for can execute zero times hence, loop code which is invariant does not dominate the exit code.
  - do-while on the other hand executes atleast once, hence loop code code does dominate all exit points

  - That means for normal for/while loops are can't move loop invariant code to preheader, so how do we solve this?
    - you can remove cond - 2, if its destination variable is dead after the loop. 
      ie we do not have code like z = y(y is not used outside the loop)
    - even though by exiting using e1, we do not execute y = b * c, we move it outside loop, as y is not used after loop.
    - one thing to be careful of is that, it does not throw any exceptions, y = b / c (if c zero) by unoptmized code
      it wouldn't have thrown exception, but now it will as we moved it to preheader it can throw an exception as we are doing needless computation.

  - Speculative Optimization
    ------------------------
    If its possible to do extra work, guessing that that work, will be useful in the future.
    If it's possible to do wasted work that will never be used, then doing the optimization is speculative.
    basically we are trying to handle it for the common case, and increasing the work(when loop executes 0 times). However we need to be really sure that,
    that you don't introduce extra exceptions, like divide by zero.
