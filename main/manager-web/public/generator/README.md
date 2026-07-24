# 语音盒子主题自定义

## 项目概述

本目录包含从 [xiaozhi-assets-generator](https://github.com/xinnan-tech/xiaozhi-assets-generator) 项目打包的静态文件，用于语音盒子主题的在线自定义与生成。用户可以通过此工具配置唤醒词、字体、表情和聊天背景等元素，并导出为 `assets.bin` 文件。

## 目录结构

```
generator/
├── assets/              # 构建生成的资源文件
│   ├── ft_render-ByO_jG18.js
│   ├── index-CYcyz9xb.js
│   └── index-NXxBVrod.css
├── static/              # 静态资源目录
│   ├── charsets/        # 字符集文件
│   │   ├── deepseek.txt
│   │   ├── gb2312.txt
│   │   ├── latin1.txt
│   │   └── qwen18409.txt
│   ├── fonts/           # 字体资源
│   │   ├── font_noto_qwen_14_1.bin
│   │   ├── font_noto_qwen_16_4.bin
│   │   ├── font_noto_qwen_20_4.bin

# Voice Box Theme Customization / การปรับแต่งธีมกล่องเสียง (Voice Box)

## Project Overview / ภาพรวมโครงการ

**[EN]** This directory contains static files packaged from the [xiaozhi-assets-generator](https://github.com/xinnan-tech/xiaozhi-assets-generator) project, designed for online customization and generation of Voice Box themes. Users can utilize this tool to configure elements such as wake words, fonts, expressions, and chat backgrounds, and export them as an `assets.bin` file.

**[TH]** ไดเรกทอรีนี้ประกอบด้วยไฟล์สแตติกที่แพ็กรวมมาจากโครงการ [xiaozhi-assets-generator](https://github.com/xinnan-tech/xiaozhi-assets-generator) สำหรับใช้ในการปรับแต่งและสร้างธีมกล่องเสียง (Voice Box) แบบออนไลน์ ผู้ใช้สามารถใช้เครื่องมือนี้ในการกำหนดค่าคำปลุก (Wake Word), ฟอนต์, อิโมจิ/สีหน้า และพื้นหลังแชท พร้อมทั้งส่งออกเป็นไฟล์ `assets.bin` ได้

## Directory Structure / โครงสร้างไดเรกทอรี

```
generator/
├── assets/              # Build generated asset files / ไฟล์ทรัพยากรที่สร้างจากการบิลด์
│   ├── ft_render-ByO_jG18.js
│   ├── index-CYcyz9xb.js
│   └── index-NXxBVrod.css
├── static/              # Static assets directory / ไดเรกทอรีทรัพยากรสแตติก
│   ├── charsets/        # Character set files / ไฟล์ชุดตัวอักษร
│   │   ├── deepseek.txt
│   │   ├── gb2312.txt
│   │   ├── latin1.txt
│   │   └── qwen18409.txt
│   ├── fonts/           # Font resources / ทรัพยากรฟอนต์
│   │   ├── font_noto_qwen_14_1.bin
│   │   ├── font_noto_qwen_16_4.bin
│   │   ├── font_noto_qwen_20_4.bin
│   │   ├── font_noto_qwen_30_4.bin
│   │   ├── font_puhui_deepseek_14_1.bin
│   │   ├── font_puhui_deepseek_16_4.bin
│   │   ├── font_puhui_deepseek_20_4.bin
│   │   ├── font_puhui_deepseek_30_4.bin
│   │   ├── noto_qwen.ttf
│   │   └── puhui_deepseek.ttf
│   ├── multinet_model/  # Custom wake word model / โมเดลคำปลุกแบบกำหนดเอง
│   │   ├── fst/
│   │   ├── mn6_cn/
│   │   ├── mn6_en/
│   │   ├── mn7_cn/
│   │   └── mn7_en/
│   ├── twemoji32/       # 32x32 expression images / ภาพอิโมจิขนาด 32x32
│   ├── twemoji64/       # 64x64 expression images / ภาพอิโมจิขนาด 64x64
│   ├── wakenet_model/   # Preset wake word model / โมเดลคำปลุกที่ตั้งค่าไว้ล่วงหน้า
│   └── README.md        # Static assets documentation / เอกสารอธิบายทรัพยากรสแตติก
├── index.html           # Main page / หน้าเว็บหลัก
└── README.md            # Project documentation / เอกสารอธิบายโครงการ
```

## Main Features / คุณสมบัติหลัก

### 1. Chip and Screen Configuration / การกำหนดค่าชิปและหน้าจอ

**[EN]**
- Supports various chip models: ESP32-S3, ESP32-C3, ESP32-P4, ESP32-C6
- Flexible screen resolution settings
- Supports RGB565 color format

**[TH]**
- รองรับชิปหลายรุ่น: ESP32-S3, ESP32-C3, ESP32-P4, ESP32-C6
- ตั้งค่าความละเอียดหน้าจอได้อย่างยืดหยุ่น
- รองรับรูปแบบสี RGB565

---

### 2. Wake Word Configuration / การกำหนดค่าคำปลุก (Wake Word)

**[EN]**
- **Preset Wake Words**: Based on WakeNet models supported by different chips
- **Custom Wake Words**: Supports Chinese and English command words with configurable threshold and timeout settings

**[TH]**
- **คำปลุกตั้งต้น (Preset Wake Words)**: อิงตามโมเดล WakeNet ที่รองรับในชิปแต่ละรุ่น
- **คำปลุกแบบกำหนดเอง (Custom Wake Words)**: รองรับคำสั่งภาษาจีนและภาษาอังกฤษ สามารถตั้งค่าเกณฑ์ (Threshold) และเวลาหมดเวลา (Timeout) ได้

---

### 3. Font Configuration / การกำหนดค่าฟอนต์

**[EN]**
- Presets multiple fonts: Alibaba PuHuiTi, Noto Qwen, etc.
- Supports uploading custom TTF/WOFF font files
- Configurable font size and color depth (bpp)

**[TH]**
- มีฟอนต์สำเร็จรูปให้เลือก เช่น Alibaba PuHuiTi, Noto Qwen เป็นต้น
- รองรับการอัปโหลดไฟล์ฟอนต์ TTF/WOFF แบบกำหนดเอง
- สามารถตั้งค่าขนาดฟอนต์และความลึกของสี (bpp) ได้

---

### 4. Expression Set / ชุดอิโมจิ / สีหน้า (Expressions)

**[EN]**
- Provides preset schemes with 21 basic expressions (available in 32x32 and 64x64 sizes)
- Supports custom expression uploads

**[TH]**
- มีชุดพรีเซ็ตอิโมจิพื้นฐาน 21 แบบ (ให้เลือกทั้งขนาด 32x32 และ 64x64)
- รองรับการอัปโหลดอิโมจิแบบกำหนดเอง

---

### 5. Chat Background / พื้นหลังห้องแชท

**[EN]**
- Supports switching between light and dark modes
- Configurable solid color backgrounds or image backgrounds
- Automatically adapts to screen resolution

**[TH]**
- รองรับการสลับโหมดสว่าง (Light Mode) และโหมดมืด (Dark Mode)
- ตั้งค่าพื้นหลังเป็นสีเรียบหรือรูปภาพได้
- ปรับขนาดให้เข้ากับความละเอียดหน้าจอโดยอัตโนมัติ

## How to Use / วิธีการใช้งาน

**[EN]**
1. Start the `index.html` file as a HTTP service
2. Select the chip model and screen configuration
3. Configure theme elements through different tabs
4. Click the generate button to view the asset manifest
5. After confirmation, generate and download the `assets.bin` file

**[TH]**
1. เริ่มการทำงานไฟล์ `index.html` ในรูปแบบบริการเว็บ (Web Service/Server)
2. เลือกรุ่นชิปและการกำหนดค่าหน้าจอ
3. ปรับแต่งองค์ประกอบของธีมผ่านแท็บต่างๆ
4. คลิกปุ่มสร้าง (Generate) เพื่อดูรายการทรัพยากร
5. ยืนยันเพื่อสร้างและดาวน์โหลดไฟล์ `assets.bin`

## Technical Notes / คำอธิบายทางเทคนิค

**[EN]**
- The built static assets are located in the `assets/` directory
- Original models and asset files are located in the `static/` directory
- Supports offline usage with no additional dependencies required

**[TH]**
- ทรัพยากรสแตติกหลังจากการบิลด์จะอยู่ที่ไดเรกทอรี `assets/`
- โมเดลและไฟล์ทรัพยากรต้นฉบับจะอยู่ที่ไดเรกทอรี `static/`
- รองรับการใช้งานแบบออฟไลน์โดยไม่ต้องใช้ทรัพยากรภายนอกเพิ่มเติม

## Precautions / ข้อควรระวัง

**[EN]**
- This tool is designed for offline use; all resources are already included in the directory
- The generated `assets.bin` file needs to be used in conjunction with the Voice Box hardware
- Pay attention to file formats and size limits for custom assets to ensure compatibility

**[TH]**
- เครื่องมือนี้ได้รับการออกแบบมาสำหรับการใช้งานออฟไลน์ ทรัพยากรทั้งหมดรวมอยู่ในไดเรกทอรีแล้ว
- ไฟล์ `assets.bin` ที่สร้างขึ้นจะต้องนำไปใช้งานร่วมกับอุปกรณ์ฮาร์ดแวร์กล่องเสียง (Voice Box)
- การใช้ทรัพยากรแบบกำหนดเองต้องระมัดระวังเรื่องรูปแบบไฟล์และข้อจำกัดด้านขนาดเพื่อให้มั่นใจว่าสามารถใช้งานร่วมกันได้

│   │   ├── font_noto_qwen_30_4.bin
│   │   ├── font_puhui_deepseek_14_1.bin
│   │   ├── font_puhui_deepseek_16_4.bin
│   │   ├── font_puhui_deepseek_20_4.bin
│   │   ├── font_puhui_deepseek_30_4.bin
│   │   ├── noto_qwen.ttf
│   │   └── puhui_deepseek.ttf
│   ├── multinet_model/  # 自定义唤醒词模型
│   │   ├── fst/
│   │   ├── mn6_cn/
│   │   ├── mn6_en/
│   │   ├── mn7_cn/
│   │   └── mn7_en/
│   ├── twemoji32/       # 32x32 表情图片
│   ├── twemoji64/       # 64x64 表情图片
│   ├── wakenet_model/   # 预设唤醒词模型
│   └── README.md        # 静态资源说明
├── index.html           # 主页面
└── README.md            # 项目说明文档
```

## 主要功能

### 1. 芯片与屏幕配置
- 支持多种芯片型号：ESP32-S3、ESP32-C3、ESP32-P4、ESP32-C6
- 灵活的屏幕分辨率设置
- 支持 RGB565 颜色格式

### 2. 唤醒词配置
- **预设唤醒词**：基于不同芯片支持的 WakeNet 模型
- **自定义唤醒词**：支持中文和英文命令词，可配置阈值和超时时间

### 3. 字体配置
- 预设多种字体：阿里巴巴普惠体、Noto Qwen 等
- 支持上传自定义 TTF/WOFF 字体文件
- 可配置字号和颜色深度（bpp）

### 4. 表情集合
- 提供 21 种基础表情的预设方案（32x32 和 64x64 两种尺寸）
- 支持自定义表情上传

### 5. 聊天背景
- 支持浅色/深色模式切换
- 可配置纯色背景或图片背景
- 自动适配屏幕分辨率

## 使用方法

1. 以服务方式启动 `index.html` 文件
2. 选择芯片型号和屏幕配置
3. 通过不同标签页配置主题元素
4. 点击生成按钮查看资源清单
5. 确认后生成并下载 `assets.bin` 文件

## 技术说明

- 构建后的静态资源位于 `assets/` 目录
- 原始模型和资源文件位于 `static/` 目录
- 支持离线使用，无需额外依赖

## 注意事项

- 本工具为离线使用设计，所有资源已包含在目录中
- 生成的 `assets.bin` 文件需要与语音盒子硬件配合使用
- 自定义资源需注意文件格式和大小限制，以确保兼容

