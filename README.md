# 电工五班作业收发机器人

A Python-based QQ bot for automated homework collection, packaging, and secure return distribution.

基于 QQ 机器人的班级作业自动收发系统，支持学生提交作业、管理员打包导出、老师返还文件批量导入、学生按身份查询并领取自己的返还文件。
注意：本工程仅用于电子科技大学格拉斯哥学院2025级电子信息工程五班的收发作业，纯粹是收作业太（懒）麻（得）烦（收）而开发的。若他人想要使用，记得修改.env文件，并自己附带班级学号名单的CSV文件
记得还要创立logs,exports,storage三个文件夹，storage有三个下级文件夹，分别是archive，inbox和temp。

---

## 项目简介

这个项目用于解决班级作业管理中常见的几个问题：

- 学生提交格式混乱，文件命名不统一
- 不同老师对文件命名模板要求不同
- 学委需要按类别和批次整理大量 PDF
- 老师返还的是整包 zip，人工拆分和分发效率低
- 学生不应该看到别人的返还文件或成绩
- 学委需要快速导出已交 / 缺交名单

---

## 功能特性

### 学生端
- 提交作业信息
- 上传 PDF 文件
- 学号姓名自动校验
- 自动重命名与归档
- 查询并领取返还文件

### 管理员端
- 打包导出作业
- 导入老师返还 zip
- 自动匹配返还文件
- 导出已交名单 / 缺交名单
- 查看未匹配文件
- 手动匹配文件

---

## 项目结构

qq-homework-bot/
├─ app/
├─ data/
├─ storage/
├─ exports/
├─ logs/
├─ .env
└─ README.md

---

## 安装依赖

pip install qq-botpy python-dotenv httpx pandas openpyxl

---

## 配置 .env

BOT_APPID=你的AppID  
BOT_APPSECRET=你的AppSecret  
BOT_USE_SANDBOX=true  
ADMIN_OPENID=你的openid  

---

## 启动

python -m app.main

---

## 学生使用

提交：

提交 <类别> <批次> <学号> <姓名>

例如：

提交 大物实验 实验2 2025xxxxxxxxxx 张三  

然后发送 PDF

查询：

查询 <类别> <批次>

---

## 管理员使用

打包：

/打包 <类别> <批次>

导入返还：

/导入返还 <类别> <批次>

已交：

/已交 <类别> <批次>

缺交：

/缺交 <类别> <批次>

未匹配：

/未匹配 <类别> <批次>

手动匹配：

/手动匹配 <类别> <批次> <学号> <文件名>

---

## 核心设计

- openid 自动绑定学号
- 学生只能获取自己的返还文件
- 支持多课程、多批次、多命名模板
- 自动记录提交与返还

---

## 部署建议

- 腾讯云轻量服务器
- Ubuntu 24.04
- systemd 常驻运行

---

## License

仅用于教学与班级作业管理
MIT Lisence
