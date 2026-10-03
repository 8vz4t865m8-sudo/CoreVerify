#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoreVerify 编译前静态检查

在沙箱（无 iOS SDK）里能跑的部分，覆盖三类风险：
  A. 工程一致性    —— 文件名、install name、头注释版本号是否对得上
  B. 代码安全      —— 禁止出现已知会导致闪退/卡死的写法
  C. 坐标合理性    —— CVLayout.h 里的常量是否和实测值一致，
                      按钮矩形之间是否重叠（重叠会导致误屏蔽可点区域）

用法： python3 checks/preflight.py
返回： 0 = 全过；1 = 有 FAIL
"""

import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

PASS, WARN, FAIL = [], [], []


def ok(m):
    PASS.append(m)
    print("  \033[32m✓\033[0m %s" % m)


def warn(m):
    WARN.append(m)
    print("  \033[33m!\033[0m %s" % m)


def bad(m):
    FAIL.append(m)
    print("  \033[31m✗\033[0m %s" % m)


def strip_comments(src):
    """剥掉注释，避免注释里的示例代码被误判"""
    s = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    s = re.sub(r"//[^\n]*", "", s)
    return s


def read(p):
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════════════
print("\n\033[1m═══ A. 工程一致性 ═══\033[0m")
# ══════════════════════════════════════════════════════════════════════════

mk = read("Makefile") or ""
m = re.search(r"^\s*OUT\s*=\s*(\S+)", mk, re.M)
out_name = m.group(1) if m else None

if out_name == "CoreVerify.v1.dylib":
    ok("A1 产物名 = CoreVerify.v1.dylib")
elif out_name:
    warn("A1 产物名 = %s（期望 CoreVerify.v1.dylib）" % out_name)
else:
    bad("A1 Makefile 里找不到 OUT 定义")

if "@executable_path/%s" % out_name in mk:
    ok("A2 install name = @executable_path/%s" % out_name)
else:
    bad("A2 install name 与 OUT 不一致 —— insert_dylib 插进去后 dyld 找不到")

# 源文件清单是否都存在
srcs = re.findall(r"^\s+(src/\S+\.m)\s*\\?$", mk, re.M)
for s in srcs:
    if os.path.exists(s):
        ok("A3 源文件存在: %s (%d 行)" % (s, len(read(s).splitlines())))
    else:
        bad("A3 源文件缺失: %s" % s)

# 头文件是否都能被找到
for h in ["src/CVLayout.h", "src/CVLog.h",
          "src/ui/CVVerifyPanel.h", "src/ui/CVOverlay.h",
          "src/t3sdk/T3Verify.h"]:
    if os.path.exists(h):
        ok("A4 头文件存在: %s" % h)
    else:
        bad("A4 头文件缺失: %s" % h)

# T3 SDK 是否完整
t3m = read("src/t3sdk/T3Verify.m")
t3h = read("src/t3sdk/T3Verify.h")
if t3m and t3h:
    ok("A5 T3Verify SDK 已就位（.m %d 行 / .h %d 行）"
       % (len(t3m.splitlines()), len(t3h.splitlines())))
    for sym in ["initRsaWithLoginCode", "loginWithKami", "heartbeatWithKami",
                "getMachineCode"]:
        if sym in t3h:
            ok("A5b T3 接口存在: %s" % sym)
        else:
            bad("A5b T3 头文件缺少接口: %s" % sym)
else:
    bad("A5 缺少 T3Verify SDK 源文件")


# ══════════════════════════════════════════════════════════════════════════
print("\n\033[1m═══ B. 代码安全 ═══\033[0m")
# ══════════════════════════════════════════════════════════════════════════

core = read("src/CoreVerify.m") or ""
core_code = strip_comments(core)
panel = read("src/ui/CVVerifyPanel.m") or ""
panel_code = strip_comments(panel)
overlay = read("src/ui/CVOverlay.m") or ""
overlay_code = strip_comments(overlay)

# B1 ★ 不允许用 Keychain —— 自签环境 SecItemAdd = -34018
allm = core_code + panel_code + overlay_code
if re.search(r"SecItem(Add|CopyMatching|Delete|Update)", allm):
    bad("B1 出现 Keychain API SecItem* —— 自签环境下必然 -34018")
else:
    ok("B1 未使用 Keychain（SecItem*），自签安全")

# B2 ★ 不允许全量类遍历
if re.search(r"objc_(copy|get)ClassList", allm):
    bad("B2 出现 objc_copyClassList 全量遍历 —— 启动期会卡死")
else:
    ok("B2 未做全量类遍历")

def extract_balanced(code, start_idx):
    """
    从 start_idx（指向 '{'）开始，按大括号配平提取整段。
    比正则可靠得多 —— 正则的 [^}]* 会被内层 } 截断。
    """
    depth = 0
    i = start_idx
    while i < len(code):
        c = code[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return code[start_idx:i + 1]
        i += 1
    return code[start_idx:]


def calls_in_background(code, api):
    """
    判断 `api` 是否被包在 dispatch_async(...) 的 block 里调用。

    ★ 关键：Objective-C 里 GCD 的写法是
          dispatch_async(queue, ^{ ... });
      也就是 block 体在 **dispatch_async(...) 的括号内部**，
      不是在括号后面。所以要在括号范围内找 "^" 再找 "{"。
    """
    for m in re.finditer(r"dispatch_async\s*\(", code):
        open_paren = m.end() - 1

        # 配平，找到匹配的 ")"
        depth, i = 0, open_paren
        while i < len(code):
            if code[i] == "(":
                depth += 1
            elif code[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if i >= len(code):
            continue

        inner = code[open_paren + 1:i]      # dispatch_async 括号内部
        if "^" not in inner:
            continue

        # 在括号内部找 block 的 "{"，并按配平取体
        brace_rel = inner.find("{", inner.find("^"))
        if brace_rel == -1:
            continue
        brace_abs = open_paren + 1 + brace_rel
        body = extract_balanced(code, brace_abs)

        if re.search(r"\b%s\b" % re.escape(api), body):
            return True, body
    return False, ""


# B3 ★ 网络请求必须在子线程（T3 的 loginWithKami 是同步阻塞）
if re.search(r"loginWithKami", panel_code):
    found, _ = calls_in_background(panel_code, "loginWithKami")
    if found:
        ok("B3 面板里 loginWithKami 在 dispatch_async 子线程中调用")
    else:
        bad("B3 loginWithKami 没在子线程 —— 会卡住主线程（界面假死）")

if re.search(r"heartbeatWithKami", core_code):
    found, _ = calls_in_background(core_code, "heartbeatWithKami")
    if found:
        ok("B3b 心跳 heartbeatWithKami 在子线程")
    else:
        bad("B3b 心跳没在子线程 —— 每 60s 卡一次主线程")

# B4 ★ 跨线程 UI 安全
#    面板里有子线程验证 → 必须有回主线程的分发
if re.search(r"dispatch_async\s*\(\s*dispatch_get_main_queue", panel_code):
    ok("B4 面板里网络结果切回了主线程更新 UI")
else:
    bad("B4 面板在子线程验证但没切回主线程 —— 更新 UI 会崩")

#    覆盖层是纯 UI 对象，只在主线程创建/挂载即可（CoreVerify 里已保证）
if re.search(r"attachToWindow", overlay_code):
    ok("B4b 覆盖层通过 attachToWindow 挂载（由主线程调用）")
else:
    warn("B4b 覆盖层没有 attachToWindow 入口")

# B5 ★ 覆盖层的 hitTest 必须返回 nil（穿透）
m3 = re.search(r"-\s*\(UIView\s*\*\)\s*hitTest:\(CGPoint\)\w+\s*withEvent:", overlay_code)
if m3:
    brace = overlay_code.find("{", m3.end())
    body = extract_balanced(overlay_code, brace) if brace != -1 else ""
    if "return nil" in body:
        ok("B5 覆盖层 hitTest 有 return nil（触摸可穿透）")
    else:
        bad("B5 hitTest 没有 return nil —— 整层会吃掉所有触摸，宿主全废")
    if "return blk" in body or "return self" in body:
        ok("B5b hitTest 命中屏蔽块时返回了拦截视图")
else:
    bad("B5 覆盖层没有实现 hitTest:withEvent:")

# B6 ★ 验证成功后必须移除面板
if re.search(r"\[self\s+removeFromSuperview\]", panel_code):
    ok("B6 验证面板会 removeFromSuperview（'验证成功就没有了'）")
else:
    bad("B6 面板没有 removeFromSuperview —— 验证成功也关不掉")

# B7 ★ constructor 里不能做重活
m4 = re.search(r"__attribute__\(\(constructor\)\)(.*?)\n\}", core_code, re.S)
if m4:
    entry = m4.group(1)
    for pat, why in [(r"\bsleep\s*\(", "sleep 阻塞"),
                     (r"loginWithKami", "网络请求"),
                     (r"NSURLSession", "网络请求")]:
        if re.search(pat, entry):
            bad("B7 constructor 里有 %s" % why)
    else:
        ok("B7 constructor 里没有阻塞/网络操作")
    if "dispatch_async" in entry:
        ok("B7b constructor 把实际工作丢到了 dispatch_async")
else:
    warn("B7 没找到 constructor 入口")

# B8 系统进程守卫
if re.search(r"com\.apple\.", core_code):
    ok("B8 有系统进程守卫（跳过 com.apple.* bundle）")
else:
    bad("B8 没有系统进程守卫 —— 会被注入到系统 App 里")

# B9 位置更新（旋转/分屏）要有处理
if "relayout" in overlay_code:
    ok("B9 覆盖层有 relayout（尺寸变化时重算）")
else:
    warn("B9 覆盖层没有 relayout")

# B10 日志必须落地文件（自签下 NSLog 抓不到）
log_m = read("src/CVLog.m") or ""
if "Document" in log_m or "NSSearchPathForDirectoriesInDomains" in log_m:
    ok("B10 日志写入沙盒 Documents（get-task-allow=False 也能看）")
else:
    bad("B10 日志没落地文件 —— 自签环境下抓不到任何日志")


# ══════════════════════════════════════════════════════════════════════════
print("\n\033[1m═══ C. 坐标合理性 ═══\033[0m")
# ══════════════════════════════════════════════════════════════════════════

lay = read("src/CVLayout.h") or ""


def getf(name):
    m = re.search(r"%s\s*=\s*([-\d.]+)\s*;" % re.escape(name), lay)
    if not m:
        return None
    return float(m.group(1))


def getrect(name):
    # 兼容 `CVRectXxx = {{11.8, 318.4}, {98.6, 36.9}}` 与
    #      `CVRectXxx   = {{ 11.8, 318.4}, { 98.6, 36.9}}` 两种书写
    m = re.search(r"\b%s\s*=\s*\{\{\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\}\s*,"
                  r"\s*\{\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\}\s*\}" % re.escape(name), lay)
    if not m:
        return None
    return tuple(float(x) for x in m.groups())


# C1 设计基准
w, h = getf("CVDesignWidth"), getf("CVDesignHeight")
if w == 390.0 and h == 844.0:
    ok("C1 设计基准 390 × 844（与截图 1024×2216 比例 0.4621 吻合）")
else:
    bad("C1 设计基准不对：%s × %s" % (w, h))

# C2 到期条几何
bl, bt = getf("CVBarLeft"), getf("CVBarTop")
bw, bh = getf("CVBarWidth"), getf("CVBarHeight")
if None not in (bl, bt, bw, bh):
    ok("C2 到期条 x=%.1f y=%.1f w=%.1f h=%.1f" % (bl, bt, bw, bh))
    # 实测：x 24.4~366.4pt，y 233.8~268.1pt
    if abs(bl - 24.4) < 0.5 and abs(bt - 233.8) < 0.5:
        ok("C2a 起点与实测一致（24.4, 233.8）")
    else:
        bad("C2a 起点与实测不符（应为 24.4, 233.8）")
    if abs(bw - 342.0) < 1.0 and abs(bh - 34.3) < 0.5:
        ok("C2b 尺寸与实测一致（342.0 × 34.3）")
    else:
        bad("C2b 尺寸与实测不符（应为 342.0 × 34.3）")
    if abs(bl + bw - 366.4) < 1.0:
        ok("C2c 右边界 366.4pt，左右边距对称")
    else:
        warn("C2c 右边界 %.1f，实测 366.4" % (bl + bw))
    if abs(bl * 2 + bw - 390.0) < 1.5:
        ok("C2d 左右边距对称（距屏边各 %.1fpt）" % bl)
    else:
        warn("C2d 左右边距不对称")
else:
    bad("C2 到期条常量不全")

# C3 六个屏蔽块
blocks = {
    "查看公告": "CVRectAnnounce",
    "启动游戏": "CVRectLaunchGame",
    "提交工单": "CVRectTicket",
    "检查更新": "CVRectCheckUpd",
    "工单进度": "CVRectTicketProg",
    "激活续时": "CVRectRenew",
}
rects = {}
for label, const in blocks.items():
    r = getrect(const)
    if r:
        rects[label] = r
        ok("C3 %-6s x=%.1f y=%.1f w=%.1f h=%.1f" % ((label,) + r))
    else:
        bad("C3 %s 常量解析失败（%s）" % (label, const))

# C3b 实测值比对
expect = {
    "查看公告": (11.8, 318.4, 98.6, 36.9),
    "启动游戏": (279.2, 318.4, 98.6, 36.9),
    "提交工单": (11.8, 380.9, 100.5, 49.2),
    "检查更新": (277.3, 380.9, 100.5, 49.2),
    "工单进度": (11.8, 530.5, 100.2, 39.6),
    "激活续时": (277.6, 530.5, 100.2, 39.6),
}
mismatch = []
for label, (ex, ey, ew, eh) in expect.items():
    if label not in rects:
        continue
    ax, ay, aw, ah = rects[label]
    if abs(ax - ex) > 0.6 or abs(ay - ey) > 0.6 or \
       abs(aw - ew) > 0.6 or abs(ah - eh) > 0.6:
        mismatch.append("%s 实际(%.1f,%.1f,%.1f,%.1f) 期望(%.1f,%.1f,%.1f,%.1f)"
                        % (label, ax, ay, aw, ah, ex, ey, ew, eh))
if mismatch:
    for x in mismatch:
        bad("C3b 坐标偏差: %s" % x)
else:
    ok("C3b 六个屏蔽块坐标全部与截图实测一致")

# C4 ★ 屏蔽块之间不能重叠（重叠会误伤）
names = list(rects.keys())
overlap = []
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        a1, b1 = rects[names[i]], rects[names[j]]
        if (a1[0] < b1[0] + b1[2] and b1[0] < a1[0] + a1[2] and
                a1[1] < b1[1] + b1[3] and b1[1] < a1[1] + a1[3]):
            overlap.append("%s × %s" % (names[i], names[j]))
if overlap:
    for x in overlap:
        bad("C4 屏蔽块重叠: %s" % x)
else:
    ok("C4 六个屏蔽块互不重叠")

# C5 ★ 屏蔽块不能压到要放行的两个区域
keep = {"打开菜单": getrect("CVRectOpenMenu"), "音乐键": getrect("CVRectMusic")}
hit_keep = []
for kn, kr in keep.items():
    if not kr:
        bad("C5 %s 常量解析失败" % kn)
        continue
    ok("C5 %-5s 放行区 x=%.1f y=%.1f w=%.1f h=%.1f" % ((kn,) + kr))
    for bn, br in rects.items():
        if (br[0] < kr[0] + kr[2] and kr[0] < br[0] + br[2] and
                br[1] < kr[1] + kr[3] and kr[1] < br[1] + br[3]):
            hit_keep.append("%s(屏蔽) 压到 %s(放行)" % (bn, kn))
if hit_keep:
    for x in hit_keep:
        bad("C5b %s —— 会把要放行的按钮一起挡掉" % x)
else:
    ok("C5b 六个屏蔽块均未压到「打开菜单」和「音乐键」")

# C6 所有矩形必须在屏幕内
oob = []
for n, r in list(rects.items()) + list(keep.items()):
    if r is None:
        continue
    if r[0] < 0 or r[1] < 0 or r[0] + r[2] > 390.5 or r[1] + r[3] > 844.5:
        oob.append("%s (%.1f,%.1f,%.1f,%.1f)" % ((n,) + r))
if oob:
    for x in oob:
        bad("C6 越出屏幕: %s" % x)
else:
    ok("C6 所有矩形均在 390×844 屏幕内")

# C7 屏幕比例交叉验证
EXPECT_RATIO = 1024 / 2216.0
D = 390.0 / 844.0
if abs(EXPECT_RATIO - D) < 0.001:
    ok("C7 截图 1024×2216 比例 %.4f 与 390:844 比例 %.4f 吻合（scale=%.4f）"
       % (EXPECT_RATIO, D, 1024 / 390.0))
else:
    bad("C7 截图比例与设计基准不符：%.4f vs %.4f" % (EXPECT_RATIO, D))

# C8 面板/覆盖层尺寸自适应
if "scale" in overlay_code and ("/ CVDesignWidth" in overlay_code or
                                "/CVDesignWidth" in overlay_code):
    ok("C8 覆盖层按屏幕宽度等比缩放")
else:
    warn("C8 覆盖层没有等比缩放 —— 换机型会错位")

# C9 安全区偏移处理
if "safeAreaInsets" in overlay_code:
    ok("C9 覆盖层处理了安全区偏移")
else:
    warn("C9 覆盖层未处理安全区偏移")


# ══════════════════════════════════════════════════════════════════════════
print("\n\033[1m═══ E. 到期时间「直改优先 / 覆盖兜底」 ═══\033[0m")
# ══════════════════════════════════════════════════════════════════════════
#
#  用户要求原文：
#    「如果可以直接hook掉原宿主的到期时间显示真实的不行就覆盖掉显示真实的」
#
#  所以必须满足：
#    1. 存在 CVHostHook（直改方案）
#    2. CoreVerify.m 里是「先 hook，失败才覆盖」
#    3. 覆盖层在 hook 成功时不重复画胶囊（否则会出现两个到期时间）
#
hook_m = read("src/ui/CVHostHook.m") or ""
hook_h = read("src/ui/CVHostHook.h") or ""

if hook_m and hook_h:
    ok("E1 CVHostHook 直改模块就位（.m %d 行）" % len(hook_m.splitlines()))
    for sym, desc in (("applyExpiryText", "直接改写宿主标签"),
                      ("startKeepAliveWithExpiry", "防宿主回写守护"),
                      ("locateExpiryLabel", "标签定位")):
        if sym in hook_m:
            ok("E1b 提供能力：%s" % desc)
        else:
            bad("E1b 缺少能力：%s（%s）" % (desc, sym))
else:
    bad("E1 缺少 CVHostHook 模块")

# E2 ★ 优先级顺序：必须先 hook 再覆盖
if "CVHostHook applyExpiryText" in core and "attachToWindow" in core:
    i_hook = core.find("CVHostHook applyExpiryText")
    i_ovl = core.find("attachToWindow")
    if i_hook < i_ovl:
        ok("E2 先尝试直改宿主标签，再挂覆盖层（顺序正确）")
    else:
        bad("E2 顺序反了 —— 先挂了覆盖层才 hook，会出现双份到期时间")
else:
    bad("E2 CoreVerify.m 没有把两条路径串起来")

# E3 ★ hook 成功时不能重复画胶囊
if "hooked ? nil : shown" in core:
    ok("E3 hook 成功时覆盖层不画胶囊（避免双份到期）")
else:
    bad("E3 未处理「hook 成功仍画胶囊」的情况 —— 会出现两条到期时间")

# E4 ★ barCover 必须判空（它在 hook 成功后是不存在的）
if "if (self.barCover)" in overlay_code or "if (!self.barCover)" in overlay_code:
    ok("E4 覆盖层对 barCover 做了判空（hook 场景下它为 nil）")
else:
    bad("E4 relayout/setter 未判空 barCover —— hook 成功后会崩")

# E5 ★ 直改方案不能污染全局 UILabel 行为
if "method_exchangeImplementations" in hook_m or "class_replaceMethod" in hook_m:
    bad("E5 CVHostHook 用了 method swizzling —— 会污染全 App 标签，风险过高")
else:
    ok("E5 直改方案未使用 method swizzling（只改当前可见的那一个标签）")

# E6 候选标签必须排除自己的视图
if "CVOverlay" in hook_m or "hasPrefix:@\"CV\"" in hook_m:
    ok("E6 定位时排除了自身视图")
else:
    warn("E6 未显式排除自身视图，可能改到自己画的标签")

# E7 判定区常量存在
lay_txt = read("src/CVLayout.h") or ""
if "CVBarTouchZone" in lay_txt:
    ok("E7 CVLayout 提供到期条判定区 CVBarTouchZone")
else:
    warn("E7 CVLayout 缺 CVBarTouchZone，标签打分不精确")


# ══════════════════════════════════════════════════════════════════════════
print("\n\033[1m═══ D. T3 凭据与测试版 dylib 交叉核对 ═══\033[0m")
# ══════════════════════════════════════════════════════════════════════════
#
#  背景：
#    T3 的调用码 / APPKEY 是一串 16~32 位十六进制，人工抄写极易看错
#    （本工程就真的抄错过一次：APPKEY 的 df 被写成 fc）。
#    这里拿「测试版 dylib」当权威源做逐字节比对，
#    任何一位不一致都会被当场抓出来。
#
REF_DYLIB = "/workspace/CoreOffline.work.dylib"

T3_CREDS = [
    # (变量名, 从 dylib 里搜的锚点, 说明)
    ("kT3LoginCode",     "0AAD3A3337741A5B", "T3 登录调用码"),
    ("kT3NoticeCode",    "7EB0F4A8272A7EBD", "T3 公告调用码"),
    ("kT3VersionCode",   "61D5FC87F536273F", "T3 版本调用码"),
    ("kT3HeartbeatCode", "A44066FE62E69F9D", "T3 心跳调用码"),
    ("kT3AppKey",        "1e45cd9daa2d5d7dfc6d8e66abe43b0a", "T3 APPKEY"),
]

ref = None
try:
    with open(REF_DYLIB, "rb") as f:
        ref = f.read()
except Exception:
    pass

if ref is None:
    warn("D0 找不到参考 dylib %s，跳过凭据交叉核对" % REF_DYLIB)
else:
    ok("D0 参考 dylib 已加载（%d 字节）" % len(ref))
    for var, expected, desc in T3_CREDS:
        # 1) 源码里必须引用了这个变量
        if var not in core:
            bad("D1 %s 未在 CoreVerify.m 中定义" % var)
            continue
        # 2) 取源码里的实际字面量
        m = re.search(r'%s\s*=\s*@"([^"]+)"' % re.escape(var), core)
        if not m:
            bad("D1 %s 字面量解析失败" % var)
            continue
        actual = m.group(1)
        # 3) 与期望值逐字符比对
        if actual != expected:
            bad("D2 %s 值与权威源不一致！\n"
                "        源码: %s\n"
                "        应为: %s" % (var, actual, expected))
            continue
        # 4) 该值必须真的能在测试版 dylib 里找到（ASCII 或 UTF-16）
        in_ascii = expected.encode("ascii") in ref
        in_utf16 = expected.encode("utf-16-le") in ref
        if in_ascii or in_utf16:
            enc = "ASCII" if in_ascii else "UTF-16"
            ok("D2 %s 与 %s 一致且已在该 dylib 中验证（%s）" % (desc, var, enc))
        else:
            bad("D2 %s 在测试版 dylib 中找不到该值 —— 可能抄错" % desc)


# H0 ★ postflight.py 自身的健壮性
#
#  历史教训：曾经因为把 ok/warn/bad 写成单参数调用，
#  postflight 在 CI 上抛 TypeError，而本地（无 lipo/otool 分支）走不到那行，
#  完全没暴露。所以这里用 AST 静态扫描所有调用的参数个数。
_pf = read("checks/postflight.py") or ""
if _pf:
    try:
        arity_bad = [
            (n.lineno, n.func.id, len(n.args) + len(n.keywords))
            for n in ast.walk(ast.parse(_pf))
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id in ("ok", "warn", "bad")
            and len(n.args) + len(n.keywords) != 2
        ]
        if arity_bad:
            for ln, fn, cnt in arity_bad:
                bad("H0 postflight 行 %d: %s() 传了 %d 个参数（应为 2）"
                    % (ln, fn, cnt))
        else:
            ok("H0 postflight 的 ok/warn/bad 调用参数个数全部正确")
    except SyntaxError as e:
        bad("H0 postflight.py 语法错误: %s" % e)
else:
    warn("H0 找不到 postflight.py")


# ══════════════════════════════════════════════════════════════════════════
print("\n\033[1m═══ 汇总 ═══\033[0m")
print("  通过 %d，警告 %d，失败 %d" % (len(PASS), len(WARN), len(FAIL)))
if FAIL:
    print("\n\033[31m失败项：\033[0m")
    for x in FAIL:
        print("   - %s" % x)
if WARN:
    print("\n\033[33m警告项：\033[0m")
    for x in WARN:
        print("   - %s" % x)
sys.exit(1 if FAIL else 0)
