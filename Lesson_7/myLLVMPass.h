#ifndef LLVM_TRANSFORMS_myLLVMPASS_H
#define LLVM_TRANSFORMS_myLLVMPASS_H

#include "llvm/IR/PassManager.h"

namespace llvm {

class myLLVMPass : public PassInfoMixin<myLLVMPass> {
public:
  PreservedAnalyses run(Function &F, FunctionAnalysisManager &AM);
};

} // namespace llvm

#endif // LLVM_TRANSFORMS_myLLVMPASS_H
