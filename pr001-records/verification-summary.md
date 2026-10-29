# 验证说明

验证日期：2026-10-30（Asia/Shanghai）。环境：Linux x86_64、GCC/G++ 11.4、CMake 3.22.1、Make 4.3、Clang 24.0.0git。Release、断言 ON、clang/X86/examples ON，构建并行度 2。

- CMake 配置：PASS，退出码 0。
- Clang 与 TraverseFunctionDecls 插件构建：PASS，退出码 0。
- 实际回归：33 PASS，0 FAIL。
- README 示例：PASS，输出 foo0: 0、foo1: 0、foo2: 1、foo3: 0。
- 修改文件空白检查：PASS。
- 已验证源码与保留的本地文件：逐文件 SHA256 一致。

JSON 中 `$SOURCE`、`$TEST_RECORDS` 和 `$INSTALL_PREFIX` 是对原测试环境路径的替换，命令参数和退出状态保留原记录。它们是历史实验验证结果，不代表 GitHub Actions 已执行。

额外 Debug、安装及 VSCode F5 环境验收暂缓。完整快照和源码包保留在本地；本仓库保留源码和适合公开查看的验证记录。
