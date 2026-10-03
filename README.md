# CoreVerify

给宿主 App 叠一层「全屏卡密验证 + 主页覆盖」的 dylib。

> 产物：`CoreVerify.v1.dylib`（双切片 arm64 + arm64e）

---

## 这个 dylib 做什么

用户明确要的三件事，全部已实现：

| # | 需求 | 实现 |
|---|------|------|
| ① | 全屏卡密验证界面，**验证成功就消失** | `CVVerifyPanel` —— 全屏自绘，不依赖宿主任何类 |
| ② | 覆盖掉「授权至：2099-12-31 23:59:59」，显示**真实**到期 | `CVHostHook`（直改宿主标签）→ 失败则 `CVOverlay`（平面覆盖） |
| ③ | 6 个按钮点不到，但保留「打开菜单」+ 顶部「音乐键」 | `CVOverlay` 的 `hitTest:` 精确拦截 |

### ① 全屏卡密验证界面

- 全屏自绘，**不依赖宿主**（用户要求）
- 验证逻辑用 **T3 SDK**（真实网络验证）
- 验证通过 → 界面淡出移除
- 卡密验证成功后会记住，下次自动登录

### ② 到期时间：直改优先，覆盖兜底

用户原话：

> 如果可以直接 hook 掉原宿主的到期时间显示真实的不行就覆盖掉显示真实的

所以是**两步走**：

```
CVHostHook applyExpiryText:
  ├─ 找到宿主那条 UILabel  →  直接改它的 text          ← 视觉完全融入宿主
  └─ 找不到                 →  返回 NO，交给 CVOverlay 平面覆盖
```

**怎么在不硬编码类名的前提下找到那个标签？**

沿用测试版 dylib 的思路（按可见文本筛），但更稳：

1. 遍历 keyWindow 下所有 `UILabel`
2. 排除自身视图（`tag 9000..9100` / 类名前缀 `CV`）
3. 文本能匹配日期正则 `(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}` 或含「授权至」
4. 按「关键字 +100 / 日期 +50 / 落在到期条区域 +40 / 单行 +5」打分，取最高

**不用 method swizzling。** 那会污染全 App 的 `setText:`，风险远大于收益。
这里只在当前可见的标签里精确挑一个，改完就完事，另加 1 秒一次的防回写守护。

### ③ 屏蔽 6 个按钮

| 屏蔽（点了没反应） | 放行 |
|---|---|
| 查看公告、启动游戏、提交工单、检查更新、工单进度、激活续时 | **打开菜单**、顶部**音乐键** |

实现：覆盖层默认 `userInteractionEnabled = YES`，但重写 `hitTest:withEvent:`：

```objc
- (UIView *)hitTest:(CGPoint)point withEvent:(UIEvent *)event {
    for (UIView *blk in self.blockViews) {
        if (CGRectContainsPoint(blk.frame, point)) return blk;   // 吃掉
    }
    return nil;   // ★ 其它位置一律穿透到宿主
}
```

「打开菜单」和「音乐键」虽然视觉上被盖住，但它们的矩形**不在屏蔽集合**里，
触摸照样落到宿主真按钮上 —— 功能完整保留。

---

## 坐标来源（本项目最核心的资产）

全部来自对用户截图的**像素级实测**，不是估算。

```
截图：1024 × 2216 px，iPhone 13（390 × 844 pt）
比例 1024/390 = 2.6256 px/pt —— 与 390:844 的 0.46209 完全吻合
换算：pt = px / 2.6256
```

**到期时间胶囊条**（实测 x=500 纵向扫描 + y=616 横向扫描）：

| 项 | 像素 | pt |
|---|---|---|
| 左边界 | x=64 | 24.4 |
| 右边界 | x=962 | 366.4 |
| 上边界 | y=614 | 233.8 |
| 下边界 | y=704 | 268.1 |
| 圆角 | — | 17.15（= 高/2） |

**6 个按钮**（高饱和像素扫描，`sat>50 & lum>70`）：

| 按钮 | x (pt) | y (pt) | w × h |
|---|---|---|---|
| 查看公告 | 11.8 | 318.4 | 98.6 × 36.9 |
| 音乐键 ★放行 | 176.0 | 318.4 | 37.7 × 36.9 |
| 启动游戏 | 279.2 | 318.4 | 98.6 × 36.9 |
| 提交工单 | 11.8 | 380.9 | 100.5 × 49.2 |
| 打开菜单 ★放行 | 122.6 | 384.3 | 144.3 × 121.9 |
| 检查更新 | 277.3 | 380.9 | 100.5 × 49.2 |
| 工单进度 | 11.8 | 530.5 | 100.2 × 39.6 |
| 激活续时 | 277.6 | 530.5 | 100.2 × 39.6 |

**取色**：

| 位置 | 色值 |
|---|---|
| 胶囊左描边 | `#CC4392` |
| 胶囊中部 | `#BB52C9` |
| 胶囊右描边 | `#8D5CF5` |
| 胶囊内部 | `#191737` |
| 页面背景 | `#0B0E1C` |
| 提交工单底 | `#2A68E7` |
| 打开菜单中心 | `#37C76B` |

全部集中定义在 [`src/CVLayout.h`](src/CVLayout.h)。

---

## 目录结构

```
coreverify/
├── Makefile
├── README.md
├── src/
│   ├── CoreVerify.m           主入口（constructor）+ 流程编排 + 心跳
│   ├── CVLayout.h             ★ 坐标/配色常量（全部来自截图像素实测）
│   ├── CVLog.h / CVLog.m      落地日志（自签环境 NSLog 抓不到）
│   ├── ui/
│   │   ├── CVVerifyPanel.h/.m ① 全屏卡密验证界面
│   │   ├── CVOverlay.h/.m     ③ 按钮屏蔽 + ② 到期覆盖（兜底）
│   │   └── CVHostHook.h/.m    ② 到期时间直改宿主标签（优先）
│   └── t3sdk/
│       ├── T3Verify.h         T3 SDK（纯源码，零外部依赖）
│       └── T3Verify.m
├── checks/
│   ├── preflight.py           68 项静态断言（无需 SDK）
│   ├── make_stubs.py          iOS SDK 最小 stub（给语法检查用）
│   ├── make_libc.py           Apple 风格极简 libc stub
│   ├── syntax_check.sh        Objective-C 语法检查（Linux 可跑）
│   └── postflight.py          编译产物验证（CI 上跑）
└── .github/workflows/
    └── build.yml              CI：静态检查 + macOS 构建 + 产物断言
```

---

## 构建

```bash
# 只跑静态检查（Linux / macOS 都行，秒级）
make check

# 完整构建（需要 macOS + Xcode + iOS SDK）
make ARCHS="arm64 arm64e"

# 构建 + 产物验证
make verify
```

产物：`CoreVerify.v1.dylib`，install name = `@executable_path/CoreVerify.v1.dylib`

> **沙箱/CI 说明**：本仓库在 Linux 上也能做实质检查 ——
> `checks/syntax_check.sh` 用 `clang -target arm64-apple-ios14.0` + 最小 stub 头，
> 能抓出漏分号、括号不配对、`@end` 缺失、方法签名不匹配、类型未定义等问题。
> 真机构建走 GitHub Actions 的 macOS runner。

---

## 检查体系

### `make check`（不需要 SDK）

**A 组 · 工程一致性** —— 产物名 / install name / 源文件 / T3 SDK 完整性

**B 组 · 代码安全**
- 不用 Keychain（自签环境 `SecItemAdd` 会返回 `-34018`）
- 不做全局类遍历
- 网络请求必须在子线程（T3 的 `loginWithKami` 是同步阻塞的）
- 跨线程 UI 必须回主线程
- `hitTest:` 必须穿透
- 不注入系统进程

**C 组 · 坐标合理性**
- 设计基准 390×844 与截图比例交叉验证
- 到期条几何（含左右边距对称性）
- 6 个屏蔽块坐标与实测一致
- 屏蔽块互不重叠、不压放行区、不越屏
- 等比缩放 + 安全区偏移

**D 组 · T3 凭据交叉核对** ★
- 拿**测试版 dylib** 当权威源，逐字节比对调用码 / APPKEY
- 本项目就真的在这上面栽过一次：APPKEY 的 `df` 被误写成 `fc`

**E 组 · 到期时间「直改优先 / 覆盖兜底」**
- 模块就位、调用顺序正确、hook 成功时不重复画胶囊
- `barCover` 判空、不用 swizzling、排除自身视图

### `make verify`（需要 SDK）

`checks/postflight.py` 验证产物：

| 组 | 检查 |
|---|---|
| A | 存在 / 体积 / Mach-O magic |
| B | `lipo -info` 双切片 arm64 + arm64e |
| C | `otool -D` install name |
| D | `otool -L` 链了 Foundation / UIKit / Security |
| E | `nm -gU` constructor `CoreVerifyEntry` |
| F | `strings` 有 T3 调用码 / RSA 公钥 / UI 文案 |
| G | ★ **反向断言**：绝不能有测试版后门痕迹 |

**G 组是本项目的一道保险。** 它检查产物里**不得出现**：

| 禁用串 | 含义 |
|---|---|
| `2099-12-31` | 测试版的「永远有效」硬编码到期值 |
| `t.me/cheatrev` | 测试版的 Telegram 跳转目标 |
| `CoreHomeLinkTarget` | 测试版的按钮跳转类 |
| `CoreHomeRewriteControls` | 测试版的按钮劫持函数 |
| `1970-01-01 00:00:01` | 测试版的未授权哨兵值 |

> 实测有效：拿 `postflight.py` 去跑测试版 dylib，**这 5 条全部命中**。

---

## 与测试版 dylib 的区别

| | 测试版 `CoreOffline.work.dylib` | 本版 `CoreVerify.v1.dylib` |
|---|---|---|
| 按钮点击 | **被劫持成跳转** `https://t.me/cheatrev` | **点了没反应**（不做任何动作） |
| 到期时间 | 硬编码 `2099-12-31 23:59:59` | 真实到期（来自 T3 验证结果） |
| 授权判定 | 后门：到期串 ≠ `1970-01-01 00:00:01` 即放行 | 真实 T3 网络验证 |
| 卡密验证 | 复用宿主弹窗 | **全屏自绘，不依赖宿主** |
| 宿主侵入度 | hook 了 `UIButton` 的 target | 只叠一层，宿主内部不动 |

---

## 日志

自签重打包后 `get-task-allow=False`，`NSLog` 抓不到，所以日志会落地到：

```
<App沙盒>/Documents/CoreVerify.log
```

用 Filza / 文件 App 就能打开。超过 512KB 自动滚动，保留后一半。

关键日志行：

```
[主控] 宿主窗口就绪 root=XXX
[主控] ✅ 自动登录成功，到期 2025-06-30 12:00:00
[宿主直改] 选中标签 score=190 text=「授权至：2099-12-31 23:59:59」frame=...
[宿主直改] ✅ 已改写标签  旧=「授权至：2099-12-31 23:59:59」 新=「授权至：2025-06-30 12:00:00」
[主控] 到期时间走【直改宿主标签】：「2025-06-30 12:00:00」
[覆盖层] 已挂载 window=... scale=1.000 topOffset=0.0
[心跳] 已启动，间隔 60s，连续失败 5 次处理
```

---

## 已知限制

- 坐标按 iPhone 13（390pt 宽）实测；其它机型靠等比缩放适配，
  极端比例（如 iPad）下按钮位置可能偏移。
- 「直改宿主标签」依赖宿主那条 UILabel 的文本特征；
  如果宿主改了文案风格，会自动退回覆盖层方案（不会失效，只是不够自然）。
- T3 验证需要网络；离线时会走 SDK 自己的降级逻辑。
