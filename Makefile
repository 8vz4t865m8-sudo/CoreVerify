# ══════════════════════════════════════════════════════════════════════════
#  CoreVerify —— 全屏卡密验证 + 主页覆盖 dylib
#
#  产物：CoreVerify.v1.dylib
#  注入要点：install name 必须是 @executable_path/CoreVerify.v1.dylib
#
#  依赖：Foundation + UIKit + Security（T3 SDK 的 RSA 用）+ CommonCrypto
#        全部是系统库，无第三方依赖
# ══════════════════════════════════════════════════════════════════════════

OUT       = CoreVerify.v1.dylib
TARGET    = arm64-apple-ios14.0
SDK_VER  ?= 17.5
SDK       = $(shell xcrun --sdk iphoneos --show-sdk-path 2>/dev/null)

ARCHS    ?= arm64 arm64e

SRC       = src/CoreVerify.m \
            src/CVLog.m \
            src/ui/CVVerifyPanel.m \
            src/ui/CVOverlay.m \
            src/ui/CVHostHook.m \
            src/t3sdk/T3Verify.m

INC       = -Isrc -Isrc/ui -Isrc/t3sdk
FRAMEWORKS = -framework Foundation -framework UIKit -framework Security

COMMON    = -dynamiclib \
            -fobjc-arc \
            -O2 \
            -Wall -Wno-unused-variable -Wno-unused-function \
            -fmodules \
            -miphoneos-version-min=14.0 \
            $(INC) \
            $(FRAMEWORKS) \
            -Wl,-install_name,@executable_path/$(OUT)

all: $(OUT)

$(OUT): $(SRC) src/CVLayout.h src/CVLog.h src/ui/CVVerifyPanel.h src/ui/CVOverlay.h src/ui/CVHostHook.h src/t3sdk/T3Verify.h
	@echo "=== 编译 $(OUT) ==="
ifeq ($(strip $(SDK)),)
	@echo "❌ 找不到 iphoneos SDK。请在有 Xcode 的 macOS 上构建（CI 已配置）。"
	@exit 1
endif
	@echo "SDK = $(SDK)"
	@set -e; \
	for arch in $(ARCHS); do \
	  echo "--- slice: $$arch ---"; \
	  xcrun --sdk iphoneos clang \
	      -arch $$arch \
	      -isysroot $(SDK) \
	      $(COMMON) \
	      -o $(OUT).$$arch $(SRC); \
	done
	@if [ -f $(OUT).arm64 ] && [ -f $(OUT).arm64e ]; then \
	  echo "--- 合并为 fat ---"; \
	  lipo -create -output $(OUT) $(OUT).arm64 $(OUT).arm64e; \
	  rm -f $(OUT).arm64 $(OUT).arm64e; \
	else \
	  mv $(OUT).$(word 2,$(ARCHS)) $(OUT) 2>/dev/null || mv $(OUT).$(firstword $(ARCHS)) $(OUT); \
	fi
	@echo "✅ 完成"
	@ls -la $(OUT)

# 只做静态检查（不需要 iOS SDK）
#
#  ├─ preflight.py   工程一致性 / 代码安全 / 坐标合理性 / T3 凭据交叉核对
#  └─ syntax_check.sh Objective-C 语法检查（Linux 也能跑）
check:
	@python3 checks/preflight.py
	@echo ""
	@echo "=== Objective-C 语法检查 ==="
	@./checks/syntax_check.sh

# 全量：检查 + 编译 + 产物断言
verify: check $(OUT)
	@python3 checks/postflight.py $(OUT)

clean:
	rm -f $(OUT) $(OUT).arm64 $(OUT).arm64e
	rm -rf build

.PHONY: all check verify clean
