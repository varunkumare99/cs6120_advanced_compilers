Transfer function
-----------------

   Transfer Function decides backward or forward.
   -> IN[B] = f(OUT[B]) (backward data flow)
   -> OUT[B] = f(IN[B]) (forward data flow)


Data Flow Schemas on Basic Blocks
---------------------------------
- forward
  IN[B] = ⋃ p a predecessors of B OUT[P]

- backward
  OUT[B] = ⋃ s a successors of B IN[S]


Reaching Definitions
--------------------

 - Transfer functions
   ------------------
   d: u = v + w
   f_d(x) = gen_d ⋃ (x - kill_d)  
   gen_d -> d: u = v + w
   x -> input
   kill_d: union of all definitions killed by the individual statements
   gen_d: gen set contains all the definitions inside the block that are visible immediately after the block.
 
 - Control-Flow Equations
   ----------------------
   IN[B] = ⋃ p a predecessor of B OUT[P]
 
   P is a predecessor of B
   OUT[P] ⊆ IN[B]
   IN[B] = ⋃ p a predecessor of B OUT[P]

 - Iterative Algorithm for Reaching Definitions
   --------------------------------------------
   Each graph has an ENTRY and EXIT node.
   Since no definitions at present at ENTRY and ENTRY is empty
   Applying the transfer functions results in
   OUT[ENTRY] = 0

   For all other basic blocks including EXIT (exclude ENTRY)
 
   IN[B] = ⋃ p  a predecessor of B OUT[P]
   OUT[B] = gen_B ⋃ (IN[B] - kill_B)

   all basics blocks other than entry OUT[B] = 0

   Iterative Algo
   --------------
   OUT[ENTRY] = 0 //add entry block OUT[ENTRY] since foward
   for (each basic block B other than ENTRY) OUT[B] = 0
   //above for is needed for calculing IN[B]
   while (changes to ny OUT occur)
         for (each basic block B other than ENTRY) {
                IN[B] = ⋃ p a predecessor of B OUT[p] //since OUT[p] ⊆ IN[B] since if a definition reaches by atleast one path from OUT[p] it reaches IN[B]
                OUT[B] = gen_B U (IN[B] - kill_B)
         }

   Worklist Algo
   -------------
   OUT[ENTRY] = 0 //add entry block OUT[ENTRY] since forward
   for (each basic Block B other than ENTRY) OUT[B] = 0
   WorkList = all basic blocks + EXIT block

   while WorkList:
	top_block = WorkList.pop()
        IN[top_block] = ⋃ p a predecessor of OUT[p]
        //updated IN[top_block] is utilized only by OUT[top_block]
        //which is propagated below

        OUT[top_block] = gen_B ⋃ (IN[top_block] - def_B)
        //as this is foward analysis if OUT[top_block] changed all successors will change
        //this saves iterations compared to the iterative algo as only successors are added instead of repeating for all the blocks

        if OUT[top_block] changed updated its successors:
             WorkList.add(successors of OUT[top_block])

Live Variable Analysis
----------------------
  for a variable x and point p whether the value of x at p could be used along some path in flow graph starting at p. If so, we say x is live at p otherwise, x is dead at p.
  def_B - as the set of variables defined in B prior to any use of that variable in B.
          definitely are dead at the beginning of B.
      --> a = b + c -> b, c, y, z are live before this, since a is defined before use, x is not live since redefined on line 3
          b = b + a
          x = y + z
          ---------- x is live here

      --> a = a + r -> a, r, d are live before this, b is not live as b is defined before use
          b = r + d
          x = b + r

  use_B - as the set of variable whose values maybe use in B prior to any definition of the variable.
          must be considered live on entrace to block B.

  - Iterative Algorithm for Live Variable Analysis
    ----------------------------------------------
    Each graph has an ENTRY and EXIT node.
    Since no variable is live at the beginning of EXIT
    IN[EXIT] = 0
    OUT[EXIT] = 0 as well since vacious

    For all basic blocks B other than EXIT

    IN[B] = use_B ⋃ (OUT[B] - def_B)
    a variable is live coming into the block if either it is used before redefinition in the block or it is live coming out of the block
    and is not redefined in the block 
    
    OUT[B] = ⋃ s a successor of B IN[s] //since IN[s] ⊆ OUT[B] since even if one of sucessors has a variable as live it live at OUT[B] as well
    a variable is live coming out of a block if and only if it is live coming into one of its successors.

    
 - Notes
   -----
   1. For reaching definitions and liveness Union is the meet operator. In data flow data flows along the paths, and we care if any path with the 
      desired properties exit, rather than to be true in all paths.
   2. info flow in liveness is backward, since use of x at the a point P needs to transmitted to all points prior to P in execution path, so that
      we know at prior points that x's value is used.

  
   Iterative Algo
   --------------
   IN[EXIT] = 0 //nothing is live at exit block since no instructions, IN[EXIT] since backward
   for (each basic block B other than EXIT) IN[B] = 0
   //above for is neeed for calculation OUT[B]
   while (changes to IN occur)
       for (each basic block B other than EXIT) {
            OUT[B] = ⋃ s a successor of B IN[s]
            IN[B] = use_B ⋃ (OUT[B] - def_B)
       }
      

   Worklist Algo
   -------------
   IN[EXIT] = 0 //nothing is live at exit block since no instrutions, IN[EXIT] since backward
   for (each basic block B other than EXIT) IN[B] = 0
   //above for is need for calculation of OUT[B]
   Worklist = all basic blocks + ENTRY

   while Workslist:
       top_block = Workslist.pop()
       OUT[top_block] = ⋃ s a successor of top_block IN[S]
       //this is backward flow, OUT[top_BLOCK] is passed on to the IN[top_BLOCK] which is next
       
       IN[top_block] = use_B (OUT[B] - def_B)
       //this affects OUT of predecessors

       //as this is backward analysis IN[top_block] is updated
       //add all predecessorts of IN[top_block] to worklist
       if IN[top_block] changed updated its predecessors:
             WorkList.add(predecessors of IN[top_block])


Available Expressions
---------------------

   An expression x + y is available at a point p if every path from the entry node to p evaules x + y, and after the last such evaluation prior to reaching p, there
   are no subsequent assignmentes to x or y.
  
   block kills - expression x + y if it assigns x or y and does not subsequently recompute x + y.
   block generates - expression x + y if it definitely evaluates x + y and does not subsequently define x or y.

   The primary use of available-expression information is for detecting global common subexpressions.
   p ---------- expr S available
   x = y + z
   q ----------
   at point q
   1. add y + z to set S
   2. Delete from S any expression involving x.


   p ------- exprs S
   x = x + z
   q -------- expr x + z is not added to S as at q x is alread modified.


   e_gen_B -> expressions generated by B, and arguments of this expression are not modified in subsquent instrs in B
   e_kill_B -> set of expressions that are killed in U (universal set of expressions) by B.
   say B has x = y + z, all expressions in U with x as argument is killed by x is modified.

   OUT[ENTRY] = 0
   at exit of the ENTRY node, there are no available expressions

   IN[B] = ⋂ p a predecessor of B OUT[P]
   //this is a forward analysis, expressions reaches a point p, if the expressions is available along all paths leading to point p

   OUT[B] = e_gen_B ⋃ (IN[B] - e_kill_B)

   //as this a forward analysis expressions available at the end of the block, are those that are generated by B (e_gen_B) and
   //expressions already available at the beginning of the block which are not killed by B


   Iterative Algo
   --------------
   //add entry block, OUT[ENTRY] since forward
   OUT[ENTRY] = 0 

   //no expressions available at the exit of the ENTRY node
   //we initialize the OUT[ENTRY] = 0 while the remaining OUT[B] = U since, since at beginning of the program we haven't computed any expressions.
   //Hence, none are available. While for others we initialize to U as  there is scope to reduce.
   //Say B1 is the actual starting basic block which has code, and the last code block B4 also points to B1
   //Available expressions at IN[B1] = 0, since from OUT[B4] they might reach B1, but before starting the program no expressions are computed, 0.
   //If IN[B1] was U which means, before the program even begins the all expressions in U have been computed which is false.

   for (each basic block B other than ENTRY, EXIT is included) OUT[B] = U;

   while (changes to any OUT occur)
          for (each basic block B other than ENTRY) {
               IN[B] = ⋂ p a predecessor of B OUT[P];
               OUT[B] = e_gen_B ⋃ (IN[B] - e_kill_B);
           }


   Worklist Algo
   -------------
   //Add entry block, OUT[ENTRY] since forward
   OUT[ENTRY] = 0
   for (each basic block B other than Entry) OUT[B] = U;

   Worklist = all blocks except Entry

   while Worklist:
      top_block = Worklist.pop()

      IN[top_block] = ⋂ p a predecessor of B OUT[p]
      //as this is forward analysis is transferred to other blocks below
      OUT[top_block] = e_gen_B ⋃ (IN[B] - e_kill_B)
      //as this is forward analysis, if OUT[top_block] update all its successors


      if OUT[top_block] is changed
	Worlist add all successors of OUT[top_block]


   Notes
   -----
   - for reaching definitions, it is the solution with the smallest sets that corresponds to the definition of "reaching". We obtained that solution by
     starting with the assumption that nothin reached anywhere, and build up to the solution.
   - for available expression equations we want the solution with the largest sets of available expressions, so we start with an approximation that is
     too large and work down.
   - In case of available expressions, it is conservative(safe produces correct output) to produce a subset of the exact set of available expression. The
     argument for subsets being conservative is that our intended use of the information is to replace the computation of an available expressions by a 
     previously computed value.
   

   
Very Busy Expressions analysis
------------------------------

   Busy Expressions
   ----------------
   - An expression e is busy at a program point iff 
     - an evaluation of e exists along some path wi,........wj staring at program point wi
     - no operation of any operand of e exists before its evaluation along the path(eg: operands are unchanged)
    
   - If an expression is found to be busy at some program point then it is definitely going to be used in some
     path following that point.

   Very Busy Expressions
   ---------------------
   - An expression is very busy at some point if it will definitely be evaluated before it changes(eg: operands are unchanged)
     - At a program point wi, an expression is very busy if it is busy along all paths starting at wi.

   Optimization: code hoisting
   ---------------------------
   - If an expression is found to be very busy at Wi, we can move its evaluation to that node.
   - It can be used to perform code hoisting:
	- the computation of a very busy expr can be performed at the earliest point where it is busy.
        - it doesn't (necessarily) reduce time, but code space
   - Useful for loop invariant code motion
   - if an expression is invariant in a loop and is also very busy, hence must it known in future, evaluation outside the loop
     must be worthwhile.

   Equations
   ---------
   Kill_B = { a + b | either a or b defined before use of a + b in B }
   Gen_B = { a + b | a + b is used in B before any definitions of a, b }

   Transfer Equation
   -----------------
   OUT[B] = ⋂ IN[S] s, successors of B
   //This is a backward analysis, very busy if expression is evaluated on all paths
   //Hence we used intersection

   IN[B] = (OUT[B] - KILL[B]) ⋃ GEN[B]
   //This is a backward analysis, this included expr generated by this block, and
   //expressions from OUT[B] are included provided they are not killed by B


   Notes
   -----
   Very expr is similar liveness expression.

   Iterative Algo
   --------------
   //add exit block, IN[EXIT] since backward
   IN[EXIT] = 0

   //no expressions available at the exit of the ENTRY node
   //we initialize the OUT[ENTRY] = 0 while the remaining OUT[B] = U since, since at beginning of the program we haven't computed any expressions.
   //Hence, none are available. While for others we initialize to U as  there is scope to reduce.
   //Say B1 is the actual starting basic block which has code, and the last code block B4 also points to B1
   //Available expressions at IN[B1] = 0, since from OUT[B4] they might reach B1, but before starting the program no expressions are computed, 0.
   //If IN[B1] was U which means, before the program even begins the all expressions in U have been computed which is false.

   for (each basic block B other than EXIT) IN[B] = U;
   //as intersection is taken based on this

   while (changes to any OUT occur)
          for (each basic block B other than ENTRY) {
              OUT[B] = ⋂ IN[S] s, successors of B
              //This is a backward analysis, very busy if expression is evaluated on all paths
              //Hence we used intersection
              IN[B] = (OUT[B] - KILL[B]) ⋃ GEN[B]
              //This is a backward analysis, this included expr generated by this block, and
              //expressions from OUT[B] are included provided they are not killed by B
          }


    Workslist Algo
    --------------
    //Add EXIT block, IN[EXIT] since backward
    IN[EXIT] = 0
    
    for (each basic Block B other than EXIT) IN[B] = ⋃;

    Worklist = all blocks except EXIT;

    while Worklist:
       top_block = Worklist.pop(0);	
       
       OUT[top_block] = ⋂ IN[S] s, successors of B
       //This is a backward analysis and very busy if expression is evaluated on all paths
       //Hence we used intersection

       IN[top_block] = (OUT[top_block] - KILL[top_block]) ⋃ GEN[B]
       //This is a backward analysis, this included expr generated by this block, and
       //expressions from OUT[top_block] are included provided they are not killed by top_block

       if IN[top_block] is not changed:
 	  worklist add all predecessors as this is backward analysis


Range Analysis
--------------
    - What is the minimum integer value a variable x can take?
    - Direction = Forward, since value x can take depends on assignments before it.
    - Meet operator: min of integers, say values v1, v2 reach a node, then min(v1, v2) is the value beginning
      of the node.
    - Domain is from INT_MIN.....-1, -2, 0, 1, 2, 3.........INT_MAX as the height of the lattice of infinite converges to INT_MAX
      which is not of much use.
      This transfer function is as follows.
       in               in                   in
        |                |                    |
       x:=c            x:=x+/-c          if x > c goto label
        |                |                |             |
       out              out             out            out
                                       label          fallthrough
     out = c        out = in +/- c     out = in       out = in

     These don't converge because of infinite height of lattice

    - The choice of transfer function affects precision and running time of analysis
     
               in
                |
            if x > c goto   label
              | (true)        | (false)
              |               |
              |               |
          out label          out fallthrough
          = max(in, c + 1)   = max(in, INT_MAX)
