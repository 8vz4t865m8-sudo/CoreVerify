//
//  CVOverlay.m —— 主页覆盖层实现
//
//  ★ 触摸策略（核心）：
//     本层默认 userInteractionEnabled = YES，但重写 hitTest:withEvent:，
//     只有落在"6 个按钮矩形"内才返回 self（吃掉触摸），
//     其它所有位置一律返回 nil → 穿透到宿主。
//
//     「打开菜单」和「音乐键」虽然视觉上被我们盖住，但它们的矩形
//     不在屏蔽集合里，触摸照样穿透到宿主真按钮上 —— 完美保留功能。
//
//  ★ 坐标系：
//     所有常量是 390×844 设计坐标，实际用时按屏幕宽度等比缩放，
//     并处理刘海/安全区偏移（截图是 iPhone 13，状态栏 47pt）。
//

#import "CVOverlay.h"
#import "../CVLayout.h"
#import "../CVLog.h"

@interface CVOverlay ()
@property (nonatomic, strong) UIView *barCover;        // 到期条覆盖
@property (nonatomic, strong) UILabel *deviceLabel;
@property (nonatomic, strong) UILabel *expiryLabel;
@property (nonatomic, strong) CAGradientLayer *barBorder;
@property (nonatomic, strong) NSMutableArray<UIView *> *blockViews;
@property (nonatomic, assign) CGFloat scale;           // 实际宽 / 390
@property (nonatomic, assign) CGFloat topOffset;       // 安全区顶部偏移补偿
@end

@implementation CVOverlay

#pragma mark - 构造

- (instancetype)init {
    self = [super initWithFrame:[UIScreen mainScreen].bounds];
    if (self) {
        _scale = 1.0;
        _topOffset = 0.0;
        _blockViews = [NSMutableArray array];
        self.backgroundColor = [UIColor clearColor];
        // ★ 本层必须能收到触摸，但只拦特定区域（见 hitTest:）
        self.userInteractionEnabled = YES;
        self.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
        self.clipsToBounds = NO;

        [self computeScale];
        [self buildBlockers];     // ★ 屏蔽按钮：永远要做
        [self logSummary];
        // 注：到期胶囊条默认不建（expiryText 为 nil 时）。
        //     如果调用方设置了 expiryText（说明宿主标签没 hook 成功），
        //     setExpiryText: 会自动把胶囊补建出来。
    }
    return self;
}

/// 等比缩放到实际屏幕（设计基准 390pt 宽）
- (void)computeScale {
    CGFloat w = self.bounds.size.width;
    if (w <= 0) w = [UIScreen mainScreen].bounds.size.width;
    self.scale = w / CVDesignWidth;

    // 截图顶部状态栏区域在 iPhone 13 上是 47pt（刘海屏）。
    // 如果目标设备有安全区，把设计坐标整体下移，保持视觉对齐。
    if (@available(iOS 11.0, *)) {
        UIWindow *win = [self cv_window];
        CGFloat inset = win ? win.safeAreaInsets.top : 0;
        // iPhone 13 的 top inset 正好 47；其它机型做差值补偿
        self.topOffset = inset - 47.0;
    }
    // 非刘海机型（inset=20）会得到 -27，也没问题
}

- (CGFloat)sx:(CGFloat)designPt {
    return designPt * self.scale;
}
- (CGRect)scaledRect:(CGRect)r {
    return CGRectMake(r.origin.x * self.scale,
                      (r.origin.y + self.topOffset) * self.scale,
                      r.size.width  * self.scale,
                      r.size.height * self.scale);
}

#pragma mark - ① 到期时间覆盖条

- (void)buildBarCover {
    CGRect bar = [self scaledRect:CGRectMake(CVBarLeft, CVBarTop, CVBarWidth, CVBarHeight)];

    self.barCover = [[UIView alloc] initWithFrame:bar];
    self.barCover.backgroundColor = CVBarFillColor;
    self.barCover.layer.cornerRadius = bar.size.height / 2.0;   // 胶囊
    self.barCover.layer.masksToBounds = YES;
    self.barCover.userInteractionEnabled = NO;                  // 不挡触摸

    // 渐变描边（用一层带渐变 + 内缩蒙版的方式做环形边框）
    // 简单起见：外圈 1.5pt 用渐变 mask 实现
    CAGradientLayer *grad = [CAGradientLayer layer];
    grad.frame = self.barCover.bounds;
    grad.colors = @[(__bridge id)CVBarColorLeft.CGColor,
                    (__bridge id)CVBarColorMid.CGColor,
                    (__bridge id)CVBarColorRight.CGColor];
    grad.startPoint = CGPointMake(0.0, 0.5);
    grad.endPoint   = CGPointMake(1.0, 0.5);

    // 内圆角矩形做 mask，形成 1.5pt 的渐变色描边
    CAShapeLayer *mask = [CAShapeLayer layer];
    CGFloat bw = 1.6;
    UIBezierPath *outer = [UIBezierPath bezierPathWithRoundedRect:self.barCover.bounds
                                                     cornerRadius:bar.size.height / 2.0];
    UIBezierPath *inner = [UIBezierPath bezierPathWithRoundedRect:
                           CGRectInset(self.barCover.bounds, bw, bw)
                                                     cornerRadius:bar.size.height / 2.0 - bw];
    [outer appendPath:inner];
    outer.usesEvenOddFillRule = YES;
    mask.path = outer.CGPath;
    mask.fillRule = kCAFillRuleEvenOdd;
    grad.mask = mask;
    self.barBorder = grad;
    [self.barCover.layer addSublayer:grad];

    // 左侧：设备信息
    CGFloat pad = [self sx:CVBarPaddingH];
    CGFloat fontSz = MAX(10.0, 12.0 * self.scale);

    self.deviceLabel = [[UILabel alloc] initWithFrame:
        CGRectMake(pad, 0, bar.size.width * 0.45, bar.size.height)];
    self.deviceLabel.text = self.deviceText.length > 0 ? self.deviceText : @"iPhone 13 · iOS 18.4.1";
    self.deviceLabel.font = [UIFont systemFontOfSize:fontSz weight:UIFontWeightMedium];
    self.deviceLabel.textColor = CVBarDeviceColor;
    self.deviceLabel.textAlignment = NSTextAlignmentLeft;
    self.deviceLabel.adjustsFontSizeToFitWidth = YES;
    self.deviceLabel.minimumScaleFactor = 0.7;
    [self.barCover addSubview:self.deviceLabel];

    // 右侧：授权至 + 日期（右对齐）
    self.expiryLabel = [[UILabel alloc] initWithFrame:
        CGRectMake(bar.size.width * 0.42, 0, bar.size.width * 0.58 - pad, bar.size.height)];
    self.expiryLabel.font = [UIFont systemFontOfSize:fontSz weight:UIFontWeightMedium];
    self.expiryLabel.textAlignment = NSTextAlignmentRight;
    self.expiryLabel.adjustsFontSizeToFitWidth = YES;
    self.expiryLabel.minimumScaleFactor = 0.65;
    [self.barCover addSubview:self.expiryLabel];

    [self refreshExpiryLabel];
    [self addSubview:self.barCover];
}

/// 拼「授权至： 日期」，前缀暗一些、日期亮一些
- (void)refreshExpiryLabel {
    NSString *val = self.expiryText.length > 0 ? self.expiryText : @"读取中…";
    NSString *full = [NSString stringWithFormat:@"授权至：%@", val];

    NSMutableAttributedString *as =
        [[NSMutableAttributedString alloc] initWithString:full
            attributes:@{NSForegroundColorAttributeName: CVBarLabelColor}];
    [as addAttribute:NSForegroundColorAttributeName
               value:CVBarValueColor
               range:NSMakeRange(4, full.length - 4)];   // "授权至：" 是 4 个字
    self.expiryLabel.attributedText = as;
}

/// 设置到期文案。
/// ★ 语义约定：
///     expiryText 为 nil / 空  → 不画胶囊（说明宿主标签已被 CVHostHook 直接改掉）
///     expiryText 有值         → 现场补建胶囊并显示（hook 没成功时的退路）
- (void)setExpiryText:(NSString *)expiryText {
    _expiryText = [expiryText copy];

    if (expiryText.length == 0) {
        // 不需要胶囊 —— 如果之前建过就拆掉
        if (self.barCover) {
            [self.barCover removeFromSuperview];
            self.barCover = nil;
            self.barBorder = nil;
            self.deviceLabel = nil;
            self.expiryLabel = nil;
        }
        return;
    }

    if (!self.barCover) {
        // 首次需要时才建（延迟到真正用到）
        [self buildBarCover];
    }
    if (self.expiryLabel) [self refreshExpiryLabel];
}

- (void)setDeviceText:(NSString *)deviceText {
    _deviceText = [deviceText copy];
    if (self.deviceLabel) self.deviceLabel.text = deviceText;
}

#pragma mark - ② 六个按钮屏蔽块

- (void)buildBlockers {
    NSArray<NSValue *> *rects = CVBlockedRects();
    NSArray<NSString *> *names = CVBlockedTitles();

    for (NSUInteger i = 0; i < rects.count; i++) {
        CGRect r = [self scaledRect:[rects[i] CGRectValue]];

        // 屏蔽块向内收 2pt，避免边缘误伤相邻的可点区域（音乐键/打开菜单）
        r = CGRectInset(r, 2.0 * self.scale, 2.0 * self.scale);

        UIView *blk = [[UIView alloc] initWithFrame:r];
        // 完全透明 —— 视觉上完全看不出有东西盖着，但触摸会被吃掉
        blk.backgroundColor = [UIColor clearColor];
        blk.userInteractionEnabled = YES;      // 关键：要能接住触摸
        blk.tag = 9000 + (NSInteger)i;

        // 装一个"吸收点击"的手势，这样即使 hitTest 漏了也能兜住
        UITapGestureRecognizer *absorb = [[UITapGestureRecognizer alloc]
                                          initWithTarget:self action:@selector(absorbTap:)];
        absorb.cancelsTouchesInView = YES;
        [blk addGestureRecognizer:absorb];

        [self addSubview:blk];
        [self.blockViews addObject:blk];

        CVLog(@"[覆盖层] 屏蔽 #%lu %@  x=%.1f y=%.1f w=%.1f h=%.1f",
              (unsigned long)(i + 1), names[i],
              r.origin.x, r.origin.y, r.size.width, r.size.height);
    }
}

- (void)absorbTap:(UITapGestureRecognizer *)g {
    // 什么也不做 —— 这就是"点了没反应"
    NSInteger idx = g.view.tag - 9000;
    NSArray<NSString *> *names = CVBlockedTitles();
    if (idx >= 0 && idx < (NSInteger)names.count) {
        CVLog(@"[覆盖层] 已拦截点击：%@", names[idx]);
    }
}

#pragma mark - ★ 触摸穿透核心

- (UIView *)hitTest:(CGPoint)point withEvent:(UIEvent *)event {
    // 先看有没有命中屏蔽块
    for (UIView *blk in self.blockViews) {
        if (blk.hidden || blk.alpha < 0.01) continue;
        if (CGRectContainsPoint(blk.frame, point)) {
            return blk;     // 吃掉这次触摸
        }
    }
    // 其它位置：返回 nil → 事件穿透到宿主的视图层级
    return nil;
}

- (BOOL)shouldBlockTouchAtPoint:(CGPoint)pt {
    for (UIView *blk in self.blockViews) {
        if (CGRectContainsPoint(blk.frame, pt)) return YES;
    }
    return NO;
}

#pragma mark - 挂载 / 摘除

- (void)attachToWindow {
    UIWindow *win = [self cv_window];
    if (!win) {
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.4 * NSEC_PER_SEC)),
                       dispatch_get_main_queue(), ^{ [self attachToWindow]; });
        return;
    }
    if (self.superview == win) return;

    [self removeFromSuperview];
    self.frame = win.bounds;
    [self computeScale];
    [self relayout];
    [win addSubview:self];
    // ★ 保证在最上层（但不抢 first responder）
    [win bringSubviewToFront:self];

    CVLog(@"[覆盖层] 已挂载 window=%@ bounds=%@ scale=%.3f topOffset=%.1f",
          NSStringFromClass([win class]), NSStringFromCGRect(win.bounds),
          self.scale, self.topOffset);
}

/// 屏幕尺寸变化（旋转/分屏）时重算
- (void)relayout {
    // ★ barCover 现在是可选的（宿主标签 hook 成功时不存在），必须判空
    if (self.barCover) {
        CGRect bar = [self scaledRect:CGRectMake(CVBarLeft, CVBarTop, CVBarWidth, CVBarHeight)];
        self.barCover.frame = bar;
        self.barCover.layer.cornerRadius = bar.size.height / 2.0;
        self.barBorder.frame = self.barCover.bounds;

        CGFloat pad = [self sx:CVBarPaddingH];
        self.deviceLabel.frame = CGRectMake(pad, 0, bar.size.width * 0.45, bar.size.height);
        self.expiryLabel.frame = CGRectMake(bar.size.width * 0.42, 0,
                                            bar.size.width * 0.58 - pad, bar.size.height);
    }

    NSArray<NSValue *> *rects = CVBlockedRects();
    for (NSUInteger i = 0; i < self.blockViews.count && i < rects.count; i++) {
        CGRect r = CGRectInset([self scaledRect:[rects[i] CGRectValue]],
                               2.0 * self.scale, 2.0 * self.scale);
        self.blockViews[i].frame = r;
    }
}

- (void)dismiss {
    CVLog(@"[覆盖层] 摘除");
    [self removeFromSuperview];
}

- (UIWindow *)cv_window {
    UIWindow *found = nil;
    if (@available(iOS 13.0, *)) {
        for (UIScene *scene in [UIApplication sharedApplication].connectedScenes) {
            if (![scene isKindOfClass:[UIWindowScene class]]) continue;
            UIWindowScene *ws = (UIWindowScene *)scene;
            for (UIWindow *w in ws.windows) {
                if (w.isKeyWindow) return w;
            }
            if (!found && ws.windows.count > 0) found = ws.windows.firstObject;
        }
    }
    if (!found) found = [UIApplication sharedApplication].keyWindow;
    return found;
}

- (void)logSummary {
    CVLog(@"[覆盖层] 设计坐标 → 实际坐标（scale=%.3f）：", self.scale);
    CVLog(@"  到期条  x=%.1f y=%.1f w=%.1f h=%.1f",
          [self sx:CVBarLeft], [self sx:CVBarTop + self.topOffset],
          [self sx:CVBarWidth], [self sx:CVBarHeight]);
    NSArray<NSString *> *names = CVBlockedTitles();
    NSArray<NSValue *> *rects = CVBlockedRects();
    for (NSUInteger i = 0; i < rects.count; i++) {
        CGRect r = [self scaledRect:[rects[i] CGRectValue]];
        CVLog(@"  %-8s x=%.1f y=%.1f w=%.1f h=%.1f | 放行: %s",
              [names[i] UTF8String], r.origin.x, r.origin.y, r.size.width, r.size.height,
              ([names[i] isEqualToString:@"打开菜单"] ? "YES" : "NO"));
    }
    CGRect m = [self scaledRect:CVRectMusic];
    CVLog(@"  音乐键(放行) x=%.1f y=%.1f w=%.1f h=%.1f",
          m.origin.x, m.origin.y, m.size.width, m.size.height);
}

@end
