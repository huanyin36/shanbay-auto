# shanbay-auto

扇贝单词每日自动刷词脚本。纯 API 调用，无需浏览器，1秒完成每日背词任务。

## 原理

通过 [rookiepy](https://github.com/lwouis/rookiepy) 从本机 Edge 浏览器提取已登录的扇贝 cookie，直接调用扇贝内部 API 将当日全部词条标记为"认识"，跳过浏览器渲染和 UI 交互。

## 安装

```bash
pip install -r requirements.txt
```

## 使用

1. 确保已在 Edge 浏览器中登录 [web.shanbay.com](https://web.shanbay.com)
2. 运行：

```bash
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
