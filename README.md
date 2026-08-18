# shanbay-auto

扇贝单词每日自动刷词脚本。纯 API 调用，无需浏览器操作，1 秒完成每日背词任务。

## 原理

通过 Chrome DevTools Protocol (CDP) 直接从运行中的浏览器进程读取已登录的扇贝 cookie，调用扇贝内部 API 将当日全部词条标记为"认识"，跳过浏览器渲染和 UI 交互。

> **为什么用 CDP？** 新版 Edge 更改了 cookie 加密格式（32 字节裸 AES 密钥），传统解密方式（如 rookiepy）已失效。本方案使用 CDP 完全绕过解密，直接从浏览器内存获取 cookie。

## 特性

- **纯 API 调用**，不渲染页面、不模拟点击，1 秒完成
- **CDP 提取 cookie**，绕过 Edge 新版加密，无需手动复制
- **支持 Edge 和 Chrome**，安装时自由选择
- **浏览器自动启动**，未运行时自动拉起并附加调试端口
- **自动重试**，网络请求失败时指数退避重试 3 次
- **学习时间随机化**，每词 3-8 秒随机，降低风控风险
- **日志自动清理**，每周清理超过 7 天的日志
- **日志脱敏**，自动屏蔽 cookie、token 等敏感信息
- **每日去重**，同一天只执行一次，失败可重试
- **开机自启**，安装计划任务，登录后自动运行

## 快速开始（推荐）

1. 安装 [Python](https://www.python.org)，安装时勾选 **Add python.exe to PATH**
2. 在浏览器中登录 [web.shanbay.com](https://web.shanbay.com)
3. 双击 `install.bat`

`install.bat` 会引导你完成以下步骤：

```
============================================
  shanbay-auto installer
============================================

[1/4] Checking Python...
[2/4] Installing dependencies...
[3/4] Choose browser...

  1) Edge  (default)
  2) Chrome

Select browser [1/2] (default 1):
[4/4] Creating logon scheduled task...
```

安装完成后，每次开机登录后延迟 45 秒自动执行（等待网络就绪和浏览器启动），同一天只跑一次。

> **提示**：浏览器选择会保存到 `.shanbay_config.json`，之后自动读取。如需更换浏览器，重新运行 `install.bat` 即可。

- 手动跑一次：双击 `run.bat`
- 运行日志：`shanbay.log`
- 移除自启：双击 `uninstall.bat`

## 手动方式

```bash
pip install -r requirements.txt
python shanbay.py
```

输出示例：

```
[*] 扇贝单词自动刷词 v4 (CDP+API) - Edge
[*] 浏览器未运行，正在启动 Edge 并附加调试端口...
[+] Edge 调试端口就绪
[+] Cookie 有效
[*] 今日任务: 40 新词 + 0 复习
[+] 完成！40 新词 + 0 复习，全部标记为认识
```

## 配置

### 浏览器选择

通过以下方式指定浏览器（优先级从高到低）：

1. **环境变量** `SHANBAY_BROWSER`（值为 `edge` 或 `chrome`）
2. **配置文件** `.shanbay_config.json`（`install.bat` 自动生成）
3. **默认** Edge



## 注意事项

- 支持 Windows + Edge 或 Chrome（CDP 需连接运行中的浏览器进程）
- 浏览器未运行时脚本会自动启动，但需在浏览器中保持扇贝登录态
- 浏览器中扇贝登录态过期后需重新登录一次
- 所有词条标记为"认识"，适合刷量/打卡场景，不适合真正背词
- 脚本会通过 CDP 开启浏览器远程调试端口（9222），仅用于本地提取 cookie
- 请自行评估使用风险

## 更新日志

### v4.1

- 🔒 WebSocket 通信增加 10 秒超时保护，避免脚本无限挂起
- 🔒 日志脱敏扩展：覆盖 `sessionid`、`auth_token` 等敏感字段
- 🔁 网络请求增加 3 次指数退避重试，提升 API 偶发故障时的稳定性
- 📊 学习时间随机化（每词 3-8 秒），降低风控检测风险
- 🧹 `get_session()` 改为抛异常而非 `sys.exit()`，便于调用方统一处理
- 🧹 移除硬编码的 D 盘便携版路径，改用 `SHANBAY_EDGE_PATH` 环境变量
- 🧹 `get_book_id()` 失败时不再静默 fallback，改为明确报错
- 🧹 修复 `.gitignore` 中重复的 `*.log` 规则
- ⏱️ 计划任务登录触发增加 45 秒延迟，等待网络就绪和 Edge 启动

## License

MIT
