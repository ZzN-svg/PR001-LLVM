#!/usr/bin/env python3
"""Exercise PR001 through the rebuilt Clang and its actual AST plugin."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import textwrap


CASES = [
    ('no-pragma', 'int foo1(void) { return 0; }', {'foo1': 0}),
    ('single-definition', '''
        #pragma overflowCheck
        int foo1(void) { return 0; }
        int foo2(void) { return 0; }
    ''', {'foo1': 1, 'foo2': 0}),
    ('declaration-does-not-consume', '''
        #pragma overflowCheck
        int foo1(void);
        int foo2(void) { return 0; }
        int foo3(void) { return 0; }
    ''', {'foo1': 0, 'foo2': 1, 'foo3': 0}),
    ('prototype-and-definition', '''
        #pragma overflowCheck
        int foo1(void);
        int foo1(void);
        int foo1(void) { return 0; }
        int foo2(void) { return 0; }
    ''', {'foo1': 1, 'foo2': 0}),
    ('intervening-declarations', '''
        #pragma overflowCheck
        int prototype(void);
        typedef int Number;
        struct Record { int field; };
        union Value { int i; char c; };
        enum Color { RED, BLUE };
        int global;
        int (*callback)(void);
        _Static_assert(sizeof(Number) == sizeof(int), "int size");
        int selected(void) { return 1; }
        int next(void) { return 2; }
    ''', {'prototype': 0, 'selected': 1, 'next': 0}),
    ('independent-pragmas', '''
        #pragma overflowCheck
        int a(void) { return 0; }
        int b(void) { return 0; }
        #pragma overflowCheck
        int c(void) { return 0; }
        int d(void) { return 0; }
    ''', {'a': 1, 'b': 0, 'c': 1, 'd': 0}),
    ('consecutive-pragmas', '''
        #pragma overflowCheck
        #pragma overflowCheck
        int selected(void) { return 0; }
        int next(void) { return 0; }
    ''', {'selected': 1, 'next': 0}),
    ('pragma-at-eof-no-newline', '#pragma overflowCheck', {}),
    ('pragma-at-eof-after-definition', '''
        int earlier(void) { return 0; }
        #pragma overflowCheck
    ''', {'earlier': 0}),
    ('trailing-comment-and-blank-lines', '''
        #pragma overflowCheck // comment

        /* another comment */
        int selected(void) { return 0; }
        int next(void) { return 0; }
    ''', {'selected': 1, 'next': 0}),
    ('multiline-comment', '''
        #pragma overflowCheck /* comment
                                  continued */
        int selected(void) { return 0; }
    ''', {'selected': 1}),
    ('invalid-extra-tokens', '''
        #pragma overflowCheck unexpected tokens
        int first(void) { return 0; }
        int next(void) { return 0; }
    ''', {'first': 0, 'next': 0}),
    ('case-sensitive', '''
        #pragma overflowcheck
        int plain(void) { return 0; }
    ''', {'plain': 0}),
    ('same-name-macro', '''
        #define overflowCheck another_name
        #pragma overflowCheck
        int selected(void) { return 0; }
        int next(void) { return 0; }
    ''', {'selected': 1, 'next': 0}),
    ('pragma-operator', '''
        _Pragma("overflowCheck")
        int selected(void) { return 0; }
        int next(void) { return 0; }
    ''', {'selected': 1, 'next': 0}),
    ('macro-pragma-operator', '''
        #define SELECT_NEXT _Pragma("overflowCheck")
        SELECT_NEXT
        int selected(void) { return 0; }
        int next(void) { return 0; }
    ''', {'selected': 1, 'next': 0}),
    ('inactive-directive', '''
        #if 0
        #pragma overflowCheck
        #endif
        int plain(void) { return 0; }
    ''', {'plain': 0}),
    ('later-prototype-preserves-definition', '''
        #pragma overflowCheck
        int selected(void) { return 0; }
        int selected(void);
        int selected(void);
        int next(void) { return 0; }
    ''', {'selected': 1, 'next': 0}),
    ('prototype-must-not-mark-earlier-definition', '''
        int earlier(void) { return 0; }
        #pragma overflowCheck
        int earlier(void);
        int selected(void) { return 0; }
        int next(void) { return 0; }
    ''', {'earlier': 0, 'selected': 1, 'next': 0}),
    ('function-pointer-prototype', '''
        #pragma overflowCheck
        int (*factory(void))(void);
        int selected(int (*callback)(void)) { return callback(); }
        int next(void) { return 0; }
    ''', {'factory': 0, 'selected': 1, 'next': 0}),
    ('static-inline-definition', '''
        #pragma overflowCheck
        static inline int selected(void) { return 0; }
        int next(void) { return selected(); }
    ''', {'selected': 1, 'next': 0}),
    ('empty-declarations', '''
        #pragma overflowCheck
        ; ;
        int prototype(void);
        ;
        int selected(void) { return 0; }
        int next(void) { return 0; }
    ''', {'prototype': 0, 'selected': 1, 'next': 0}),
    ('existing-pack-pragma', '''
        #pragma overflowCheck
        #pragma pack(push, 1)
        struct Packed { char c; int value; };
        #pragma pack(pop)
        _Static_assert(sizeof(struct Packed) == 5, "pack preserved");
        int selected(void) { return 0; }
        int next(void) { return 0; }
    ''', {'selected': 1, 'next': 0}),
    ('other-pragmas-do-not-consume', '''
        #pragma overflowCheck
        #pragma GCC diagnostic push
        #pragma GCC diagnostic ignored "-Wunused-function"
        int selected(void) { return 0; }
        #pragma GCC diagnostic pop
        int next(void) { return 0; }
    ''', {'selected': 1, 'next': 0}),
    ('include-prototype', '''
        #pragma overflowCheck
        #include "prototype.h"
        int selected(void) { return 0; }
        int next(void) { return 0; }
    ''', {'header_decl': 0, 'selected': 1, 'next': 0}),
    ('include-definition', '''
        #pragma overflowCheck
        #include "definition.h"
        int next(void) { return 0; }
    ''', {'header_definition': 1, 'next': 0}),
    ('pragma-from-include', '''
        #include "selection.h"
        int selected(void) { return 0; }
        int next(void) { return 0; }
    ''', {'header_decl': 0, 'selected': 1, 'next': 0}),
    ('declaration-only-at-eof', '''
        #pragma overflowCheck
        int only_declared(void);
    ''', {'only_declared': 0}),
    ('empty-translation-unit', '', {}),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clang', type=Path, required=True)
    parser.add_argument('--plugin', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path)
    args = parser.parse_args()
    clang = args.clang.resolve()
    plugin = args.plugin.resolve()
    root = (args.work_dir or Path(tempfile.mkdtemp(prefix='pr001-tests-'))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    results = []

    def run(name, command, predicate, expected=None):
        try:
            p = subprocess.run([str(x) for x in command], capture_output=True,
                               text=True, timeout=120)
            (root / (name + '.stdout')).write_text(p.stdout)
            (root / (name + '.stderr')).write_text(p.stderr)
            ok = p.returncode == 0 and predicate(p)
            result = {'name': name, 'command': [str(x) for x in command],
                      'exit_code': p.returncode, 'status': 'PASS' if ok else 'FAIL'}
        except (OSError, subprocess.TimeoutExpired) as exc:
            result = {'name': name, 'command': [str(x) for x in command],
                      'status': 'FAIL', 'error': str(exc)}
        if expected is not None:
            result['expected_stdout'] = expected
        results.append(result)
        (root / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(name + ': ' + result['status'], flush=True)

    (root / 'prototype.h').write_text('int header_decl(void);\n')
    (root / 'definition.h').write_text('int header_definition(void) { return 0; }\n')
    (root / 'selection.h').write_text('#pragma overflowCheck\nint header_decl(void);\n')
    run('clang-version', [clang, '--version'], lambda p: 'clang version' in p.stdout)

    for name, source, expected in CASES:
        path = root / (name + '.c')
        path.write_text(textwrap.dedent(source).lstrip())
        output = ''.join(f'{key}: {expected[key]}\n' for key in sorted(expected))
        command = [clang, '-std=c11', '-Xclang', '-load', '-Xclang', plugin,
                   '-Xclang', '-plugin', '-Xclang', 'traverse-fn-decls',
                   '-fsyntax-only', path]
        run(name, command,
            lambda p, output=output, name=name:
                p.stdout == output and
                (name != 'invalid-extra-tokens' or 'extra tokens' in p.stderr),
            output)

    marked = root / 'single-definition.c'
    run('normal-pragma-syntax', [clang, '-std=c11', '-fsyntax-only', marked],
        lambda p: not p.stderr)
    run('ordinary-ast-with-pragma',
        [clang, '-std=c11', '-Xclang', '-ast-dump', '-fsyntax-only', marked],
        lambda p: 'FunctionDecl' in p.stdout and 'ReturnStmt' in p.stdout)
    obj = root / 'pragma.o'
    run('normal-pragma-code-generation', [clang, '-std=c11', '-c', marked, '-o', obj],
        lambda p: obj.is_file() and obj.stat().st_size > 0)

    counts = {status: sum(r['status'] == status for r in results)
              for status in ['PASS', 'FAIL']}
    summary = {'overall': 'PASS' if counts['FAIL'] == 0 else 'FAIL',
               'counts': counts, 'clang': str(clang), 'plugin': str(plugin),
               'results': results}
    (root / 'verification-result.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'overall': summary['overall'], 'counts': counts,
                      'records': str(root)}), flush=True)
    return 0 if counts['FAIL'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
