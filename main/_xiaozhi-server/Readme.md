[![Banners](docs/images/banner1.png)](https://github.com/xinnan-tech/xiaozhi-esp32-server)

<h1 align="center">Xiaozhi Backend Service xiaozhi-esp32-server</h1>

<p align="center">
This project develops an intelligent terminal hardware and software system based on the theory and technology of human-machine symbiotic intelligence<br/>providing backend services for the open-source intelligent hardware project
<a href="https://github.com/78/xiaozhi-esp32">xiaozhi-esp32</a><br/>
Implemented using Python, Java, and Vue according to the <a href="https://ccnphfhqs21z.feishu.cn/wiki/M0XiwldO9iJwHikpXD5cEx71nKh">Xiaozhi Communication Protocol</a><br/>
Supports MQTT+UDP protocols, Websocket protocol, MCP access points, voiceprint recognition, and knowledge base
</p>

<p align="center">
<a href="./docs/FAQ.md">FAQ</a>
· <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/issues">Feedback</a>
· <a href="./README.md#%E9%83%A8%E7%BD%B2%E6%96%87%E6%A1%A3">Deployment Docs</a>
· <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/releases">Changelog</a>
</p>

<p align="center">
  <a href="./README.md"><img alt="Simplified Chinese README" src="https://img.shields.io/badge/Simplified_Chinese-DBEDFA"></a>
  <a href="./docs/readme/README_en.md"><img alt="README in English" src="https://img.shields.io/badge/English-DFE0E5"></a>
  <a href="./docs/readme/README_vi.md"><img alt="Tiếng Việt" src="https://img.shields.io/badge/Tiếng_Việt-DFE0E5"></a>
  <a href="./docs/readme/README_de.md"><img alt="Deutsch" src="https://img.shields.io/badge/Deutsch-DFE0E5"></a>
  <a href="./docs/readme/README_pt_BR.md"><img alt="Português (Brasil)" src="https://img.shields.io/badge/Português_(Brasil)-DFE0E5"></a>
  <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/releases">
    <img alt="GitHub Contributors" src="https://img.shields.io/github/v/release/xinnan-tech/xiaozhi-esp32-server?logo=docker" />
  </a>
  <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/LICENSE">
    <img alt="GitHub pull requests" src="https://img.shields.io/badge/license-MIT-white?labelColor=black" />
  </a>
  <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server">
    <img alt="stars" src="https://img.shields.io/github/stars/xinnan-tech/xiaozhi-esp32-server?color=ffcb47&labelColor=black" />
  </a>
</p>

<p align="center">
Spearheaded by Professor Siyuan Liu's Team (South China University of Technology)
</br>
Led and developed by Professor Siyuan Liu's Team (South China University of Technology)
</br>
<img src="./docs/images/hnlg.jpg" alt="South China University of Technology" width="50%">
</p>

---

## Target Audience 👥

This project needs to be used with ESP32 hardware devices. If you have already purchased ESP32 related hardware, successfully connected to the backend service deployed by Brother Xia, and wish to independently build your own `xiaozhi-esp32` backend service, then this project is perfect for you.

Want to see it in action? Click the videos below 🎥

<table>
  <tr>
    <td>
      <a href="https://www.bilibili.com/video/BV1FMFyejExX" target="_blank">
        <picture>
          <img alt="Experience Response Speed" src="docs/images/demo9.png" /></picture>
      </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1vchQzaEse" target="_blank">
        <picture>
          <img alt="Speed Optimization Secrets" src="docs/images/demo6.png" /></picture>
      </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1WEcxzFEAT" target="_blank">
        <picture>
          <img alt="Xiaozhi Digital Human Supports Voice Wake-up" src="docs/images/demo8.png" /></picture>
      </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1CKVz6UEuB" target="_blank">
        <picture>
          <img alt="Device to Device Calling, Phone Calls" src="docs/images/demo0.png" /></picture>
      </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1C1tCzUEZh" target="_blank">
        <picture>
          <img alt="Complex Medical Scenarios" src="docs/images/demo1.png" /></picture>
      </a>
    </td>
  </tr>
  <tr>
    <td>
      <a href="https://www.bilibili.com/video/BV1VC96Y5EMH" target="_blank">
        <picture>
          <img alt="Play Music, Check Weather, Broadcast News" src="docs/images/demo7.png" /></picture>
      </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV12J7WzBEaH" target="_blank">
        <picture>
          <img alt="Real-time Interruption" src="docs/images/demo10.png" /></picture>
      </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1Co76z7EvK" target="_blank">
        <picture>
          <img alt="Take Photos to Identify Objects" src="docs/images/demo12.png" /></picture>
      </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1pNXWYGEx1" target="_blank">
        <picture>
          <img alt="Control Home Appliance Switches" src="docs/images/demo5.png" /></picture>
      </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1TJ7WzzEo6" target="_blank">
        <picture>
          <img alt="Multi-instruction Tasks" src="docs/images/demo11.png" /></picture>
      </a>
    </td>
  </tr>
  <tr>
    <td>
      <a href="https://www.bilibili.com/video/BV1ZQKUzYExM" target="_blank">
        <picture>
          <img alt="MCP Access Point" src="docs/images/demo13.png" /></picture>
      </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1zUW5zJEkq" target="_blank">
        <picture>
          <img alt="MQTT Instruction Issuance" src="docs/images/demo4.png" /></picture>
      </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1Exu3zqEDe" target="_blank">
        <picture>
          <img alt="Voiceprint Recognition" src="docs/images/demo14.png" /></picture>
      </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1CDKWemEU6" target="_blank">
        <picture>
          <img alt="Custom Voice Timbre" src="docs/images/demo2.png" /></picture>
      </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV12yA2egEaC" target="_blank">
        <picture>
          <img alt="Communicate in Cantonese" src="docs/images/demo3.png" /></picture>
      </a>
    </td>
  </tr>
</table>

---

## Warning ⚠️

1. This project is open-source software. There is no commercial cooperative relationship between this software and any connected third-party API service providers (including but not limited to voice recognition, large models, voice synthesis, and other platforms). We do not provide any form of guarantee for their service quality and fund security. It is recommended that users give priority to service providers holding relevant business licenses and carefully read their service agreements and privacy policies. This software does not host any account keys, does not participate in capital circulation, and does not bear the risk of recharge fund loss.

2. The functions of this project are not yet perfect and have not passed network security assessments. Please do not use it in a production environment. If you deploy and study this project in a public network environment, please be sure to take necessary protective measures.

---

## Deployment Documentation

![Banners](docs/images/banner2.png)

This project provides two deployment methods, please choose according to your specific needs:

#### 🚀 Deployment Method Selection
| Deployment Method | Features | Applicable Scenarios | Deployment Docs | Configuration Requirements | Video Tutorials | 
|---------|------|---------|---------|---------|---------|
| **Simplified Installation** | Intelligent Dialogue, Single Agent Management | Low-configuration environment, data stored in configuration files, no database required | [①Docker Version](./docs/Deployment.md#%E6%96%B9%E5%BC%8F%E4%B8%80docker%E5%8F%AA%E8%BF%90%E8%A1%8Cserver) / [②Source Code Deployment](./docs/Deployment.md#%E6%96%B9%E5%BC%8F%E4%BA%8C%E6%9C%AC%E5%9C%B0%E6%BA%90%E7%A0%81%E5%8F%AA%E8%BF%90%E8%A1%8Cserver)| 2 cores 4G if using `FunASR`, 2 cores 2G if using full API | - | 
| **Full Module Installation** | Intelligent Dialogue, Multi-user Management, Multi-agent Management, Intelligent Control Console Interface Operations | Complete feature experience, data stored in database |[①Docker Version](./docs/Deployment_all.md#%E6%96%B9%E5%BC%8F%E4%B8%80docker%E8%BF%90%E8%A1%8C%E5%85%A8%E6%A8%A1%E5%9D%97) / [②Source Code Deployment](./docs/Deployment_all.md#%E6%96%B9%E5%BC%8F%E4%BA%8C%E6%9C%AC%E5%9C%B0%E6%BA%90%E7%A0%81%E8%BF%90%E8%A1%8C%E5%85%A8%E6%A8%A1%E5%9D%97) / [③Source Code Deployment Auto-update Tutorial](./docs/dev-ops-integration.md) | 4 cores 8G if using `FunASR`, 2 cores 4G if using full API| [Local Source Code Startup Video Tutorial](https://www.bilibili.com/video/BV1wBJhz4Ewe) | 

For FAQs and related tutorials, please refer to [this link](./docs/FAQ.md)

> 💡 Tip: The following is the test platform deployed with the latest code. You can flash and test it if needed. The concurrency is 6, and the data will be cleared every day.

Intelligent Control Console Address: https://2662r3426b.vicp.fun
Intelligent Control Console (H5 version): https://2662r3426b.vicp.fun/h5/index.html

```
Service Testing Tool: https://2662r3426b.vicp.fun/test/
OTA API Address: https://2662r3426b.vicp.fun/xiaozhi/ota/
Websocket API Address: wss://2662r3426b.vicp.fun/xiaozhi/v1/
```

#### 🚩 Configuration Instructions and Recommendations
> [!Note]
> This project provides two configuration schemes:
> 
> 1. `Entry-level All-Free Configuration`: Suitable for personal home use, all components use free solutions, no extra payment required.
> 
> 2. `Streaming Configuration`: Suitable for demonstrations, training, and scenarios with more than 2 concurrencies. Uses streaming processing technology for faster response speed and better experience.
> 
> Starting from version `0.5.2`, the project supports streaming configuration. Compared to earlier versions, the response speed is improved by about `2.5 seconds`, significantly improving the user experience.

| Module Name | Entry-level All-Free Settings | Streaming Configuration |
|:---:|:---:|:---:|
| ASR (Voice Recognition) | FunASR (Local) | 👍XunfeiStreamASR (iFlytek Streaming) |
| LLM (Large Language Model) | glm-4-flash (Zhipu) | 👍qwen-flash (Alibaba Bailian) |
| VLLM (Vision Large Model) | glm-4v-flash (Zhipu) | 👍qwen3.5-flash (Alibaba Bailian) |
| TTS (Text-to-Speech) | EdgeTTS (Microsoft) | 👍HuoshanDoubleStreamTTS (Volcengine Streaming) |
| Intent (Intent Recognition) | function_call | function_call |
| Memory | mem_local_short (Local Short-term Memory) | mem_local_short (Local Short-term Memory) |

If you care about the time consumption of each component, please refer to the [Xiaozhi Components Performance Test Report](https://github.com/xinnan-tech/xiaozhi-performance-research), and you can actually test it in your environment according to the test methods in the report.

#### 🔧 Testing Tools
This project provides the following testing tools to help you verify the system and select the appropriate models:

| Tool Name | Location | Usage Method | Functional Description |
|:---:|:---|:---:|:---:|
| Audio Interaction Testing Tool | main > digital-human > index.html | Access `http://127.0.0.1:8006/index.html` after executing `python start.py` in `main/digital-human` | Tests audio playback and reception functions, verifies whether Python-side audio processing is normal |
| Model Response Testing Tool | main > xiaozhi-server > performance_tester.py | Execute `python performance_tester.py` | Tests the response speed of three core modules: ASR (Voice Recognition), LLM (Large Model), VLLM (Vision Model), TTS (Voice Synthesis) |

> 💡 Tip: When testing model speed, only models configured with an API key will be tested.

---
## Feature List ✨
### Implemented ✅
![Please refer to - Full Module Installation Architecture Diagram](docs/images/deploy2.png)
| Functional Module | Description |
|:---:|:---|
| Core Architecture | Based on [MQTT+UDP Gateway](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/mqtt-gateway-integration.md), WebSocket, HTTP server, providing a complete console management and authentication system |
| Voice Interaction | Supports streaming ASR (Voice Recognition), streaming TTS (Voice Synthesis), VAD (Voice Activity Detection), supports multi-language recognition and voice processing |
| Voiceprint Recognition | Supports multi-user voiceprint registration, management, and recognition, processes in parallel with ASR, recognizes speaker identity in real-time, and passes it to LLM for personalized response |
| Intelligent Dialogue | Supports various LLMs (Large Language Models) to achieve intelligent dialogue |
| Visual Perception | Supports various VLLMs (Vision Large Models) to achieve multi-modal interaction |
| Intent Recognition | Supports external large model intent recognition, autonomous function calls by large models, and provides a pluggable intent processing mechanism |
| Memory System | Supports local short-term memory, mem0ai interface memory, PowerMem intelligent memory, with memory summarization functions |
| Knowledge Base | Supports RAGFlow knowledge base, allowing the large model to determine if knowledge base scheduling is needed before answering |
| Tool Calling | Supports client IOT protocol, client MCP protocol, server MCP protocol, MCP access point protocol, and custom tool functions |
| Instruction Issuance | Relying on the MQTT protocol, supports issuing MCP instructions from the Intelligent Control Console to ESP32 devices |
| Management Backend | Provides a Web management interface, supports user management, system configuration, and device management; the interface supports Simplified Chinese, Traditional Chinese, and English displays |
| Testing Tools | Provides performance testing tools, vision model testing tools, and audio interaction testing tools |
| Deployment Support | Supports Docker deployment and local deployment, provides complete configuration file management |
| Plugin System | Supports functional plugin extension, custom plugin development, and hot loading of plugins |

### Under Development 🚧

To understand the specific development plan progress, [please click here](https://github.com/users/xinnan-tech/projects/3). For FAQs and related tutorials, please refer to [this link](./docs/FAQ.md)

If you are a software developer, here is an ["Open Letter to Developers"](docs/contributor_open_letter.md), welcome to join!

---

## Product Ecosystem 👬
Xiaozhi is an ecosystem. When you use this product, you can also take a look at other [excellent projects](https://github.com/78/xiaozhi-esp32/blob/main/README_zh.md#%E7%9B%B8%E5%85%B3%E5%BC%80%E6%BA%90%E9%A1%B9%E7%9B%AE) in this ecosystem.

---

## List of Platforms/Components Supported by this Project 📋
### LLM Language Model

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| openai API Call | Alibaba Bailian, Volcengine, DeepSeek, Zhipu, Gemini, iFlytek | Zhipu, Gemini |
| ollama API Call | Ollama | - |
| dify API Call | Dify | - |
| fastgpt API Call | Fastgpt | - |
| coze API Call | Coze | - |
| xinference API Call | Xinference | - |
| homeassistant API Call | HomeAssistant | - |

In fact, any LLM that supports openai API calls can be integrated and used.

---

### VLLM Vision Model

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| openai API Call | Alibaba Bailian, Zhipu ChatGLMVLLM | Zhipu ChatGLMVLLM |

In fact, any VLLM that supports openai API calls can be integrated and used.

---

### TTS Voice Synthesis

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| API Call | EdgeTTS, iFlytek, Volcengine, Tencent Cloud, Alibaba Cloud and Bailian, CosyVoiceSiliconflow, TTS302AI, CozeCnTTS, GizwitsTTS, ACGNTTS, OpenAITTS, Lingxi Streaming TTS, MinimaxTTS | Lingxi Streaming TTS, EdgeTTS, CosyVoiceSiliconflow (Partial) |
| Local Service | FishSpeech, GPT_SOVITS_V2, GPT_SOVITS_V3, Index-TTS, PaddleSpeech | Index-TTS, PaddleSpeech, FishSpeech, GPT_SOVITS_V2, GPT_SOVITS_V3 |

---

### VAD Voice Activity Detection

| Type  |   Platform Name    | Usage Method | Pricing Model | Remarks |
|:---:|:---------:|:----:|:----:|:--:|
| VAD | SileroVAD | Local Use |  Free  |    |

---

### ASR Voice Recognition

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| Local Use | FunASR, SherpaASR | FunASR, SherpaASR |
| API Call | FunASRServer, Volcengine, iFlytek, Tencent Cloud, Alibaba Cloud, Baidu Cloud, OpenAI ASR | FunASRServer |

---

### Voiceprint Recognition

| Usage Method | Supported Platforms | Free Platforms |
|:---:|:---:|:---:|
| Local Use | 3D-Speaker | 3D-Speaker |

---

### Memory Storage

|   Type   |      Platform Name       | Usage Method |   Pricing Model    | Remarks |
|:------:|:---------------:|:----:|:---------:|:--:|
| Memory |     mem0ai      | API Call | Quota of 1000 times/month |    |
| Memory |     [powermem](./docs/powermem-integration.md)    | Local Summarization | Depends on LLM and DB |  OceanBase Open Source, supports intelligent retrieval  |
| Memory | mem_local_short | Local Summarization |    Free     |    |
| Memory |     nomem       | No Memory Mode |    Free     |    |

---

### Intent Recognition

|   Type   |     Platform Name      | Usage Method |  Pricing Model   |          Remarks           |
|:------:|:-------------:|:----:|:-------:|:---------------------:|
| Intent |  intent_llm   | API Call | Charged according to LLM |    Recognizes intent through large models, strong universality     |
| Intent | function_call | API Call | Charged according to LLM | Completes intent through large model function calls, fast speed, good effect |
| Intent |    nointent   | No Intent Mode |    Free     |    No intent recognition performed, returns dialogue results directly     |

---

### Rag Retrieval-Augmented Generation

|   Type   |     Platform Name      | Usage Method |  Pricing Model   |          Remarks           |
|:------:|:-------------:|:----:|:-------:|:---------------------:|
| Rag |  ragflow   | API Call | Charged according to tokens consumed by slicing and tokenization |    Uses RagFlow's retrieval-augmented generation function to provide more accurate dialogue responses     |

---

## Acknowledgments 🙏

| Logo | Project/Company | Description |
|:---:|:---:|:---|
| <img src="./docs/images/logo_bailing.png" width="160"> | [Bailing Voice Dialogue Robot](https://github.com/wwbin2017/bailing) | This project was inspired by the [Bailing Voice Dialogue Robot](https://github.com/wwbin2017/bailing) and implemented on its basis. |
| <img src="./docs/images/logo_tenclass.png" width="160"> | [Shifang Ronghai](https://www.tenclass.com/) | Thanks to [Shifang Ronghai](https://www.tenclass.com/) for establishing standard communication protocols, multi-device compatibility schemes, and high-concurrency scenario practice demonstrations for the Xiaozhi ecosystem; and for providing full-link technical documentation support for this project. |
| <img src="./docs/images/logo_xuanfeng.png" width="160"> | [Xuanfeng Technology](https://github.com/Eric0308) | Thanks to [Xuanfeng Technology](https://github.com/Eric0308) for contributing the implementation code of the function call framework, MCP communication protocol, and pluggable calling mechanism. Through a standardized instruction scheduling system and dynamic expansion capabilities, the interaction efficiency and functional scalability of front-end devices (IoT) are significantly improved. |
| <img src="./docs/images/logo_junsen.png" width="160"> | [huangjunsen](https://github.com/huangjunsen0406) | Thanks to [huangjunsen](https://github.com/huangjunsen0406) for contributing the `Intelligent Control Console Mobile` module, achieving efficient control and real-time interaction across mobile devices, and significantly improving operational convenience and management efficiency in mobile scenarios. |
| <img src="./docs/images/logo_huiyuan.png" width="160"> | [Huiyuan Design](http://ui.kwd988.net/) | Thanks to [Huiyuan Design](http://ui.kwd988.net/) for providing professional visual solutions for this project, using their practical design experience from serving over a thousand companies to empower the user experience of this project's product. |
| <img src="./docs/images/logo_qinren.png" width="160"> | [Xi'an Qinren Information Technology](https://www.029app.com/) | Thanks to [Xi'an Qinren Information Technology](https://www.029app.com/) for deepening the visual system of this project, ensuring the consistency and scalability of the overall design style in multi-scenario applications. |
| <img src="./docs/images/logo_contributors.png" width="160"> | [Code Contributors](https://github.com/xinnan-tech/xiaozhi-esp32-server/graphs/contributors) | Thanks to [all code contributors](https://github.com/xinnan-tech/xiaozhi-esp32-server/graphs/contributors). Your efforts make the project more robust and powerful. |


<a href="https://star-history.com/#xinnan-tech/xiaozhi-esp32-server&Date">

 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date" />
 </picture>
</a>