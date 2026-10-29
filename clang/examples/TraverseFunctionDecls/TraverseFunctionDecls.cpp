//===- TraverseFunctionDecls.cpp - PR001 function pragma report ------------===//
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include "clang/AST/ASTConsumer.h"
#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Frontend/FrontendPluginRegistry.h"
#include "llvm/Support/raw_ostream.h"
#include <map>
#include <memory>
#include <string>
#include <vector>

using namespace clang;

namespace {
class TraverseFunctionDeclsVisitor
    : public RecursiveASTVisitor<TraverseFunctionDeclsVisitor> {
  std::map<std::string, unsigned> FunctionRules;

public:
  bool VisitFunctionDecl(FunctionDecl *FD) {
    unsigned Rule = FD->getOverflowCheck();
    // A later prototype must not erase the flag recorded on the definition.
    FunctionRules[FD->getNameAsString()] |= Rule;
    return true;
  }

  void OutputAsCheckRules() const {
    for (const auto &Entry : FunctionRules)
      llvm::outs() << Entry.first << ": " << Entry.second << "\n";
  }
};

class TraverseFunctionDeclsConsumer : public ASTConsumer {
  TraverseFunctionDeclsVisitor Visitor;

public:
  void HandleTranslationUnit(ASTContext &Context) override {
    Visitor.TraverseDecl(Context.getTranslationUnitDecl());
    Visitor.OutputAsCheckRules();
  }
};

class TraverseFunctionDeclsAction : public PluginASTAction {
protected:
  std::unique_ptr<ASTConsumer>
  CreateASTConsumer(CompilerInstance &, llvm::StringRef) override {
    return std::make_unique<TraverseFunctionDeclsConsumer>();
  }

  bool ParseArgs(const CompilerInstance &,
                 const std::vector<std::string> &) override {
    return true;
  }
};
} // namespace

static FrontendPluginRegistry::Add<TraverseFunctionDeclsAction>
    X("traverse-fn-decls", "print whether each function is under overflowCheck");
