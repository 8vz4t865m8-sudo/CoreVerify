//
//  CVLayout.h —— CoreVerify 界面坐标常量
//
//  ★★★ 本文件所有数值都来自对用户截图的像素级实测，不是估算。
//
//  截图：1024 × 2216 px，iPhone 13（390 × 844 pt）
//        比例 1024/390 = 2.6256 px/pt  —— 与 390:844 完全吻合
//        换算公式： pt = px / 2.6256
//
//  取色基准：截图背景 #0B0E1C，胶囊条内底 #191737
//
//  底边安全区：截图 2216px 处是 Home Indicator（底部小白条），
//              实际可用高度到 ~2170px = 826pt
//

#ifndef CVLayout_h
#define CVLayout_h

#import <UIKit/UIKit.h>

/// 设计基准尺寸（截图对应的逻辑分辨率）
static const CGFloat CVDesignWidth  = 390.0;
static const CGFloat CVDesignHeight = 844.0;

/// 把截图像素换算成 pt（仅用于注释里留痕，代码里直接用 pt 常量）
#define CV_PX(_px)  ((_px) / 2.6256)

// ══════════════════════════════════════════════════════════════════════════
//  一、到期时间胶囊条（要覆盖的那一行）
// ══════════════════════════════════════════════════════════════════════════
//
//  实测（x=500 纵向扫描）：
//    y=614~618px  紫色上边框  #853F98 → #BB52C9
//    y=620~698px  内部底色    #191737
//    y=700~702px  蓝色下边框  #5A8FED → #5893F0
//    y=704px      胶囊结束
//
//  实测（y=616 横向扫描）：
//    x=64px  左端   #CC4392 玫红
//    x=500px 中部   #BB52C9 紫
//    x=950px 右端   #8D5CF5 蓝紫
//    → 左右边界 x=64..962px
//
//  → 胶囊：x 24.4~366.4pt，y 233.8~268.1pt，宽 342pt，高 34.3pt

//  整条覆盖层的 frame（直接盖在原胶囊上）
//  左边距 24.4pt，宽 342pt，高度 34.3pt，圆角 = 半高
static const CGFloat CVBarLeft    = 24.4;
static const CGFloat CVBarTop     = 233.8;
static const CGFloat CVBarWidth   = 342.0;
static const CGFloat CVBarHeight  = 34.3;
static const CGFloat CVBarRadius  = 17.15;   // = CVBarHeight / 2

//  胶囊内文字基线（原图 iPhone 13 文字中心 y≈660px = 251.4pt）
static const CGFloat CVBarTextCenterY = 251.4;

//  胶囊左右文字留白：原图文字起点 x≈70px = 26.7pt，
//  相对胶囊左边（24.4pt）内缩 2.3pt；再给点余量取 14pt 更稳妥
static const CGFloat CVBarPaddingH = 14.0;

//  胶囊渐变色（从左到右三元色，实测值）
#define CVBarColorLeft   [UIColor colorWithRed:0.800 green:0.263 blue:0.573 alpha:1.0]  // #CC4392
#define CVBarColorMid    [UIColor colorWithRed:0.733 green:0.322 blue:0.788 alpha:1.0]  // #BB52C9
#define CVBarColorRight  [UIColor colorWithRed:0.553 green:0.361 blue:0.957 alpha:1.0]  // #8D5CF5

//  胶囊内底色
#define CVBarFillColor   [UIColor colorWithRed:0.098 green:0.090 blue:0.216 alpha:1.0]  // #191737

//  左侧「iPhone 13 · iOS 18.4.1」文字色 #E34698
#define CVBarDeviceColor [UIColor colorWithRed:0.890 green:0.275 blue:0.596 alpha:1.0]
//  右侧「授权至：」前缀色（暗紫）
#define CVBarLabelColor  [UIColor colorWithRed:0.369 green:0.188 blue:0.455 alpha:1.0]
//  右侧日期值文字色 #6E5ED8
#define CVBarValueColor  [UIColor colorWithRed:0.431 green:0.369 blue:0.847 alpha:1.0]

// ══════════════════════════════════════════════════════════════════════════
//  二、六个要屏蔽点击的按钮 + 中央打开菜单 + 顶部音乐键
// ══════════════════════════════════════════════════════════════════════════
//
//  实测（高饱和像素横向扫描，三行）：
//
//    第 1 行 y 836..933px  (318.4..355.3 pt)
//       查看公告  x  31..290px  ( 11.8..110.4 pt)  98.6 × 36.9 pt
//       音乐键    x 462..561px  (176.0..213.7 pt)  37.7 × 36.9 pt  ← 保留可点
//       启动游戏  x 733..992px  (279.2..377.8 pt)  98.6 × 36.9 pt
//
//    第 2 行 y 1009..1329px (384.3..506.2 pt)
//       提交工单  x  31..295px  ( 11.8..112.4 pt) 100.5 × ~49  pt
//       打开菜单  x 322..701px  (122.6..267.0 pt) 144.3 × 121.9 pt ← 保留可点
//       检查更新  x 728..992px  (277.3..377.8 pt) 100.5 × ~49  pt
//
//    第 3 行 y 1393..1496px (530.5..569.8 pt)
//       工单进度  x  31..294px  ( 11.8..112.0 pt) 100.2 × 39.6 pt
//       教程      x 475..548px  (180.9..208.7 pt)  ~28 × 39.6 pt
//       激活续时  x 729..992px  (277.6..377.8 pt) 100.2 × 39.6 pt

/// 「查看公告」按钮矩形
static const CGRect CVRectAnnounce   = {{ 11.8, 318.4}, { 98.6, 36.9}};
/// 「启动游戏」按钮矩形
static const CGRect CVRectLaunchGame = {{279.2, 318.4}, { 98.6, 36.9}};
/// 「提交工单」按钮矩形（第 2 行高度按视觉取 49pt，与圆盘同一行）
static const CGRect CVRectTicket     = {{ 11.8, 380.9}, {100.5, 49.2}};
/// 「检查更新」按钮矩形
static const CGRect CVRectCheckUpd   = {{277.3, 380.9}, {100.5, 49.2}};
/// 「工单进度」按钮矩形
static const CGRect CVRectTicketProg = {{ 11.8, 530.5}, {100.2, 39.6}};
/// 「激活续时」按钮矩形
static const CGRect CVRectRenew      = {{277.6, 530.5}, {100.2, 39.6}};

/// ★ 这两块区域必须放行，不能被遮罩挡住
/// 「打开菜单」中央绿盘
static const CGRect CVRectOpenMenu   = {{122.6, 384.3}, {144.3, 121.9}};
/// 顶部音乐键
static const CGRect CVRectMusic      = {{176.0, 318.4}, { 37.7, 36.9}};

/// 六个屏蔽区（按上面顺序）
static inline NSArray<NSValue *> *CVBlockedRects(void) {
    return @[
        [NSValue valueWithCGRect:CVRectAnnounce],
        [NSValue valueWithCGRect:CVRectLaunchGame],
        [NSValue valueWithCGRect:CVRectTicket],
        [NSValue valueWithCGRect:CVRectCheckUpd],
        [NSValue valueWithCGRect:CVRectTicketProg],
        [NSValue valueWithCGRect:CVRectRenew],
    ];
}

/// 六个按钮的显示名 + 主色（用于日志与遮罩绘制）
/// 配色实测：提交工单 #2A68E7 / 打开菜单 #37C76B
static inline NSArray<NSString *> *CVBlockedTitles(void) {
    return @[@"查看公告", @"启动游戏", @"提交工单", @"检查更新", @"工单进度", @"激活续时"];
}

// ══════════════════════════════════════════════════════════════════════════
//  三、全屏验证界面（自绘）
// ══════════════════════════════════════════════════════════════════════════

/// 全屏验证层背景色，与原 App 背景一致的暗夜蓝黑 #0B0E1C
#define CVScreenBgColor  [UIColor colorWithRed:0.043 green:0.055 blue:0.110 alpha:1.0]

/// 主色调（沿用胶囊中部紫色 #BB52C9）
#define CVAccentColor    [UIColor colorWithRed:0.733 green:0.322 blue:0.788 alpha:1.0]

/// 主按钮渐变（紫 → 蓝紫，与胶囊条同系）
#define CVButtonColorA   [UIColor colorWithRed:0.800 green:0.263 blue:0.573 alpha:1.0]  // #CC4392
#define CVButtonColorB   [UIColor colorWithRed:0.553 green:0.361 blue:0.957 alpha:1.0]  // #8D5CF5

// ══════════════════════════════════════════════════════════════════════════
//  四、宿主标签定位辅助（给 CVHostHook 用）
// ══════════════════════════════════════════════════════════════════════════

/// 「到期条附近」的判定区 —— 比胶囊本身略大一圈，
/// 用于给候选 UILabel 打分（落在这一带说明它很可能就是那条到期文字）
///
/// 胶囊实测：y 233.8 ~ 268.1，高 34.3
/// 这里上下各放宽 24pt，左右放宽 8pt：
///   y 209.8 ~ 292.1   x 16.4 ~ 374.4
static inline CGRect CVBarTouchZone(void) {
    return CGRectMake(CVBarLeft - 8.0,
                      CVBarTop - 24.0,
                      CVBarWidth + 16.0,
                      CVBarHeight + 48.0);
}

#endif /* CVLayout_h */
