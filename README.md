工厂测试源码，支持图形界面。

## 依赖

- Python3
- unittest
- PyQt5

## 源码目录

```
├── boards/                  # 各板型专属文件
│   ├── k3-pico-itx/
│   │   ├── board.py         # 板型标识（COMPATIBLE、BOARD_NAME）
│   │   ├── cricket/         # cricket 配置（如有定制）
│   │   ├── stability        # 稳定性测试脚本
│   │   ├── tests/
│   │   │   ├── auto/        # 自动测试用例
│   │   │   └── manual/      # 手动测试用例
│   │   └── utils/           # 板型专属工具
│   ├── k3-com260/
│   ├── k3-com260-kit/
│   └── k3-com260-ifx/
├── common/                  # 各板型共用文件
│   ├── factorytest/         # 框架核心（launcher、board 检测等）
│   ├── res/                 # 测试资源文件
│   ├── gpu.sh
│   ├── vpu.sh
│   ├── memtester.sh
│   └── stress-ng.sh
├── debian/                  # Debian 打包脚本
└── gui-main                 # 启动脚本
```

## 测试项

测试项分为自动测试项和手动测试项。自动测试项无需人工干预，自动判定结果；手动测试项需要人工参与判断。

添加规则：

- 自动测试项放入对应板型的 `tests/auto`，手动测试项放入 `tests/manual`
- 文件名以 `test_` 开头，可加序号控制加载顺序，例如 `test_01_nvme_ssd.py`
- 每个文件定义一个测试类，继承 `unittest.TestCase`
- 测试方法名称必须以 `test_` 开头
- 类中定义字典 `LANGUAGES` 用于多语言支持

注意：不要在测试方法中调用 `os._exit()`、`sys.exit()` 或 `QApplication.quit()`，会导致测试中止，建议使用线程或子进程。

## 多国语言

相关文件：

- `common/factorytest/lang.py`
- `common/factorytest/languages.json`

支持语言：`zh`（中文）、`en`（英文），默认中文，可通过 `lang.py` 中的 `_current_lang` 修改。

---

## 开发指南

### 新增板型

**第一步：创建板型目录**

参照已有板型（如 `boards/k3-com260/`）在 `boards/` 下创建新目录，目录名即板型名称：

```
boards/<board-name>/
├── board.py
├── cricket/
├── stability
├── tests/
│   ├── __init__.py
│   ├── auto/
│   │   └── __init__.py
│   └── manual/
│       └── __init__.py
└── utils/
```

**第二步：填写 board.py**

`COMPATIBLE` 从板子的`/proc/device-tree/compatible`节点读取对应字符串，`<board-name>` 必须与 `boards/` 下的目录名称保持一致，例如：

```python
COMPATIBLE = 'spacemit, xxxx'
BOARD_NAME = '<board-name>'
```

**第三步：添加测试用例**

按照上文"测试项"规则在 `tests/auto/` 和 `tests/manual/` 下添加测试文件。

如需根据运行环境区分行为Buildroot和Bianbu，从框架导入 `is_buildroot()`：

```python
from utils import is_buildroot
```

**第四步：配置 Buildroot**

三者的对应关系：`<board-name>` 是 `boards/` 下的目录名，`BR2_PACKAGE_FACTORYTEST_BOARD` 的值必须与之完全一致，`<BOARD_MACRO>` 是对应的大写 kconfig 符号名（连字符替换为下划线）。构建时 `factorytest.mk` 通过 `BR2_PACKAGE_FACTORYTEST_BOARD` 拼接路径 `boards/$(BR2_PACKAGE_FACTORYTEST_BOARD)/`，三者必须严格匹配。

需要修改以下两处：

1. `buildroot-ext/package/factorytest/Config.in` 的 `choice` 块中新增一条选项：
   ```kconfig
   config BR2_PACKAGE_FACTORYTEST_BOARD_<BOARD_MACRO>
   	bool "<board-name>"
   ```
   并在 `BR2_PACKAGE_FACTORYTEST_BOARD` 的 `string` 块中补充对应的 `default`：
   ```kconfig
   default "<board-name>"  if BR2_PACKAGE_FACTORYTEST_BOARD_<BOARD_MACRO>
   ```

2. `factorytest.mk` 一般无需修改。

**第五步：配置 Debian 打包**

需要修改以下三处，参照已有板型：

1. `debian/rules`：在 `BOARDS` 变量中追加 `<board-name>`：
   ```makefile
   BOARDS := k3-pico-itx k3-com260 k3-com260-kit k3-com260-ifx <board-name>
   ```
2. `debian/control`：新增 `Package: spacemit-factorytest-<board-name>` 段。
3. 新建 `debian/spacemit-factorytest-<board-name>.preinst` 和 `debian/spacemit-factorytest-<board-name>.prerm` 脚本。

---

### 在 Buildroot 上运行

在芯片对应的 `plt_defconfig` 中启用 `BR2_PACKAGE_FACTORYTEST` 并设置板型：

```
BR2_PACKAGE_FACTORYTEST=y
BR2_PACKAGE_FACTORYTEST_BOARD_<BOARD_MACRO>=y
```

构建系统会将对应板型目录的文件打包进根文件系统的 `/opt/factorytest/`。系统启动后由 weston 自动拉起 `gui-main`，无需手动操作。

---

### 在 Bianbu 上运行

前提：系统已存在普通用户（假设为`bianbu`，uid 1000），Wayland 会话已启动。

以 root 身份执行：

```bash
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-0
export QT_QPA_PLATFORM=wayland
export QT_QPA_PLATFORM_PLUGIN_PATH=/usr/lib/qt/plugins/platforms
export PYTHONPATH=/opt/factorytest/common/factorytest:/opt/factorytest/cricket:/opt/factorytest:/opt/factorytest/tests

/opt/factorytest/gui-main
```

`XDG_RUNTIME_DIR` 和 `WAYLAND_DISPLAY` 指向 `bianbu` 用户的 Wayland socket，root 进程需要借助该 socket 连接显示服务器。

## TODO

- 支持命令行
