# VocalCode — 專案架構與開發計畫

> 聲控 Python IDE：整合 ASR、LLM、TTS 的無障礙程式設計環境  
> 成員：314831019 蕭嘉甫 / 314831023 Rendra Eko Prasetiyo

---

## 目錄

1. [專案結構](#1-專案結構)
2. [系統架構](#2-系統架構)
3. [各元件設計](#3-各元件設計)
4. [API 流程](#4-api-流程)
5. [開發任務清單](#5-開發任務清單)
6. [技術規格](#6-技術規格)
7. [評估指標](#7-評估指標)

---

## 1. 專案結構

```
vocalcode/
├── frontend/
│   ├── index.html          # 主頁面
│   ├── style.css           # 樣式（高對比、WCAG 無障礙）
│   ├── package.json        # devDependency: typescript
│   ├── tsconfig.json       # strict, noImplicitAny, outDir: ./js
│   ├── ts/                 # TypeScript 原始碼（source of truth）
│   │   ├── globals.d.ts    # hljs CDN 全域型別宣告
│   │   ├── main.ts         # 應用程式進入點
│   │   ├── recorder.ts     # 麥克風錄音 / Web Audio API
│   │   ├── editor.ts       # 程式碼編輯器控制
│   │   ├── tts.ts          # 文字轉語音（Web Speech API）
│   │   └── api.ts          # 型別化 fetch 封裝 + response interface
│   └── js/                 # tsc 編譯輸出（gitignore，Docker 自動生成）
│
├── backend/
│   ├── app.py              # FastAPI 主程式 / 路由
│   ├── asr.py              # 語音辨識模組（sherpa-onnx ASR 微服務代理）
│   ├── llm.py              # LLM 程式碼生成 / 除錯（Ollama 本地模型）
│   ├── executor.py         # 安全沙盒程式碼執行
│   └── schemas.py          # Pydantic 資料模型
│
├── sandbox/
│   └── Dockerfile          # 隔離的程式碼執行環境
│
├── tests/
│   ├── Dockerfile          # 測試執行環境（python:3.12-slim）
│   ├── test_api.py         # FastAPI 端點整合測試
│   ├── test_asr.py         # ASR proxy 單元測試
│   ├── test_llm.py         # LLM 生成 / 除錯單元測試
│   └── test_executor.py    # 沙盒執行單元測試
│
├── .env.example            # API 金鑰範本
├── requirements.txt
└── README.md
```

---

## 2. 系統架構

```
使用者語音
    │
    ▼
┌─────────────────────┐
│  Frontend (Browser) │  錄音 → 傳送 WAV/WebM
│  - 程式碼編輯器      │◄─── 顯示生成的程式碼
│  - Terminal 輸出     │◄─── 顯示執行結果
│  - TTS 播放          │◄─── 讀出結果/錯誤摘要
└─────────┬───────────┘
          │ HTTP (multipart audio / JSON)
          ▼
┌─────────────────────┐
│  Backend (FastAPI)  │
│                     │
│  POST /transcribe   │──► ASR 微服務 (port 8001) ──► 轉錄文字
│  POST /generate     │──► Ollama API  (本地)     ──► Python 程式碼
│  POST /execute      │──► Sandbox                ──► stdout / stderr
│  POST /debug        │──► Ollama API  (本地)     ──► 修正後程式碼
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  Docker Sandbox     │  受限 Python 執行環境
│  - 無網路存取        │  timeout: 10s
│  - 記憶體上限 256MB  │  無系統呼叫
└─────────────────────┘
```

---

## 3. 各元件設計

### 3.1 Frontend — 使用者介面

**功能需求**
- 錄音按鈕（按住說話 / 點擊切換）
- 程式碼編輯器（唯讀顯示 LLM 輸出，支援語法高亮）
- Terminal 輸出視窗（顯示 stdout / stderr）
- 狀態列（顯示：錄音中 / 處理中 / 執行中 / 完成）
- TTS 播放控制（靜音、重播）

**無障礙設計（WCAG 2.1 AA）**
- 高對比配色（背景 `#1e1e1e`，文字 `#d4d4d4`）
- 所有互動元素可鍵盤操作
- `aria-live` 區域同步狀態給螢幕閱讀器
- 焦點順序邏輯清晰

**語言**：TypeScript（strict mode，`noImplicitAny`），由 `tsc` 編譯至 `js/`，Docker build 時自動執行。

**錄音流程（`recorder.ts`）**
```
getUserMedia() → MediaRecorder → ondataavailable
→ Blob (audio/webm) → FormData → POST /transcribe
```

### 3.2 ASR — 語音辨識（`asr.py`）

**使用技術**：sherpa-onnx ASR 微服務（port 8001），由 `asr/` 目錄下的 Docker Compose 獨立啟動

**代理架構**
- `asr.py` 作為代理模組，將音訊轉發給 ASR 微服務，不直接呼叫外部 API
- ASR 微服務於本地以 GPU 加速執行雙語（中英）streaming zipformer 模型
- 若 ASR 微服務不可用，回傳 HTTP 503

**API 端點**
```
POST /transcribe
Content-Type: multipart/form-data
Body: { audio: <file> }
Response: { text: "寫一個 for loop 印出 1 到 10" }
```

### 3.3 LLM — 程式碼生成與除錯（`llm.py`）

**使用技術**：Ollama 本地推論伺服器（`ollama run`）

**架構說明**
- Ollama 在本機以 REST API 形式提供服務（預設 `http://localhost:11434`）
- 後端透過 `ollama` Python SDK 或直接呼叫 HTTP API 與本地模型互動
- 模型由環境變數 `OLLAMA_MODEL` 設定（例如 `qwen2.5-coder:7b`、`codellama:7b`）
- 無需外部 API 金鑰，所有推論於本地完成

**啟動方式（需先安裝 Ollama）**
```bash
# 下載並啟動模型
ollama run qwen2.5-coder:7b
# Ollama 伺服器自動在 http://localhost:11434 提供 API
```

**系統提示詞（Code Generation）**
```
You are an expert Python developer. The user will describe what they want in 
Mandarin, English, or a mix of both. Generate ONLY syntactically correct, 
runnable Python code. Do not include explanations outside the code block.
Output format: pure Python code only.
```

**呼叫範例（Python）**
```python
import ollama

response = ollama.chat(
    model=OLLAMA_MODEL,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": transcript},
    ],
)
code = response["message"]["content"]
```

**自動除錯流程**
```python
# executor.py 執行後若有 stderr：
error_payload = {
    "original_code": code,
    "error_traceback": stderr,
    "user_intent": original_transcript
}
# 傳入 LLM debug prompt → 取得修正後程式碼 → 再次執行
# 最多重試 3 次
```

**API 端點**
```
POST /generate
Body: { transcript: "..." }
Response: { code: "for i in range(1, 11):\n    print(i)" }

POST /debug
Body: { code: "...", error: "...", transcript: "..." }
Response: { code: "...", explanation: "Fixed index error on line 3" }
```

### 3.4 沙盒執行環境（`executor.py` + Docker）

**安全限制**
| 限制項目 | 設定值 |
|---------|--------|
| 執行超時 | 10 秒 |
| 記憶體上限 | 256 MB |
| 網路存取 | 禁止 |
| 檔案系統寫入 | 僅限 `/tmp` |
| 禁用模組 | `os.system`, `subprocess`, `socket` |

**執行方式**
```python
# 使用 subprocess + resource limits（或 Docker exec）
result = subprocess.run(
    ["python3", "-c", code],
    capture_output=True, text=True,
    timeout=10,
    # 加入 seccomp / ulimit
)
```

**API 端點**
```
POST /execute
Body: { code: "..." }
Response: { stdout: "1\n2\n...", stderr: "", exit_code: 0 }
```

### 3.5 TTS — 文字轉語音（`tts.js`）

**使用技術**：Web Speech API（`SpeechSynthesis`）

**播報邏輯**
- 執行成功 → 讀出 stdout（截斷超過 200 字）
- 執行失敗並自動修正成功 → "Code had an error, but I fixed it. Here's the corrected result."
- 修正失敗 → "I couldn't fix the error. Please check the terminal for details."
- 程式碼生成完成 → "Code generated. Running now."

---

## 4. API 流程

### 完整使用者流程

```
[1] 使用者按下錄音鍵，說：「寫一個 function 計算費氏數列」
    └─► recorder.js 收集音訊 Blob

[2] POST /transcribe (音訊檔)
    └─► asr.py 代理 → ASR 微服務 (port 8001) 回傳：「寫一個 function 計算費氏數列」

[3] POST /generate (transcript)
    └─► llm.py → Ollama 本地模型回傳 Python code
    └─► editor.js 顯示程式碼

[4] POST /execute (code)
    ├─► 成功 → stdout 顯示於 Terminal，TTS 播報結果
    └─► 失敗 → 自動進入除錯流程

[5] POST /debug (code + error)  ← 失敗時才觸發
    └─► llm.py → Ollama 本地模型回傳修正程式碼
    └─► 重回步驟 [4]，最多 3 次
```

---

## 5. 開發任務清單

### Phase 1：基礎建設（第 1-2 週）

- [ ] 初始化專案結構與 Git repo
- [ ] 建立 Python 虛擬環境，安裝 FastAPI / uvicorn / openai / google-generativeai
- [ ] 設定 `.env` 環境變數管理（API keys）
- [ ] 建立 FastAPI 骨架（`app.py`）+ 健康檢查端點
- [ ] 前端 HTML/CSS 基礎排版（編輯器區、Terminal 區、按鈕區）

### Phase 2：ASR 模組（第 2-3 週）

- [ ] 實作 `recorder.js`：`getUserMedia` + `MediaRecorder`
- [ ] 實作 `POST /transcribe`：接收音訊 → 代理至 ASR 微服務 (port 8001)
- [ ] 實作 `backend/asr.py` 代理模組（httpx 轉發 multipart 音訊）
- [ ] 確認 ASR 微服務（`asr/compose.yaml`）可正常啟動並辨識雙語
- [ ] 前端顯示轉錄結果（即時預覽）
- [ ] 測試案例：中文、英文、混合語言各 10 句

### Phase 3：LLM 程式碼生成（第 3-4 週）

- [ ] 安裝並啟動 Ollama，拉取目標模型（`ollama pull qwen2.5-coder:7b`）
- [ ] 實作 `llm.py`：使用 `ollama` Python SDK 與本地模型互動
- [ ] 設計並測試 system prompt（生成品質基準）
- [ ] 實作 `POST /generate` 端點
- [ ] 確保 LLM 輸出為純 Python（解析 markdown code block，去除 ` ```python ` 包裝）
- [ ] 前端接收程式碼並顯示於編輯器（語法高亮）

### Phase 4：沙盒執行（第 4-5 週）

- [ ] 實作 `executor.py`：subprocess 執行 + timeout
- [ ] 建立 Docker 沙盒環境（`sandbox/Dockerfile`）
- [ ] 實作 `POST /execute` 端點
- [ ] 安全測試：確認危險程式碼（`os.system`, `rm -rf` 等）無法執行
- [ ] 前端顯示 stdout / stderr 於 Terminal

### Phase 5：自動除錯迴圈（第 5-6 週）

- [ ] 實作 `POST /debug` 端點：錯誤 + 原始碼 → Ollama 本地模型 → 修正碼
- [ ] 實作重試機制（最多 3 次，超過則回報失敗）
- [ ] 在前端標示「自動修正中」狀態
- [ ] 測試案例：語法錯誤、執行期錯誤、邏輯錯誤各 5 組

### Phase 6：TTS 整合（第 6 週）

- [ ] 實作 `tts.js`：`SpeechSynthesis` 封裝
- [ ] 設計各場景播報文稿
- [ ] 靜音 / 重播控制按鈕
- [ ] 測試：確認所有狀態都有對應的語音回饋

### Phase 7：整合測試與優化（第 7-8 週）

- [ ] 端對端流程測試（錄音 → 轉錄 → 生成 → 執行 → 播報）
- [ ] 無障礙測試（鍵盤操作、螢幕閱讀器）
- [ ] 效能測試：量測各階段延遲
- [ ] 錯誤處理：網路錯誤、API 配額超限、麥克風拒絕授權
- [ ] UI 細節優化（loading 動畫、過渡效果）

### Phase 8：評估與展示（第 8 週）

- [ ] 設計評估測試集（30 題：簡單 / 中階 / 錯誤場景各 10 題）
- [ ] 量測 WER（Word Error Rate）
- [ ] 量測程式碼正確率
- [ ] 量測除錯成功率
- [ ] 量測任務完成時間
- [ ] 準備 Demo 影片與簡報

---

## 6. 技術規格

### 後端依賴（`requirements.txt`）

```
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.9
httpx>=0.27.0           # 代理請求至 ASR 微服務
ollama>=0.2.0           # Ollama Python SDK（本地 LLM）
python-dotenv>=1.0.0
pydantic>=2.7.0
```

### 環境變數（`.env.example`）

```
# Ollama — 本地 LLM 推論伺服器
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b

# ASR 微服務（由 asr/compose.yaml 啟動）
ASR_SERVICE_URL=http://localhost:8001

# 沙盒設定
MAX_DEBUG_RETRIES=3
SANDBOX_TIMEOUT=10
```

### 跨來源資源共享（CORS）

後端需允許前端開發伺服器的來源：
```python
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

---

## 7. 評估指標

| 指標 | 計算方式 | 目標 |
|------|---------|------|
| WER（語音辨識錯誤率） | `(S+D+I) / N × 100%` | < 15% |
| 程式碼正確率 | 通過測試案例數 / 總題數 | > 70% |
| 除錯成功率 | 自動修正成功次數 / 觸發除錯次數 | > 60% |
| 任務完成時間 | 從說話結束到結果播報完成 | < 15 秒 |

### 測試情境

**簡單任務**（預期正確率高）
- 印出 1 到 N 的數字
- 定義加法 function
- 字串反轉

**中階任務**
- 讀取 CSV 並計算平均值
- 呼叫外部 API（受沙盒限制，測試錯誤處理）
- 遞迴函式

**錯誤場景**（測試自動除錯）
- 故意製造 IndexError
- 故意製造 NameError
- 無限迴圈（測試 timeout）

---

## 延伸功能（若時間允許）

- [ ] 語音控制 IDE 操作（「刪除第 4 行」、「復原」、「執行程式」）
- [ ] VS Code Extension 版本
- [ ] 對話歷史：記住上一段程式碼以支援「修改剛才的程式」
- [ ] 多語言 TTS 輸出（中文播報）
