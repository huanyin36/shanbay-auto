# shanbay-auto

扇贝单词每日自动刷词脚本。纯 API 调用，无需浏览器，1秒完成每日背词任务。

## 原理

通过 [rookiepy](https://github.com/lwouis/rookiepy) 从本机 Edge 浏览器提取已登录的扇贝 cookie，直接调用扇贝内部 API 将当日全部词条标记为"认识"，跳过浏览器渲染和 UI 交互。

## 快速开始（推荐）

1. 安装 [Python](https://www.python.org)，安装时勾选 **Add python.exe to PATH**
2. 在 Edge 浏览器登录 [web.shanbay.com](https://web.shanbay.com)
3. 双击 `install.bat`

`install.bat` 会自动安装依赖，并创建登录触发的计划任务 `ShanbayDaily`。之后每次开机登录自动刷词，同一天只跑一次（由 `.shanbay_state.json` 去重，失败当天可重试）。

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

- 仅支持 Windows + Edge（rookiepy 从 Edge 的 cookie 数据库提取凭证）
- Edge 中扇贝登录态过期后需重新登录一次
- 所有词条标记为"认识"，适合刷量/打卡场景，不适合真正背词
- 请自行评估使用风险

## License

MIT
