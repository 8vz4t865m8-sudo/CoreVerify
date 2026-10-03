//
//  CVHostHook.m —— 宿主到期标签「直改」实现
//
//  见 CVHostHook.h 顶部的设计说明。
//

#import "CVHostHook.h"
#import "../CVLayout.h"
#import "../CVLog.h"

// 日期正则：匹配 19xx / 20xx 开头的 yyyy-MM-dd 或 yyyy/MM/dd
static NSString * const kCVDatePattern = @"(?:19|20)\\d{2}[-/]\\d{1,2}[-/]\\d{1,2}";

// 到期文案特征词（宿主自己也用这个前缀）
static NSString * const kCVExpiryKeyword = @"授权至";

@interface CVHostHook ()
@property (nonatomic, strong, nullable) UILabel *targetLabel;
@property (nonatomic, copy, nullable) NSString *desiredText;
@property (nonatomic, strong, nullable) NSTimer *keepAliveTimer;
@end

@implementation CVHostHook

+ (instancetype)shared {
    static CVHostHook *s;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ s = [[CVHostHook alloc] init]; });
    return s;
}

#pragma mark - 公开接口

+ (BOOL)applyExpiryText:(NSString *)expiry {
    CVHostHook *h = [CVHostHook shared];
    UILabel *lb = [h locateExpiryLabel];
    if (!lb) {
        CVLog(@"[宿主直改] 未找到到期标签，退回覆盖层方案");
        return NO;
    }
    h.targetLabel = lb;
    h.desiredText = [h composeTextFor:expiry];

    NSString *before = lb.text ?: @"";
    lb.text = h.desiredText;
    CVLog(@"[宿主直改] ✅ 已改写标签  旧=「%@」 新=「%@」", before, h.desiredText);
    return YES;
}

+ (void)startKeepAliveWithExpiry:(NSString *)expiry {
    CVHostHook *h = [CVHostHook shared];
    [h stopKeepAliveTimer];       // ★ 注意：stopKeepAlive 是类方法（对外接口），
                                  //   这里是实例内部清理，用实例方法避免自调用歧义

    h.desiredText = [h composeTextFor:expiry];
    h.keepAliveTimer = [NSTimer scheduledTimerWithTimeInterval:1.0
                                                       target:h
                                                     selector:@selector(onKeepAliveTick)
                                                     userInfo:nil
                                                      repeats:YES];
    CVLog(@"[宿主直改] 已开启防回写守护");
}

+ (void)stopKeepAlive {
    [[CVHostHook shared] stopKeepAliveTimer];
}

/// 实例级定时器清理（供内部调用）
- (void)stopKeepAliveTimer {
    [self.keepAliveTimer invalidate];
    self.keepAliveTimer = nil;
}

+ (void)logCandidates {
    [[CVHostHook shared] logCandidates];
}

#pragma mark - 内部

/// 把真实到期时间拼成和宿主一样的文案：「授权至：2025-06-30 12:00:00」
- (NSString *)composeTextFor:(NSString *)expiry {
    NSString *v = expiry.length > 0 ? expiry : @"未知";
    return [NSString stringWithFormat:@"%@：%@", kCVExpiryKeyword, v];
}

/// 宿主可能定时刷新它自己的文案，这里每秒检查一次，被改回去就再改回来
- (void)onKeepAliveTick {
    UILabel *lb = self.targetLabel;
    if (!lb) return;
    if (!lb.window) return;              // 标签已经不在界面上，别动它
    if (self.desiredText.length == 0) return;
    if ([lb.text isEqualToString:self.desiredText]) return;

    NSString *was = lb.text ?: @"";
    lb.text = self.desiredText;
    CVLog(@"[宿主直改] 检测到回写，已纠正  →「%@」", was);
}

#pragma mark - 定位

/// 在 keyWindow 里找那个显示到期时间的 UILabel
- (nullable UILabel *)locateExpiryLabel {
    UIWindow *win = [self keyWindow];
    if (!win) {
        CVLog(@"[宿主直改] keyWindow 为空");
        return nil;
    }

    NSMutableArray<UILabel *> *cands = [NSMutableArray array];
    [self collectLabelsIn:win into:cands];

    // 过滤 + 评分，取最优
    UILabel *best = nil;
    NSInteger bestScore = 0;

    for (UILabel *lb in cands) {
        if (![self isEligible:lb]) continue;
        NSInteger score = [self scoreOf:lb];
        if (score > bestScore) {
            bestScore = score;
            best = lb;
        }
    }

    if (best && bestScore > 0) {
        CVLog(@"[宿主直改] 选中标签 score=%ld text=「%@」 frame=%@",
              (long)bestScore, best.text ?: @"", NSStringFromCGRect(best.frame));
    }
    return best;
}

/// 递归收集所有 UILabel
- (void)collectLabelsIn:(UIView *)root into:(NSMutableArray<UILabel *> *)out {
    if ([root isKindOfClass:[UILabel class]]) {
        [out addObject:(UILabel *)root];
    }
    for (UIView *sub in root.subviews) {
        [self collectLabelsIn:sub into:out];
    }
}

/// 硬性条件：不是我们的视图、可见、有文本、且文本像日期或含关键字
- (BOOL)isEligible:(UILabel *)lb {
    if (lb.hidden || lb.alpha < 0.01) return NO;
    if (lb.window != [self keyWindow]) return NO;

    // ★ 排除我们自己的视图（CVOverlay / CVVerifyPanel 都带特定 tag）
    if (lb.tag >= 9000 && lb.tag < 9100) return NO;      // CVOverlay 屏蔽块
    if ([NSStringFromClass([lb class]) hasPrefix:@"CV"]) return NO;

    NSString *t = lb.text;
    if (t.length == 0) return NO;

    BOOL hasDate = [self text:t matches:kCVDatePattern];
    BOOL hasKey  = [t rangeOfString:kCVExpiryKeyword].location != NSNotFound;
    return hasDate || hasKey;
}

/// 打分：越像"宿主那条到期标签"分越高
- (NSInteger)scoreOf:(UILabel *)lb {
    NSInteger s = 0;
    NSString *t = lb.text ?: @"";

    if ([t rangeOfString:kCVExpiryKeyword].location != NSNotFound) s += 100;
    if ([self text:t matches:kCVDatePattern]) s += 50;

    // 位置：换算到设计坐标，看是否落在到期条附近
    CGRect f = [self designRectFor:lb];
    if (CGRectIntersectsRect(f, CVBarTouchZone())) s += 40;

    // 单行、字号中等，更像标签主体
    if (lb.numberOfLines == 1) s += 5;

    return s;
}

/// 把某个 view 的 frame 换算成「390×844 设计坐标」
- (CGRect)designRectFor:(UIView *)v {
    UIWindow *win = [self keyWindow];
    if (!win) return CGRectZero;
    CGRect inWin = [v convertRect:v.bounds toView:win];
    CGFloat scale = win.bounds.size.width / CVDesignWidth;
    if (scale <= 0) return CGRectZero;
    return CGRectMake(inWin.origin.x / scale,
                      inWin.origin.y / scale,
                      inWin.size.width / scale,
                      inWin.size.height / scale);
}

- (BOOL)text:(NSString *)t matches:(NSString *)pattern {
    NSRegularExpression *re =
        [NSRegularExpression regularExpressionWithPattern:pattern
                                                  options:0
                                                    error:NULL];
    if (!re) return NO;
    NSRange r = NSMakeRange(0, t.length);
    return [re firstMatchInString:t options:0 range:r] != nil;
}

- (void)logCandidates {
    UIWindow *win = [self keyWindow];
    if (!win) { CVLog(@"[宿主直改] keyWindow 为空"); return; }
    NSMutableArray<UILabel *> *cands = [NSMutableArray array];
    [self collectLabelsIn:win into:cands];
    CVLog(@"[宿主直改] 共扫到 %lu 个 UILabel，其中像到期的：",
          (unsigned long)cands.count);
    for (UILabel *lb in cands) {
        if (![self isEligible:lb]) continue;
        CVLog(@"   · score=%ld text=「%@」 frame=%@",
              (long)[self scoreOf:lb], lb.text ?: @"",
              NSStringFromCGRect([self designRectFor:lb]));
    }
}

#pragma mark - 工具

- (nullable UIWindow *)keyWindow {
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

@end
