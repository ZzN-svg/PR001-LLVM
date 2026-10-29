# PR001 LLVM 实验源码

本目录包含完整 LLVM/Clang 源码及 PR001 第 7.1–7.4 节的实现。实验功能是在 AST 中记录 `#pragma overflowCheck` 对应的函数，并通过 `traverse-fn-decls` 插件打印 `函数名: 0/1`。

恢复基线为 LLVM 官方版本 `33ec67a140529cd1ae204e231dc718788c1bc95d`（Clang 24.0.0git）。本实验涉及的三个原始词法/Parser 文件与原工程的 Mac 基线备份逐字节一致。平台重置后，使用该兼容基线恢复完整工程，再补回保存的修改。原课程插件模板随服务器环境丢失，已按指导书恢复插件框架，并接入真实属性读取。

## 在 Linux 构建

进入本目录后执行：

```sh
cmake -S llvm -B build -G "Unix Makefiles" \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLVM_ENABLE_PROJECTS=clang \
  -DLLVM_TARGETS_TO_BUILD=X86 \
  -DLLVM_BUILD_EXAMPLES=ON \
  -DCLANG_BUILD_EXAMPLES=ON \
  -DLLVM_ENABLE_ASSERTIONS=ON \
  -DLLVM_ENABLE_RTTI=OFF \
  -DLLVM_ENABLE_EH=OFF
cmake --build build --target clang TraverseFunctionDecls -- -j2
```

已有工程请先备份，并沿用兼容的构建缓存；本轮服务器原缓存已随平台环境丢失。不要直接用其他 Clang 版本加载该插件，编译器和插件需要使用同一份修改后的头文件重新构建。

## 查看真实 0/1 输出

```sh
build/bin/clang -Xclang -load \
  -Xclang build/lib/TraverseFunctionDecls.so \
  -Xclang -plugin -Xclang traverse-fn-decls \
  -fsyntax-only pr001-tests/example.c
```

预期输出：

```text
foo0: 0
foo1: 0
foo2: 1
foo3: 0
```

`foo1` 只有声明，不消耗制导；`foo2` 是最近的函数定义；后续 `foo3` 不继承状态。`foo2` 定义后又出现的声明也不会把插件输出重置为 0。连续制导仍只选择最近的一个定义。

## 运行回归验证

```sh
python3 pr001-tests/verify.py \
  --clang build/bin/clang \
  --plugin build/lib/TraverseFunctionDecls.so \
  --work-dir /tmp/pr001-full-lab-tests
```

脚本实际加载插件，并逐例核对完整输出。它同时保存命令、退出码、标准输出、诊断和 `verification-result.json`，覆盖声明、定义、间隔声明、重复声明、连续制导、注释、宏、头文件、现有 pack pragma、普通 AST 和目标代码生成。

## 实现位置

- `clang/include/clang/Basic/TokenKinds.def`：pragma annotation 类型。
- `clang/lib/Parse/ParsePragma.cpp`：处理 pragma、消费指令行、构造并重新注入 annotation，注册与反注册 Handler。
- `clang/include/clang/Parse/Parser.h`、`clang/lib/Parse/Parser.cpp`：Handler 所有权和 annotation 消费入口。
- `clang/include/clang/Sema/Sema.h`、`clang/lib/Sema/SemaAttr.cpp`：初始化明确的待匹配状态和激活方法。
- `clang/lib/Sema/SemaDecl.cpp`：在函数定义完成时记录属性并清除状态，声明不走此入口。
- `clang/include/clang/AST/Decl.h`：默认 false 的属性和 public get/set 接口。
- `clang/examples/TraverseFunctionDecls/`、`clang/examples/CMakeLists.txt`：插件及构建接入。

Parser 使用当前版本的 `ConsumeAnnotationToken()` 消费 annotation；这与指导书的消费意图一致，并保留 annotation 的源码结束位置。所有现有通用 Lexer/Preprocessor 分派函数保持原实现。

本轮按用户后续指示优先完成全部实验代码；额外 Debug 构建、安装及 VSCode F5 环境验收暂缓。没有建立 Git 提交，也没有推送 GitLab。
