#!/bin/bash
# ════════════════════════════════════════════════════════════════
#  syntax_check.sh —— Objective-C 源码语法检查
#
#  背景：
#    真正编译这个 dylib 需要 macOS + Xcode + iOS SDK（走 GitHub Actions）。
#    但在 Linux 沙箱里，我们可以用 clang 的 -fsyntax-only 提前抓出
#    「漏分号 / 括号不配对 / @end 缺失 / 方法签名不匹配 / 类型未定义」
#    这类问题 —— 这些正是 CI 上最常见的失败原因。
#
#  原理：
#    1. clang 支持 -target arm64-apple-ios14.0，能启用 Apple 的
#       ObjC 特性（ARC、blocks、NS_ASSUME_NONNULL 等）
#    2. 缺 iOS SDK 头 → 用 checks/make_stubs.py 生成的最小 stub 顶替
#    3. glibc 头与 Apple target 不兼容（__nonnull 等）→ 用
#       checks/libc/ 下的极简 Apple 风格 libc 头顶替
#
#  用法：
#    ./checks/syntax_check.sh              # 检查全部源文件
#    ./checks/syntax_check.sh src/CVLog.m  # 检查指定文件
# ════════════════════════════════════════════════════════════════
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STUB="${CV_STUB_DIR:-/tmp/cvstub}"
LIBC="${CV_LIBC_DIR:-/tmp/cvlibc}"

# ── 0. 准备 stub 环境 ──
if [ ! -f "$STUB/Foundation/Foundation.h" ]; then
    echo "[syntax_check] 生成 stub 头 → $STUB"
    python3 "$ROOT/checks/make_stubs.py" >/dev/null
fi
if [ ! -f "$LIBC/stdio.h" ]; then
    echo "[syntax_check] 生成 libc stub → $LIBC"
    python3 "$ROOT/checks/make_libc.py" >/dev/null
fi

CLANG_INC="$(clang -print-resource-dir)/include"

# ── 1. 待检查的源文件 ──
if [ "$#" -gt 0 ]; then
    FILES=("$@")
else
    FILES=(
        "$ROOT/src/CVLog.m"
        "$ROOT/src/CoreVerify.m"
        "$ROOT/src/ui/CVOverlay.m"
        "$ROOT/src/ui/CVHostHook.m"
        "$ROOT/src/ui/CVVerifyPanel.m"
        "$ROOT/src/t3sdk/T3Verify.m"
    )
fi

# ── 2. 逐个检查 ──
PASS=0; FAIL=0
for f in "${FILES[@]}"; do
    [ -f "$f" ] || { echo "  ⚠️  跳过不存在的文件: $f"; continue; }
    rel="${f#$ROOT/}"
    out="$(clang -fsyntax-only -x objective-c \
        -target arm64-apple-ios14.0 \
        -nostdinc \
        -I"$LIBC" \
        -I"$CLANG_INC" \
        -I"$STUB" -I"$STUB/UIKit" -I"$STUB/Foundation" \
        -I"$ROOT/src" -I"$ROOT/src/ui" -I"$ROOT/src/t3sdk" \
        -fobjc-arc -fblocks \
        -Wno-everything \
        "$f" 2>&1)"
    if [ -z "$out" ]; then
        printf "  ✅ %s\n" "$rel"
        PASS=$((PASS + 1))
    else
        printf "  ❌ %s\n" "$rel"
        echo "$out" | sed 's/^/       /' | head -25
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "═══ 语法检查汇总 ═══"
echo "  通过 $PASS，失败 $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
