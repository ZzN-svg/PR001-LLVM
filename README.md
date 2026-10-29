# PR001 LLVM/Clang 实验

本仓库基于 LLVM 官方工程，包含编译原理 PR001 第 **7.1–7.4 节完整代码**。实验在 AST 中记录 `#pragma overflowCheck` 对应的函数，通过 `traverse-fn-decls` 插件输出 `函数名: 0/1`。

实验分支：`pr001-complete`。固定基线：[`33ec67a140529cd1ae204e231dc718788c1bc95d`](https://github.com/llvm/llvm-project/commit/33ec67a140529cd1ae204e231dc718788c1bc95d)，Clang 24.0.0git。

## 已验证结果

2026-10-30 在 Linux/GCC 11.4 环境完成 Clang 和插件构建（退出码 0）；**33 项实际回归测试全部 PASS，0 项 FAIL**。覆盖函数声明不消耗制导、最近函数定义、连续制导、宏、头文件、其他 pragma、普通 AST 和目标代码生成。

[逐项测试记录](pr001-records/verification-result.json) · [构建记录](pr001-records/build-results.json) · [验证说明](pr001-records/verification-summary.md) · [实验源码 SHA256](pr001-records/SOURCE-SHA256.json)

这些是已执行的实验环境验证记录；后续修改需重新运行测试。额外 Debug 构建、安装和 VSCode F5 环境验收暂缓。

## 获取与构建

```sh
git clone --single-branch --branch pr001-complete https://github.com/ZzN-svg/PR001-LLVM.git
cd PR001-LLVM
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
python3 pr001-tests/verify.py \
  --clang build/bin/clang \
  --plugin build/lib/TraverseFunctionDecls.so \
  --work-dir /tmp/pr001-full-lab-tests
```

必须使用本仓库同一版本编译出的 Clang 和插件。更完整的运行说明见 [README-PR001.md](README-PR001.md)。

## 实现导航

| 环节 | 文件 |
| --- | --- |
| 7.1 Handler 注册和生命周期 | [Parser.h](clang/include/clang/Parse/Parser.h)、[ParsePragma.cpp](clang/lib/Parse/ParsePragma.cpp) |
| 7.2 制导识别与 annotation 注入 | [TokenKinds.def](clang/include/clang/Basic/TokenKinds.def)、[ParsePragma.cpp](clang/lib/Parse/ParsePragma.cpp) |
| 7.3 Parser 消费、Sema 状态、函数属性 | [Parser.cpp](clang/lib/Parse/Parser.cpp)、[Sema.h](clang/include/clang/Sema/Sema.h)、[SemaAttr.cpp](clang/lib/Sema/SemaAttr.cpp)、[SemaDecl.cpp](clang/lib/Sema/SemaDecl.cpp)、[Decl.h](clang/include/clang/AST/Decl.h) |
| 7.4 AST 输出插件 | [TraverseFunctionDecls.cpp](clang/examples/TraverseFunctionDecls/TraverseFunctionDecls.cpp) |
| 回归脚本与示例 | [verify.py](pr001-tests/verify.py)、[example.c](pr001-tests/example.c) |

一个制导只匹配其后最近的一个函数**定义**，声明不消耗状态。插件读取真实的 `getOverflowCheck()`，定义后再次声明不会把 1 覆盖成 0。本实验实现 AST 标记与输出，不包含运行时算术溢出插桩。

## 来源与许可

学院环境重置后，以指定官方版本和保留的实验备份恢复。本次涉及的三个原始 Parser/词法文件与原工程基线逐字节一致；整份原工程修订号未记录，因此此版本属于兼容恢复基线。原课程插件框架按指导书重建并接入真实 getter。

[完整实验补丁](PR001-full.patch) 可应用于指定官方基线；先在新目录预检，避免覆盖活动工程。LLVM 的原始项目介绍保留在 [README-LLVM-upstream.md](README-LLVM-upstream.md)，许可见 [LICENSE.TXT](LICENSE.TXT)。
