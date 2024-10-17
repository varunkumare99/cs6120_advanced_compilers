BackEdge
--------

An edge A(tail) -> B(head), where B dominates A.

Natural Loops
-------------

A natural loop is the smallest set of vertices L including A and B such that, for every v in L, either all the predecessors of v are in L or v = B(you are can in edges outside of the loop).

LICM
----

ALGO
----
 Iterate to convergence:
   for every instruction in a given loop:
	make it as L.I IFF for all arguments in X, either:
        - all reaching definitions of X are outside the loop
        - There is exactly one definition, and it is already marked as loop invariant.
        why exactly one definition?
        If there are multiple definitions of a variable, the value may change across iterations, making the instruction not loop-invariant. Ex: say one of definition is taken only on else branch
        within a loop. Hence we want to be conservative and be 100% sure. Hence we do this.

is mainly two parts:
-------------------
- identify loop invariant instructions
- move LI to preheader

When to move L.I instructions to Preheaders IFF:
-----------------------------------------------
- Definition dominates all its uses.
- No other definitions of the same variable.
- Dominates all loop exists (so it would have been computed anyway)
  - Say you move an instruction to pre header, but this code is not executed on all exit points of the loop. But now that it is in preheader it is always executed. Which may throw exception.
    You have to sure you aren't doing needless computation without any affects.


Induction Variable Elimination
------------------------------
- mainly used in array indexing.
     
	for (let i = 0; i < 100; ++i) {
    		f(a[i]);
	}

       //in C terms
       for (let i = 0; i < 100; ++i) {
    		f(a + i * stride);
	}

       //after optimization
       let a_100 = a + 100 * stride;
       for (let a_i = a; a_i < a_100; a_i += stride) {
    		f(a_i);


Finding natural loops in CFG
----------------------------
- First find all back edges.
- Iterate over the back edges one by one.
- from each back edge find the loop header. Now from this header get all nodes dominated by this header. See if they form a loop with the back edge. If yes this is a natural loop.

INDUCTION VARIABLES
-------------------

for(j=......) {                                    t3 = &A
	//A[j] = 0                                 for (j = .....) {
        t1 = 4 * j;                                     *t3 = 0
        t2 = &A;                                        t3 = t3 + 4
        t3 = t1 + t2                               }
        *t3 = 0
}


