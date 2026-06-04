# V4 Hierarchical Labels

The V4 output keeps the required hierarchy:

```text
教学参考病症判断：<最小病症>（<大方向> > <中方向>）。
最小病症：<最小病症>。
逻辑链：<evidence> -> <rule> -> <大方向> -> <中方向> -> <最小病症>。
```

For the authorized newtraining DICOM set, V4 can output combined teaching labels such as:

```text
瓣膜性心脏病 > 多瓣膜轻度反流 > 轻度三尖瓣反流伴轻度二尖瓣反流伴轻度主动脉瓣反流
```

When structural proxies are also triggered, V4 appends cautious teaching-reference phrases such as:

```text
左室收缩功能减低待排
节段性室壁运动异常待排
左房增大倾向
```

These are educational proxy labels and must be reviewed through formal echocardiography workflow.
