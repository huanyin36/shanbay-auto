# shanbay-auto

扇贝单词每日自动刷词脚本。纯 API 调用，无需浏览器，1秒完成每日背词任务。

## 原理

通过 Chrome DevTools Protocol (CDP) 直接从运行中的 Edge 进程读取已登录的扇贝 cookie，直接调用扇贝内部 API 将当日全部词条标记为"认识"，跳过浏览器渲染和 UI 交互。

> **注意**：新版 Edge 更改了 cookie 加密格式（32字节裸 AES 密钥），传统解密方式（如 rookiepy）已失效。本方案使用 CDP 完全绕过解密，直接从浏览器内存获取 cookie。

## 快速开始（推荐）

1. 安装 [Python](https://www.python.org)，安装时勾选 **Add python.exe to PATH**
2. 在 Edge 浏览器登录 [web.shanbay.com](https://web.shanbay.com)
3. **建议将 Edge 设置为开机自启**（脚本需要连接运行中的 Edge 进程）
4. 双击 `install.bat`

`install.bat` 会自动安装依赖（含 `websocket-client`），并创建登录触发的计划任务 `ShanbayDaily`。之后每次开机登录自动刷词，同一天只跑一次（由 `.shanbay_state.json` 去重，失败当天可重试）。

> **重要**：脚本运行时 Edge 必须处于运行状态（CDP 需要连接活跃的浏览器进程）。

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
[*] 扇贝单词自动刷词 v3 (API)
[+] Cookie 有效
[*] 今日任务: 40 新词 + 0 复习
[+] 完成！40 新词 + 0 复习，全部标记为认识
```

## 注意事项

- 仅支持 Windows + Edge（CDP 需连接运行中的 Edge 进程）
- **脚本运行时 Edge 必须处于运行状态**
- Edge 中扇贝登录态过期后需重新登录一次
- 所有词条标记为"认识"，适合刷量/打卡场景，不适合真正背词
- 请自行评估使用风险

## License

MIT
