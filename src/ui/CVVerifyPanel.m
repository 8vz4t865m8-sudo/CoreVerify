//
//  CVVerifyPanel.m —— 全屏卡密验证界面实现
//
//  ★ 设计原则（前几版踩坑总结）：
//    1. 全屏铺满，背景不透明 —— 让宿主的界面完全看不见，避免误触
//    2. 不使用 UIVisualEffectView（自签环境下偶发崩溃）
//    3. 不使用 Keychain（T3 SDK 也不用，只走 NSUserDefaults）
//    4. 键盘处理用通知，不用监听 window
//    5. 验证在子线程做，主线程只更新 UI —— T3 的 loginWithKami 会阻塞
//

#import "CVVerifyPanel.h"
#import "../CVLayout.h"
#import "../CVLog.h"

static NSString * const kCVPrefSavedCard = @"cv_saved_card";
static NSString * const kCVPrefStateCode = @"cv_state_code";
static NSString * const kCVPrefEndTime   = @"cv_end_time";

@interface CVVerifyPanel () <UITextFieldDelegate>
@property (nonatomic, strong) T3Verify *verifier;
@property (nonatomic, strong) UITextField *input;
@property (nonatomic, strong) UIButton *submitButton;
@property (nonatomic, strong) UILabel *statusLabel;
@property (nonatomic, strong, nullable) UIActivityIndicatorView *spinner;
@property (nonatomic, assign) BOOL busy;
@property (nonatomic, assign) CGFloat keyboardHeight;
@property (nonatomic, strong) UIView *card;       // 中部卡片容器
@property (nonatomic, strong) NSLayoutConstraint *cardCenterY;
@property (nonatomic, strong, nullable) CAGradientLayer *submitGradient;
@end
@implementation CVVerifyPanel

#pragma mark - 构造

- (instancetype)initWithVerifier:(T3Verify *)verifier {
    self = [super initWithFrame:[UIScreen mainScreen].bounds];
    if (self) {
        _verifier = verifier;
        self.backgroundColor = CVScreenBgColor;
        self.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
        [self buildUI];
        [self observeKeyboard];
        [self prefill];
    }
    return self;
}

#pragma mark - UI 构建

- (void)buildUI {
    // ── 背景微光（两个大圆，纯装饰，不拦截触摸）──
    UIView *glow1 = [[UIView alloc] initWithFrame:CGRectMake(-80, -60, 260, 260)];
    glow1.backgroundColor = CVAccentColor;
    glow1.alpha = 0.10;
    glow1.layer.cornerRadius = 130;
    glow1.userInteractionEnabled = NO;
    [self addSubview:glow1];

    UIView *glow2 = [[UIView alloc] initWithFrame:CGRectMake(CVDesignWidth - 150, 520, 220, 220)];
    glow2.backgroundColor = CVButtonColorB;
    glow2.alpha = 0.09;
    glow2.layer.cornerRadius = 110;
    glow2.userInteractionEnabled = NO;
    [self addSubview:glow2];

    // ── 中部卡片 ──
    self.card = [[UIView alloc] init];
    self.card.translatesAutoresizingMaskIntoConstraints = NO;
    [self addSubview:self.card];

    // 图标（自绘盾牌）
    UIView *iconWrap = [[UIView alloc] initWithFrame:CGRectMake(0, 0, 64, 64)];
    iconWrap.translatesAutoresizingMaskIntoConstraints = NO;
    iconWrap.backgroundColor = [UIColor colorWithWhite:1.0 alpha:0.06];
    iconWrap.layer.cornerRadius = 18;
    iconWrap.layer.borderWidth = 1.0;
    iconWrap.layer.borderColor = [CVAccentColor colorWithAlphaComponent:0.45].CGColor;
    [self.card addSubview:iconWrap];

    UILabel *iconGlyph = [[UILabel alloc] init];
    iconGlyph.translatesAutoresizingMaskIntoConstraints = NO;
    iconGlyph.text = @"\U0001F512"; // 🔒
    iconGlyph.font = [UIFont systemFontOfSize:30];
    iconGlyph.textAlignment = NSTextAlignmentCenter;
    [iconWrap addSubview:iconGlyph];

    // 标题
    UILabel *title = [[UILabel alloc] init];
    title.translatesAutoresizingMaskIntoConstraints = NO;
    title.text = @"卡密验证";
    title.font = [UIFont systemFontOfSize:26 weight:UIFontWeightBold];
    title.textColor = [UIColor whiteColor];
    title.textAlignment = NSTextAlignmentCenter;
    [self.card addSubview:title];

    // 副标题
    UILabel *subtitle = [[UILabel alloc] init];
    subtitle.translatesAutoresizingMaskIntoConstraints = NO;
    subtitle.text = @"请输入卡密以激活完整功能";
    subtitle.font = [UIFont systemFontOfSize:13.5];
    subtitle.textColor = [UIColor colorWithWhite:1.0 alpha:0.45];
    subtitle.textAlignment = NSTextAlignmentCenter;
    [self.card addSubview:subtitle];

    // ── 输入框容器 ──
    UIView *inputWrap = [[UIView alloc] init];
    inputWrap.translatesAutoresizingMaskIntoConstraints = NO;
    inputWrap.backgroundColor = [UIColor colorWithWhite:1.0 alpha:0.055];
    inputWrap.layer.cornerRadius = 13;
    inputWrap.layer.borderWidth = 1.0;
    inputWrap.layer.borderColor = [UIColor colorWithWhite:1.0 alpha:0.10].CGColor;
    [self.card addSubview:inputWrap];

    self.input = [[UITextField alloc] init];
    self.input.translatesAutoresizingMaskIntoConstraints = NO;
    self.input.placeholder = @"请输入卡密";
    self.input.attributedPlaceholder = [[NSAttributedString alloc]
        initWithString:@"请输入卡密"
            attributes:@{NSForegroundColorAttributeName:[UIColor colorWithWhite:1.0 alpha:0.28]}];
    self.input.font = [UIFont fontWithName:@"Menlo" size:14.5] ?: [UIFont systemFontOfSize:14.5];
    self.input.textColor = [UIColor whiteColor];
    self.input.tintColor = CVAccentColor;
    self.input.backgroundColor = [UIColor clearColor];
    self.input.autocorrectionType = UITextAutocorrectionTypeNo;
    self.input.autocapitalizationType = UITextAutocapitalizationTypeNone;
    self.input.spellCheckingType = UITextSpellCheckingTypeNo;
    self.input.keyboardType = UIKeyboardTypeASCIICapable;
    self.input.returnKeyType = UIReturnKeyGo;
    self.input.delegate = self;
    self.input.clearButtonMode = UITextFieldViewModeWhileEditing;
    [inputWrap addSubview:self.input];

    // 「粘贴」小按钮
    UIButton *pasteBtn = [UIButton buttonWithType:UIButtonTypeSystem];
    pasteBtn.translatesAutoresizingMaskIntoConstraints = NO;
    [pasteBtn setTitle:@"粘贴" forState:UIControlStateNormal];
    [pasteBtn setTitleColor:CVAccentColor forState:UIControlStateNormal];
    pasteBtn.titleLabel.font = [UIFont systemFontOfSize:13 weight:UIFontWeightMedium];
    [pasteBtn addTarget:self action:@selector(onPaste) forControlEvents:UIControlEventTouchUpInside];
    [inputWrap addSubview:pasteBtn];

    // ── 提交按钮（渐变背景）──
    self.submitButton = [UIButton buttonWithType:UIButtonTypeCustom];
    self.submitButton.translatesAutoresizingMaskIntoConstraints = NO;
    [self.submitButton setTitle:@"验证并激活" forState:UIControlStateNormal];
    [self.submitButton setTitleColor:[UIColor whiteColor] forState:UIControlStateNormal];
    self.submitButton.titleLabel.font = [UIFont systemFontOfSize:16.5 weight:UIFontWeightSemibold];
    self.submitButton.layer.cornerRadius = 13;
    self.submitButton.layer.masksToBounds = YES;
    [self.submitButton addTarget:self action:@selector(onSubmit) forControlEvents:UIControlEventTouchUpInside];

    CAGradientLayer *grad = [CAGradientLayer layer];
    grad.colors = @[(__bridge id)CVButtonColorA.CGColor,
                    (__bridge id)CVButtonColorB.CGColor];
    grad.startPoint = CGPointMake(0.0, 0.5);
    grad.endPoint   = CGPointMake(1.0, 0.5);
    grad.frame = CGRectMake(0, 0, CVDesignWidth - 96, 48);
    grad.cornerRadius = 13;
    [self.submitButton.layer insertSublayer:grad atIndex:0];
    self.submitGradient = grad;
    [self.card addSubview:self.submitButton];

    // ── 状态提示条 ──
    self.statusLabel = [[UILabel alloc] init];
    self.statusLabel.translatesAutoresizingMaskIntoConstraints = NO;
    self.statusLabel.font = [UIFont systemFontOfSize:12.5];
    self.statusLabel.textColor = [UIColor colorWithWhite:1.0 alpha:0.55];
    self.statusLabel.textAlignment = NSTextAlignmentCenter;
    self.statusLabel.numberOfLines = 2;
    self.statusLabel.text = @"";
    [self.card addSubview:self.statusLabel];

    // ── 加载指示器 ──
    self.spinner = [[UIActivityIndicatorView alloc] initWithActivityIndicatorStyle:UIActivityIndicatorViewStyleMedium];
    self.spinner.translatesAutoresizingMaskIntoConstraints = NO;
    self.spinner.color = [UIColor whiteColor];
    self.spinner.hidesWhenStopped = YES;
    [self.submitButton addSubview:self.spinner];

    // ── 底部小字 ──
    UILabel *foot = [[UILabel alloc] init];
    foot.translatesAutoresizingMaskIntoConstraints = NO;
    foot.text = @"验证通过后即可进入主界面";
    foot.font = [UIFont systemFontOfSize:11.5];
    foot.textColor = [UIColor colorWithWhite:1.0 alpha:0.22];
    foot.textAlignment = NSTextAlignmentCenter;
    [self.card addSubview:foot];

    // ── 约束 ──
    UILayoutGuide *g = self.safeAreaLayoutGuide;
    [NSLayoutConstraint activateConstraints:@[
        // 卡片整体
        [self.card.leadingAnchor  constraintEqualToAnchor:self.leadingAnchor constant:48],
        [self.card.trailingAnchor constraintEqualToAnchor:self.trailingAnchor constant:-48],

        // 图标
        [iconWrap.topAnchor      constraintEqualToAnchor:self.card.topAnchor],
        [iconWrap.centerXAnchor  constraintEqualToAnchor:self.card.centerXAnchor],
        [iconWrap.widthAnchor     constraintEqualToConstant:64],
        [iconWrap.heightAnchor    constraintEqualToConstant:64],
        [iconGlyph.centerXAnchor  constraintEqualToAnchor:iconWrap.centerXAnchor],
        [iconGlyph.centerYAnchor  constraintEqualToAnchor:iconWrap.centerYAnchor],

        // 标题
        [title.topAnchor     constraintEqualToAnchor:iconWrap.bottomAnchor constant:18],
        [title.leadingAnchor constraintEqualToAnchor:self.card.leadingAnchor],
        [title.trailingAnchor constraintEqualToAnchor:self.card.trailingAnchor],

        // 副标题
        [subtitle.topAnchor     constraintEqualToAnchor:title.bottomAnchor constant:6],
        [subtitle.leadingAnchor constraintEqualToAnchor:self.card.leadingAnchor],
        [subtitle.trailingAnchor constraintEqualToAnchor:self.card.trailingAnchor],

        // 输入框容器
        [inputWrap.topAnchor      constraintEqualToAnchor:subtitle.bottomAnchor constant:26],
        [inputWrap.leadingAnchor  constraintEqualToAnchor:self.card.leadingAnchor],
        [inputWrap.trailingAnchor constraintEqualToAnchor:self.card.trailingAnchor],
        [inputWrap.heightAnchor   constraintEqualToConstant:52],

        [self.input.leadingAnchor  constraintEqualToAnchor:inputWrap.leadingAnchor constant:15],
        [self.input.topAnchor      constraintEqualToAnchor:inputWrap.topAnchor],
        [self.input.bottomAnchor   constraintEqualToAnchor:inputWrap.bottomAnchor],
        [pasteBtn.leadingAnchor    constraintEqualToAnchor:self.input.trailingAnchor constant:8],
        [pasteBtn.trailingAnchor   constraintEqualToAnchor:inputWrap.trailingAnchor constant:-14],
        [pasteBtn.centerYAnchor    constraintEqualToAnchor:inputWrap.centerYAnchor],

        // 提交按钮
        [self.submitButton.topAnchor      constraintEqualToAnchor:inputWrap.bottomAnchor constant:16],
        [self.submitButton.leadingAnchor  constraintEqualToAnchor:self.card.leadingAnchor],
        [self.submitButton.trailingAnchor constraintEqualToAnchor:self.card.trailingAnchor],
        [self.submitButton.heightAnchor   constraintEqualToConstant:48],

        [self.spinner.trailingAnchor constraintEqualToAnchor:self.submitButton.trailingAnchor constant:-18],
        [self.spinner.centerYAnchor  constraintEqualToAnchor:self.submitButton.centerYAnchor],

        // 状态
        [self.statusLabel.topAnchor      constraintEqualToAnchor:self.submitButton.bottomAnchor constant:14],
        [self.statusLabel.leadingAnchor  constraintEqualToAnchor:self.card.leadingAnchor constant:-10],
        [self.statusLabel.trailingAnchor constraintEqualToAnchor:self.card.trailingAnchor constant:10],

        // 底部小字
        [foot.topAnchor      constraintEqualToAnchor:self.statusLabel.bottomAnchor constant:16],
        [foot.leadingAnchor  constraintEqualToAnchor:self.card.leadingAnchor],
        [foot.trailingAnchor constraintEqualToAnchor:self.card.trailingAnchor],
        [foot.bottomAnchor   constraintEqualToAnchor:self.card.bottomAnchor],
    ]];

    // 卡片垂直居中（键盘弹出时上移）
    self.cardCenterY = [self.card.centerYAnchor constraintEqualToAnchor:g.centerYAnchor constant:-20];
    self.cardCenterY.active = YES;
}

#pragma mark - 键盘

- (void)observeKeyboard {
    [[NSNotificationCenter defaultCenter] addObserver:self
                                             selector:@selector(onKeyboardChange:)
                                                 name:UIKeyboardWillChangeFrameNotification
                                               object:nil];
}

- (void)onKeyboardChange:(NSNotification *)note {
    NSDictionary *info = note.userInfo;
    CGRect end = [info[UIKeyboardFrameEndUserInfoKey] CGRectValue];
    NSTimeInterval dur = [info[UIKeyboardAnimationDurationUserInfoKey] doubleValue];

    CGFloat screenH = self.bounds.size.height;
    CGFloat overlap = MAX(0.0, screenH - end.origin.y);
    // 键盘占了下半屏，卡片上移
    CGFloat shift = overlap > 0 ? -MIN(overlap / 2.0, 150.0) : -20.0;

    self.cardCenterY.constant = shift;
    [UIView animateWithDuration:dur > 0 ? dur : 0.25
                          delay:0
                        options:UIViewAnimationOptionCurveEaseOut
                     animations:^{ [self layoutIfNeeded]; }
                     completion:nil];
}

#pragma mark - 卡密预填 / 保存

- (void)prefill {
    NSString *saved = [[NSUserDefaults standardUserDefaults] stringForKey:kCVPrefSavedCard];
    if (saved.length > 0) {
        self.input.text = saved;
        CVLog(@"[面板] 预填已保存卡密 ***%s", saved.length > 4
              ? [[saved substringFromIndex:saved.length - 4] UTF8String] : "****");
    }
}

- (void)onPaste {
    NSString *s = [UIPasteboard generalPasteboard].string;
    s = [s stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
    if (s.length == 0) {
        [self setStatus:@"剪贴板是空的" isError:YES];
        return;
    }
    self.input.text = s;
    [self setStatus:@"" isError:NO];
}

#pragma mark - 提交验证

- (BOOL)textFieldShouldReturn:(UITextField *)textField {
    [self onSubmit];
    return YES;
}

- (void)onSubmit {
    if (self.busy) return;

    NSString *card = [self.input.text stringByTrimmingCharactersInSet:
                      [NSCharacterSet whitespaceAndNewlineCharacterSet]];
    if (card.length == 0) {
        [self setStatus:@"请先输入卡密" isError:YES];
        return;
    }

    [self.input resignFirstResponder];
    [self setBusy:YES status:@"正在验证，请稍候…"];

    // ★ T3 的 loginWithKami 是同步阻塞的，必须丢到子线程
    __weak typeof(self) weakSelf = self;
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        NSString *machineCode = [T3Verify getMachineCode];
        T3LoginResult *result = nil;
        @try {
            result = [weakSelf.verifier loginWithKami:card imei:machineCode];
        } @catch (NSException *e) {
            result = [T3LoginResult fail:[NSString stringWithFormat:@"验证异常：%@", e.reason]];
        }

        dispatch_async(dispatch_get_main_queue(), ^{
            typeof(self) self = weakSelf;
            if (!self) return;

            if (result && result.success) {
                [self setBusy:NO status:@""];
                CVLog(@"[面板] ✅ 验证成功 card=***%s 到期=%s 时长=%s 剩余=%s",
                      card.length > 4 ? [[card substringFromIndex:card.length - 4] UTF8String] : "****",
                      result.endTime ? [result.endTime UTF8String] : "(nil)",
                      result.amount  ? [result.amount  UTF8String] : "-",
                      result.available ? [result.available UTF8String] : "-");

                // 落地保存，供下次自动登录 + 到期展示
                NSUserDefaults *ud = [NSUserDefaults standardUserDefaults];
                [ud setObject:card forKey:kCVPrefSavedCard];
                if (result.statecode) [ud setObject:result.statecode forKey:kCVPrefStateCode];
                if (result.endTime)   [ud setObject:result.endTime   forKey:kCVPrefEndTime];
                [ud synchronize];

                if (self.onVerified) self.onVerified(result, card, result.statecode ?: @"");
                [self dismiss];

            } else {
                NSString *msg = result.error.length > 0 ? result.error : @"验证失败，请检查卡密";
                [self setBusy:NO status:msg];
                CVLog(@"[面板] ❌ 验证失败：%s", [msg UTF8String]);
                // 轻微抖动反馈
                [self shake];
            }
        });
    });
}

- (void)shake {
    CAKeyframeAnimation *k = [CAKeyframeAnimation animationWithKeyPath:@"transform.translation.x"];
    k.values = @[@(-9), @(9), @(-6), @(6), @(-3), @(3), @(0)];
    k.duration = 0.4;
    [self.card.layer addAnimation:k forKey:@"cv_shake"];
}

#pragma mark - 状态

- (void)setBusy:(BOOL)busy status:(NSString *)status {
    self.busy = busy;
    self.submitButton.enabled = !busy;
    self.submitButton.alpha = busy ? 0.62 : 1.0;
    if (busy) [self.spinner startAnimating]; else [self.spinner stopAnimating];
    [self setStatus:status isError:NO];
}

- (void)setStatus:(NSString *)text isError:(BOOL)isError {
    self.statusLabel.text = text ?: @"";
    self.statusLabel.textColor = isError
        ? [UIColor colorWithRed:1.0 green:0.42 blue:0.46 alpha:1.0]
        : [UIColor colorWithWhite:1.0 alpha:0.55];
}

#pragma mark - 显示 / 隐藏

- (void)showInWindow {
    UIWindow *win = [self cv_keyWindow];
    if (!win) {
        CVLog(@"[面板] ⚠️ 找不到可用 window，延迟重试");
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.4 * NSEC_PER_SEC)),
                       dispatch_get_main_queue(), ^{ [self showInWindow]; });
        return;
    }

    self.frame = win.bounds;
    [win addSubview:self];
    self.alpha = 0.0;
    self.card.transform = CGAffineTransformMakeScale(0.94, 0.94);
    [UIView animateWithDuration:0.28 animations:^{
        self.alpha = 1.0;
        self.card.transform = CGAffineTransformIdentity;
    } completion:^(BOOL f) {
        CVLog(@"[面板] 全屏验证界面已显示");
    }];
}

- (void)dismiss {
    [self.input resignFirstResponder];
    [UIView animateWithDuration:0.24 animations:^{
        self.alpha = 0.0;
        self.card.transform = CGAffineTransformMakeScale(0.96, 0.96);
    } completion:^(BOOL finished) {
        [self removeFromSuperview];
        CVLog(@"[面板] 验证界面已移除");
    }];
}

- (UIWindow *)cv_keyWindow {
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

- (void)dealloc {
    [[NSNotificationCenter defaultCenter] removeObserver:self];
}

@end
