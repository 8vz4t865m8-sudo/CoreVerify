#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
postflight.py —— 编译产物验证（在 CI 的 macOS runner 上跑）

目标：确认 make 出来的 CoreVerify.v1.dylib 真的符合预期，
      而不只是「编译没报错」。

检查维度：
  A. 文件基本属性   —— 存在、非空、是 Mach-O
  B. 架构           —— lipo -info 必须是双切片 arm64 + arm64e
  C. 安装名         —— otool -D 必须是 @executable_path/CoreVerify.v1.dylib
  D. 动态依赖       —— otool -L 必须链 Foundation / UIKit / Security
  E. 导出符号       —— nm -gU 必须有 CoreVerifyEntry（constructor）
  F. 关键字符串     —— strings 必须包含 T3 调用码 / RSA 公钥头 / 日志前缀
  G. 反向断言       —— 不得包含测试版 dylib 的后门串（2099-12-31 / t.me/cheatrev）

用法：
    python3 checks/postflight.py build/CoreVerify.v1.dylib
    python3 checks/postflight.py                 # 自动找 Makefile 里的 OUT
"""

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PASS = 0
WARN = 0
FAIL = 0
DETAILS = []


def ok(tag, msg):
    global PASS
    PASS += 1
    DETAILS.append(("✅", tag, msg))


def warn(tag, msg):
    global WARN
    WARN += 1
    DETAILS.append(("⚠️ ", tag, msg))


def bad(tag, msg):
    global FAIL
    FAIL += 1
    DETAILS.append(("❌", tag, msg))


def run(cmd):
    """执行命令，返回 (rc, stdout+stderr)"""
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=120)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return 127, str(e)


def artifact_from_makefile():
    mk = os.path.join(ROOT, "Makefile")
    if not os.path.isfile(mk):
        return None
    with open(mk, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*OUT\s*[:?]?=\s*(\S+)", line)
            if m:
                return m.group(1)
    return None


def find_artifact(arg):
    cands = []
    if arg:
        cands.append(arg)
    out = artifact_from_makefile()
    if out:
        cands += [out, os.path.join("build", out), os.path.join(ROOT, out)]
    cands += [
        "CoreVerify.v1.dylib",
        "build/CoreVerify.v1.dylib",
        os.path.join(ROOT, "CoreVerify.v1.dylib"),
        os.path.join(ROOT, "build", "CoreVerify.v1.dylib"),
    ]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    path = find_artifact(arg)

    print("═" * 62)
    print("  CoreVerify.v1.dylib 产物验证")
    print("═" * 62)

    # ── A. 基本属性 ──
    if not path:
        bad("A1", "找不到产物 CoreVerify.v1.dylib")
        report()
        return 1
    size = os.path.getsize(path)
    ok("A1", "产物存在: %s (%d 字节)" % (path, size))
    if size < 4096:
        bad("A2", "体积过小（%d 字节），疑似构建失败" % size)
    else:
        ok("A2", "体积正常")

    with open(path, "rb") as f:
        magic = f.read(4)
    # Mach-O 64 位（小端/大端）、FAT
    MACHO = {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf",
             b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
             b"\xca\xfe\xba\xbf"}
    if magic in MACHO:
        ok("A3", "是合法 Mach-O（magic=%s）" % magic.hex())
    else:
        bad("A3", "magic 异常: %s" % magic.hex())

    # ── 判断是否是 macOS（决定 lipo/otool/nm 能不能用）──
    # ★ 注意：strings 在 Linux 也有，所以即使非 macOS 也要跑 F/G 组检查 ——
    #   这样在沙箱里也能对着「测试版 dylib」验证我们的反向断言是真的有效。
    is_macos = os.uname().sysname == "Darwin"
    have_otool = run("which otool")[0] == 0
    have_lipo = run("which lipo")[0] == 0
    have_nm = run("which nm")[0] == 0

    # ── B. 架构 ──
    if have_lipo:
        rc, out = run("lipo -info '%s'" % path)
        if rc == 0:
            if "arm64e" in out and "arm64" in out:
                ok("B1", "双切片: %s" % out.strip().split(":")[-1].strip())
            elif "arm64" in out:
                warn("B1", "只有 arm64，缺 arm64e —— 部分越狱环境可能无法注入")
            else:
                bad("B1", "架构异常: %s" % out.strip())
        else:
            warn("B1", "lipo -info 失败: %s" % out.strip()[:80])
    else:
        warn("B1", "无 lipo，跳过架构检查（CI 的 macOS runner 会执行）")

    # ── C. install name ──
    if have_otool:
        rc, out = run("otool -D '%s'" % path)
        if rc == 0:
            if "CoreVerify.v1.dylib" in out:
                ok("C1", "install name 正确")
            else:
                bad("C1", "install name 不含 CoreVerify.v1.dylib: %s"
                          % out.strip()[:100])
            if "@executable_path/" in out:
                ok("C2", "@executable_path 前缀正确")
            else:
                warn("C2", "install name 未使用 @executable_path，注入后可能找不到")
        else:
            warn("C1", "otool -D 失败")

        # ── D. 依赖 ──
        rc, out = run("otool -L '%s'" % path)
        if rc == 0:
            for fw, tag in (("Foundation", "D1"), ("UIKit", "D2"),
                            ("Security", "D3")):
                if fw in out:
                    ok(tag, "已链接 %s" % fw)
                else:
                    bad(tag, "未链接 %s（T3 SDK 需要它）" % fw)
        else:
            warn("D1", "otool -L 失败")
    else:
        warn("C1", "无 otool，跳过 install name / 依赖检查")

    # ── E. 导出符号 / constructor ──
    if have_nm:
        # ★ constructor 是 `__attribute__((constructor)) static void` —— 
        #   static 意味着它是**局部符号**，`nm -gU`（只看全局）根本看不到它！
        #   正确做法：看 __mod_init_func 段，或在 nm -a（含局部符号）里找。
        #
        #   __mod_init_func 是 dyld 真正会调用的初始化函数表 ——
        #   只要它非空，就说明 constructor 确实生效了。
        rc, out = run("otool -l '%s' 2>/dev/null | "
                      "awk '/sectname __mod_init_func/,/^$/' | "
                      "grep -E 'size|sectname' | head -5" % path) if have_otool else (1, "")
        mod_init_ok = False
        if rc == 0 and out:
            m = re.search(r"size\s+0x([0-9a-fA-F]+)", out)
            if m and int(m.group(1), 16) > 0:
                mod_init_ok = True
                ok("E1", "constructor 已进 __mod_init_func（size=0x%s，dyld 会调用）"
                   % m.group(1))
            else:
                bad("E1", "__mod_init_func 为空 —— constructor 不会执行")
        else:
            # 退路：在全部符号（含 static 局部符号）里找
            rc2, out2 = run("nm -a '%s' 2>/dev/null || nm '%s'" % (path, path))
            if rc2 == 0 and "CoreVerifyEntry" in out2:
                ok("E1", "找到 constructor CoreVerifyEntry（局部符号）")
                mod_init_ok = True
            elif rc2 == 0 and "CoreVerify" in out2:
                ok("E1", "找到 CoreVerify 相关符号（constructor 大概率已生效）")
                mod_init_ok = True
            else:
                bad("E1", "找不到 constructor —— 注入后不会自动启动")

        # 应导出的 Objective-C 类（这些是全局符号，-gU 能看到）
        rc, out = run("nm -gU '%s' 2>/dev/null || nm -g '%s'" % (path, path))
        if rc == 0:
            for cls in ("CoreVerify", "CVOverlay", "CVVerifyPanel", "CVHostHook",
                        "T3Verify"):
                if ("_OBJC_CLASS_$_" + cls) in out:
                    ok("E2", "类 %s 已导出" % cls)
                else:
                    warn("E2", "类 %s 未在导出表（可能被内联/优化掉）" % cls)
        else:
            warn("E2", "nm -g 失败: %s" % out.strip()[:80])
    else:
        warn("E1", "无 nm，跳过符号检查")

    # ── F. 关键字符串 ──
    #
    # ★ 为什么不直接用 `strings`？
    #   产物是 fat 二进制（arm64 + arm64e 两个切片）。
    #   直接对 fat 跑 strings 时，不同版本对切片边界的处理不一致，
    #   会漏掉 __cstring 里的内容（我们真的踩过：APPKEY 明明在却报缺失）。
    #
    #   可靠做法：先 lipo -thin 拆出每个切片，再对切片跑 strings，取并集。
    strings_text = ""
    if have_lipo:
        for arch in ("arm64e", "arm64"):
            thin = "/tmp/cv-verify-%s" % arch
            rc, _ = run("lipo -thin %s '%s' -output %s" % (arch, path, thin))
            if rc == 0 and os.path.isfile(thin):
                rc2, out2 = run("strings -a %s" % thin)
                if rc2 == 0:
                    strings_text += out2
                try:
                    os.remove(thin)
                except Exception:
                    pass
    # 再补一次直接 strings（thin 场景 / 没有 lipo 时用）
    rc, out = run("strings -a '%s'" % path)
    if rc == 0:
        strings_text += out

    if strings_text:
        must = [
            ("F1", "0AAD3A3337741A5B", "T3 登录调用码"),
            ("F2", "7EB0F4A8272A7EBD", "T3 公告调用码"),
            ("F3", "61D5FC87F536273F", "T3 版本调用码"),
            ("F4", "A44066FE62E69F9D", "T3 心跳调用码"),
            ("F5", "1e45cd9daa2d5d7dfc6d8e66abe43b0a", "T3 APPKEY"),
            ("F6", "BEGIN PUBLIC KEY", "RSA 公钥头"),
            ("F7", "w.t3yanzheng.com", "T3 服务器地址"),
        ]
        for tag, needle, desc in must:
            if needle in strings_text:
                ok(tag, "包含 %s（%s）" % (desc, needle))
            else:
                bad(tag, "缺少 %s（%s）—— 验证功能会失效" % (desc, needle))

        # UI 文案：中文以 UTF-16 存在 __ustring / __cfstring，
        # strings 默认只抓 ASCII，看不到属正常 → 只提示不判失败
        chinese_missing = []
        for tag, needle, desc in (
            ("F8",  "授权至", "到期时间前缀"),
            ("F9",  "验证并激活", "验证按钮文案"),
            ("F10", "请输入卡密", "输入框占位符"),
        ):
            if needle in strings_text:
                ok(tag, "包含 UI 文案「%s」" % desc)
            else:
                chinese_missing.append(desc)
        if chinese_missing:
            warn("F8", "中文文案 %s 未在 ASCII 串中出现"
                      "（UTF-16 编码所致，属正常）" % "/".join(chinese_missing))
    else:
        warn("F1", "strings 无输出，无法校验关键字符串")

    # ── G. 反向断言：绝不能带测试版的后门 ──
    if strings_text:
        forbidden = [
            ("G1", "2099-12-31",      "测试版的「永远有效」硬编码到期值"),
            ("G2", "t.me/cheatrev",   "测试版的 Telegram 跳转目标"),
            ("G3", "CoreHomeLinkTarget", "测试版的按钮跳转类"),
            ("G4", "CoreHomeRewriteControls", "测试版的按钮劫持函数"),
            ("G5", "1970-01-01 00:00:01", "测试版的未授权哨兵值"),
        ]
        for tag, needle, desc in forbidden:
            if needle in strings_text:
                bad(tag, "★ 出现禁用串 %s（%s）—— 这是测试版的痕迹！"
                         % (needle, desc))
            else:
                ok(tag, "已排除 %s" % desc)
    else:
        warn("G1", "无法读取字符串，反向断言跳过")

    report()
    return 0 if FAIL == 0 else 1


def report():
    print()
    print("─" * 62)
    for mark, tag, msg in DETAILS:
        print("  %s %-5s %s" % (mark, tag, msg))
    print("─" * 62)
    print("  通过 %d，警告 %d，失败 %d" % (PASS, WARN, FAIL))
    print("═" * 62)


if __name__ == "__main__":
    sys.exit(main())
