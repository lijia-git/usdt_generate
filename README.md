# USDT靓号生成器 (USDT Vanity Address Generator)

一个基于 GPU 加速的 USDT (TRC20) 靓号地址生成器，支持助记词和私钥两种生成方式。使用 PyQt6 构建了现代化的图形界面，支持实时显示生成速度、进度等信息。

## ✨ 主要特性

- 🚀 GPU 加速支持，自动选择最优计算设备(支持 NVIDIA/Apple Silicon/AMD)
- 💻 美观的图形用户界面
- 📝 支持助记词和私钥两种生成模式
- 🎯 支持多个靓号模式同时匹配
- 🔄 实时显示生成速度和进度
- 💾 自动保存生成结果
- 🔔 生成完成提示音

## 🛠️ 安装

### 环境要求
- Python 3.7+
- OpenCL 支持的显卡驱动

### 安装依赖
pip install PyQt6 pyOpenCL tronpy mnemonic playsound

## 🚀 使用方法

1. 克隆项目
git clone https://github.com/your-username/usdt-vanity-address-generator.git
cd usdt-vanity-address-generator

2. 运行程序
python main_gui.py

3. 在界面中:
   - 选择生成模式(助记词/私钥)
   - 输入靓号模式(如: 888,666,999)
   - 设置生成数量
   - 点击"开始生成"

## 📝 结果保存

- 生成的地址会自动保存到 found_addresses.json 文件中
- 可以通过界面的"查看结果"按钮查看已生成的靓号

## ⚠️ 注意事项

- 生成速度取决于您的硬件配置
- 靓号位数越多,生成时间越长
- 请妥善保管生成的私钥/助记词
- 建议定期备份生成结果

## 📜 许可证

[MIT License](LICENSE)

## 免责声明

本程序仅供学习研究使用，请勿用于非法用途。使用本程序生成的地址时请注意资产安全。

usdt靓号生成器，使用gpu显卡加速，trc20协议支持助记词和私钥两种方式。
![image](https://github.com/user-attachments/assets/71baf653-6ed5-4969-9dfd-d94c270d635c)
![image](https://github.com/user-attachments/assets/0e7c02b5-33ed-42a9-afc8-ffb8dc5df2dc)