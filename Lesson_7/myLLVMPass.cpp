#include "llvm/Transforms/Utils/myLLVMPass.h"
#include "llvm/IR/Function.h"
#include "llvm/Support/Debug.h"
#include "llvm/IR/Instruction.h"
#define DEBUG_TYPE "varun"
using namespace llvm;

PreservedAnalyses myLLVMPass::run(Function &F, FunctionAnalysisManager &AM) {
	for (auto& B : F) {
		for (auto& I : B) {
			if (I.getOpcode() == llvm::Instruction::FDiv) {
				errs() << "FDiv Instruction: " << I << "\n";
			}
			else {
				errs() << "normalOPs Instruction: " << I << "\n";
		       }	
		}
	}
	return PreservedAnalyses::all();
}
