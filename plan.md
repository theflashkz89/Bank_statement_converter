# 银行对账单PDF转Excel转换器 - 开发计划

> **文档状态**: ✅ 需求已确认，待审核后开发  
> **更新日期**: 2025-12-31  
> **当前版本**: V1.0（原生PDF解析）  
> **未来版本**: V2.0（OCR扫描件支持）  
> **Git仓库**: https://github.com/theflashkz89/Bank_statement_converter

---

## ⚠️ 必须遵守的三条规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | **每步必测** | 每完成一个小步骤，必须进行功能测试，确认无误后再继续 |
| 2 | **测试通过后必须提交** | 用户确认测试通过后，必须执行 `git commit` 更新版本控制 |
| 3 | **最小改动原则** | 只修改计划中明确要求的部分，不触碰其他功能代码 |

---

## 📑 目录

| 章节 | 内容 | 说明 |
|-----|------|------|
| [一、项目概述](#一项目概述) | 项目目标、输出表头 | 快速了解项目 |
| [二、银行对账单格式分析](#二银行对账单格式分析) | Airwallex、HSBC格式详解 | PDF结构参考 |
| [三、技术方案](#三技术方案) | 技术栈、DeepSeek API | 技术选型 |
| [四、数据处理流程](#四数据处理流程) | 架构图、字段映射、**技术陷阱** | 核心逻辑 |
| [五、输出规格](#五输出规格) | Excel结构、格式化规则 | 输出标准 |
| [六、项目文件结构](#六项目文件结构) | 目录树 | 代码组织 |
| [七、版本规划](#七版本规划) | V1.0/V2.0、OCR预留 | 版本路线 |
| [八、实施阶段表](#八实施阶段表最小可实施任务分割) | **46项最小任务** | ⭐ 开发执行 |
| [九、需求确认汇总](#九需求确认汇总-) | 已确认需求列表 | 需求追溯 |
| [十、依赖清单](#十依赖清单) | requirements.txt | 环境配置 |
| [十一、GUI界面设计](#十一gui界面设计streamlit) | Streamlit界面、代码示例 | UI参考 |
| [十二、优化说明](#十二优化说明已采纳) | 4项已采纳优化 | 设计决策 |

---

## 一、项目概述

### 1.1 项目目标
将PDF格式的银行对账单（Airwallex、HSBC）转换为标准化Excel格式，支持多币种、智能解析、批量处理。

### 1.2 最终输出表头（9列）

| 列名 | 说明 | 数据类型 | 示例 |
|------|------|---------|------|
| **Date** | 交易日期 | 日期 | 2024-06-23 |
| **Account Currency** | 账户币种 | 文本 | HKD / USD / CNY |
| **Payer** | 付款方 | 文本 | MDH INTERNATIONAL HONG KONG |
| **Payee** | 收款方 | 文本 | MONX TEAM LTD |
| **Debit** | 借方金额（支出） | **数值** | 23500.00 |
| **Credit** | 贷方金额（收入） | **数值** | 30132.99 |
| **Balance** | 余额 | **数值** | 6632.99 |
| **Reference** | 交易参考号 | 文本 | INV 0016,0017,0019,0020 |
| **Description** | 交易描述 | 文本 | Payout - Pay HKD 23500.00 to MONX TEAM LTD |

> ⚠️ **Excel友好设计**：Debit/Credit/Balance列为**纯数值**（不含货币符号），配合Account Currency列使用，支持Excel公式计算（SUM等）。

---

## 二、银行对账单格式分析

### 2.1 Airwallex 对账单

**文件特征：**
- 命名规则：`{序号}-{公司名}-ASR_{币种}_{开始日期}_{结束日期}.pdf`
- 支持币种：AUD, CNY, EUR, HKD, PHP, USD
- 类型：年度对账单

**PDF表格结构：**
```
┌────────────┬─────────────────────────────────────┬────────────────┬───────────────┬────────────────┐
│    Date    │              Details                │     Credit     │     Debit     │    Balance     │
├────────────┼─────────────────────────────────────┼────────────────┼───────────────┼────────────────┤
│Jun 23 2024 │ Conversion                          │ 30,132.99 HKD  │               │ 30,132.99 HKD  │
│            │ Sell USD 3880.00                    │                │               │                │
├────────────┼─────────────────────────────────────┼────────────────┼───────────────┼────────────────┤
│Jun 23 2024 │ Payout                              │                │ 23,500.00 HKD │ 6,632.99 HKD   │
│            │ Pay HKD 23500.00 to MONX TEAM LTD   │                │               │                │
├────────────┼─────────────────────────────────────┼────────────────┼───────────────┼────────────────┤
│Jul 30 2024 │ Global Account Collection           │ 21,635.00 HKD  │               │ 28,267.99 HKD  │
│            │ MDH INTERNATIONAL HONG KONG |       │                │               │                │
│            │ Ref: INV 0016,0017,0019,0020 |      │                │               │                │
│            │ GA INTERGROUP SHIPPING HK LIMITED | │                │               │                │
│            │ 798275351 |                         │                │               │                │
│            │ 47b3c949-2154-45bc-adc5-1a8136221642│                │               │                │
├────────────┼─────────────────────────────────────┼────────────────┼───────────────┼────────────────┤
│Jul 30 2024 │ Fee                                 │                │ 64.90 HKD     │ 28,203.09 HKD  │
│            │ Reason: Deposit to account 798275351│                │               │                │
└────────────┴─────────────────────────────────────┴────────────────┴───────────────┴────────────────┘
```

**Details字段解析规则：**

| 交易类型 | Details格式 | 提取规则 |
|---------|------------|---------|
| Conversion | `Conversion`<br>`Sell USD 3880.00` | Payer: 本账户<br>Payee: Unknown<br>Ref: 无 |
| Payout | `Payout`<br>`Pay HKD 23500.00 to {Payee}` | Payer: 本账户<br>Payee: 提取`to`后的公司名<br>Ref: 无 |
| Global Account Collection | `Global Account Collection`<br>`{Payer} \| Ref: {Ref} \| ...` | Payer: 第一个`\|`前的公司名<br>Payee: 本账户<br>Ref: 提取`Ref:`后的内容 |
| Fee | `Fee`<br>`Reason: {Description}` | Payer: 本账户<br>Payee: Airwallex<br>Ref: 无 |

**汇总信息位置：**
```
HKD Account Summary
├── Starting balance on Jan 01 2024: 0.00 HKD
├── Total collections and other additions: 633,081.56 HKD
├── Total payouts and other subtractions: 632,711.70 HKD
├── Minimum balance: 0.00 HKD
├── Maximum balance: 161,095.77 HKD
└── Ending balance on Dec 31 2025: 369.86 HKD
```

---

### 2.2 HSBC 对账单

**文件特征：**
- 命名规则：`HSBC {年} {月}.pdf` 或 `HSBC Bank {YYYYMMDD}.pdf`
- 类型：月度对账单
- 特点：**一份PDF可能包含多个币种账户**

**PDF表格结构：**
```
HSBC Sprint Account HKD Savings 汇丰Sprint户口 - 港元储蓄
┌─────────┬──────────────────────────────┬──────────┬────────────┬─────────────┐
│  Date   │    Transaction Details       │ Deposit  │ Withdrawal │   Balance   │
│  日期   │         进支详情              │   存入   │    提取     │    结余     │
├─────────┼──────────────────────────────┼──────────┼────────────┼─────────────┤
│ 8 May   │ B/F BALANCE                  │          │            │ 187,191.60  │
│         │ 承前转结                      │          │            │             │
├─────────┼──────────────────────────────┼──────────┼────────────┼─────────────┤
│ 9 May   │ POS MDC  (09MAY24)           │          │    127.48  │             │
│         │ UBER *TRIP HELP.UBER         │          │            │             │
│         │ 转账支出                      │          │            │             │
├─────────┼──────────────────────────────┼──────────┼────────────┼─────────────┤
│ 9 May   │ POS MDC  (09MAY24)           │          │     66.97  │             │
│         │ UBER *TRIP                   │          │            │             │
│         │ 转账支出                      │          │            │             │
├─────────┼──────────────────────────────┼──────────┼────────────┼─────────────┤
│ 10 May  │ POS MDC  (10MAY24)           │          │    130.25  │ 186,650.87  │
│         │ UBER *TRIP                   │          │            │             │
│         │ 转账支出                      │          │            │             │
└─────────┴──────────────────────────────┴──────────┴────────────┴─────────────┘

（可能还有其他币种账户...）
HSBC Sprint Account USD Savings 汇丰Sprint户口 - 美元储蓄
┌─────────┬──────────────────────────────┬──────────┬────────────┬─────────────┐
│ ...     │ ...                          │ ...      │ ...        │ ...         │
```

**Transaction Details解析规则：**

| 行号 | 内容 | 提取字段 |
|-----|------|---------|
| 第1行 | `POS MDC (日期)` 或 `B/F BALANCE` | 交易类型标识 |
| 第2行 | 商户名称（如`UBER *TRIP HELP.UBER`） | **Payee** |
| 第3行 | 中文交易类型（如`转账支出`） | 追加到**Description** |

**年份获取逻辑（含跨年处理）：**

> ⚠️ **跨年陷阱**：月度账单可能跨年（如2023年12月～2024年1月），需智能判断年份。

```python
def determine_year(transaction_date: str, statement_date: datetime) -> int:
    """
    智能判断交易年份
    
    参数:
        transaction_date: 交易日期文本，如 "18 Dec"
        statement_date: 账单生成日期，如 datetime(2024, 1, 8)
    
    返回:
        正确的年份
    
    逻辑:
        - 如果交易月份 > 账单月份，说明是上一年的交易
        - 例如：账单日期1月，交易日期12月 → 年份-1
    """
    # 解析交易月份
    tx_month = parse_month(transaction_date)  # "18 Dec" → 12
    stmt_month = statement_date.month          # 1
    stmt_year = statement_date.year            # 2024
    
    # 跨年判断：交易月份大于账单月份，说明是去年
    if tx_month > stmt_month + 6:  # 加6是为了处理边界情况
        return stmt_year - 1
    else:
        return stmt_year

# 示例：
# 账单日期: 2024年1月8日
# 交易 "18 Dec" → 2023-12-18 ✓ (而不是错误的2024-12-18)
# 交易 "5 Jan"  → 2024-01-05 ✓
```

**年份来源优先级**：
1. 优先从页眉日期提取（如"8 June 2024"）
2. 备选从文件名提取（如"HSBC 2024 05.pdf"）
3. 从`POS MDC (09MAY24)`中的日期码提取（如`MAY24`→2024年5月）

**多币种识别：**
- 通过账户标题识别：`HSBC Sprint Account {Currency} Savings`
- Currency可能值：HKD, USD, CNY, EUR等

---

## 三、技术方案

### 3.1 技术栈

```
Python 3.11.9
├── pdfplumber          # PDF表格提取（主力库）
├── pandas              # 数据处理
├── openpyxl            # Excel读写
├── python-dateutil     # 智能日期解析
├── openai              # DeepSeek API调用
├── streamlit           # Web UI界面（现代化、支持数据预览）
├── logging             # 日志记录
└── PyInstaller         # 打包exe（含启动脚本）
```

> ✅ **UI框架选择：Streamlit**
> - 支持在界面上**预览解析后的Excel数据**，便于财务核对后再下载
> - 现代化界面，用户体验好
> - 通过启动脚本封装，用户感觉像打开普通软件

### 3.2 DeepSeek API 集成

**用途**：智能解析Details字段，提取Payer/Payee/Reference

**配置方式**：
```python
# config.py

# === DeepSeek API配置 ===
DEEPSEEK_API_KEY = ""  # ← 用户在此填写API Key
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# === OCR配置（V2功能，暂不启用）===
OCR_PROVIDER = ""  # 可选: "textin", "baidu", ""(不使用)
TEXTIN_API_KEY = ""
BAIDU_API_KEY = ""
BAIDU_SECRET_KEY = ""
```

**调用逻辑（批量处理优化）**：

> ⚠️ **性能优化**：采用批量处理模式，每次发送15-20条记录，避免逐条调用导致的性能问题和API限流。

```python
BATCH_SIZE = 15  # 每批处理15条记录

def parse_details_batch_with_ai(details_list: list[str]) -> list[dict]:
    """
    批量使用DeepSeek API解析交易详情
    输入: 15-20条Details文本的列表
    返回: 对应的解析结果列表 [{"payer": str, "payee": str, "reference": str}, ...]
    """
    if not DEEPSEEK_API_KEY:
        # API Key未配置，使用正则解析
        return [parse_details_with_regex(d) for d in details_list]
    
    # 构建批量请求
    numbered_details = "\n".join([f"{i+1}. {d}" for i, d in enumerate(details_list)])
    
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {
                "role": "system", 
                "content": """从银行交易详情中提取信息。输入是编号列表，请返回对应的JSON数组。
每条记录提取：
- payer: 付款方（本账户付出时填"Self"）
- payee: 收款方（本账户收入时填"Self"）  
- reference: 交易参考号（不含UUID格式的ID）
无法识别时填"Unknown"。

返回格式示例：
[{"payer":"Self","payee":"MONX TEAM LTD","reference":""},{"payer":"MDH INTERNATIONAL","payee":"Self","reference":"INV 0016"}]"""
            },
            {"role": "user", "content": numbered_details}
        ],
        temperature=0.1
    )
    return json.loads(response.choices[0].message.content)

def process_all_details(all_details: list[str]) -> list[dict]:
    """分批处理所有Details"""
    results = []
    for i in range(0, len(all_details), BATCH_SIZE):
        batch = all_details[i:i+BATCH_SIZE]
        try:
            batch_results = parse_details_batch_with_ai(batch)
            results.extend(batch_results)
        except Exception as e:
            # 单批失败时降级为正则解析
            logging.warning(f"API调用失败，降级为正则解析: {e}")
            results.extend([parse_details_with_regex(d) for d in batch])
    return results
```

**性能对比**：
| 方式 | 500条记录耗时 | API调用次数 |
|-----|-------------|------------|
| 逐条调用 | ~250秒（4分钟） | 500次 |
| 批量处理(15条/批) | ~17秒 | 34次 |

**降级策略**：
1. API Key未配置 → 使用正则解析
2. 单批调用失败 → 该批降级为正则，不影响其他批次
3. 网络超时 → 重试1次后降级

---

## 四、数据处理流程

### 4.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GUI 界面 (tkinter)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ 选择PDF文件  │  │ 选择输出目录 │  │  开始转换   │  │     处理进度/日志    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              主控制器 (main.py)                              │
│  1. 扫描输入文件                                                             │
│  2. 识别银行类型 (Airwallex / HSBC)                                          │
│  3. 分发到对应解析器                                                         │
│  4. 收集结果并输出                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
           │                                              │
           ▼                                              ▼
┌─────────────────────────┐                ┌─────────────────────────┐
│   AirwallexParser       │                │      HSBCParser         │
├─────────────────────────┤                ├─────────────────────────┤
│ - 提取表格数据          │                │ - 提取表格数据          │
│ - 解析Details字段       │                │ - 识别多币种账户        │
│ - 调用DeepSeek API      │                │ - 补充年份信息          │
│ - 提取汇总信息          │                │ - 解析Transaction Details│
│ - 过滤UUID              │                │ - 保留中文标签          │
└─────────────────────────┘                └─────────────────────────┘
           │                                              │
           └──────────────────────┬───────────────────────┘
                                  ▼
                    ┌─────────────────────────┐
                    │     Normalizer          │
                    ├─────────────────────────┤
                    │ - 日期格式: YYYY-MM-DD  │
                    │ - 金额格式: 千位分隔符  │
                    │ - 货币符号: 保留        │
                    │ - 缺失值: "Unknown"     │
                    │ - 统一9列表头           │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │     ExcelExporter       │
                    ├─────────────────────────┤
                    │ - Sheet1: Transactions  │
                    │ - Sheet2: Summary       │
                    │ - 格式化单元格          │
                    │ - 自动列宽              │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   {原文件名}_converted.xlsx │
                    └─────────────────────────┘
```

### 4.2 字段映射表

| 标准输出 | Airwallex源 | HSBC源 | 处理逻辑 |
|---------|------------|--------|---------|
| Date | Date列 | Date列 | Airwallex: 直接解析"Jun 23 2024"<br>HSBC: 智能补充年份（含跨年处理） |
| Account Currency | 从文件名或表头提取 | 从账户标题提取 | 识别`{Currency} Savings`或`ASR_{Currency}` |
| Payer | Details解析 | "Unknown" | DeepSeek批量解析/正则提取 |
| Payee | Details解析 | Transaction Details第2行 | DeepSeek批量解析/正则提取 |
| Debit | Debit列 | Withdrawal列 | **去除货币符号，转为纯数值** |
| Credit | Credit列 | Deposit列 | **去除货币符号，转为纯数值** |
| Balance | Balance列 | Balance列 | **去除货币符号，转为纯数值** |
| Reference | Details中Ref:后内容 | 空 | 提取业务参考号，过滤UUID |
| Description | Details完整内容 | Transaction Details完整内容 | 保留中文标签，多行合并 |

### 4.3 特殊情况处理

| 情况 | 处理方式 |
|-----|---------|
| Payer/Payee无法识别 | 填写"Unknown" |
| UUID格式（如47b3c949-...） | 过滤不保留 |
| B/F BALANCE（期初余额） | 保留，Description标记为"期初余额" |
| 表格跨页 | 自动合并，跳过重复表头 |
| 空行 | 跳过 |
| 多币种账户(HSBC) | Account Currency列区分 |

### 4.4 ⚠️ 技术陷阱与解决方案

#### 陷阱1: Windows文件占用锁（Excel Exporter）

**场景**：用户打开了 `ABC_converted.xlsx` 正在核对，此时重新点击"开始解析"。

**后果**：`PermissionError: [Errno 13] Permission denied`，程序崩溃。

**解决方案**：
```python
# exporter.py
def save_excel(df, filepath):
    try:
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Transactions', index=False)
    except PermissionError:
        # 友好提示，不崩溃
        raise FileLockedError(
            f"⚠️ 文件被占用，请先关闭已打开的 Excel 文件：\n{filepath}"
        )

# 自定义异常
class FileLockedError(Exception):
    pass
```

---

#### 陷阱2: Streamlit重跑机制（App.py）

**特性**：Streamlit的机制是"只要用户与界面交互，整个脚本就会从头运行一遍"。

**风险**：用户点击"下载Excel"时，如果没有缓存，程序会重新解析PDF（浪费时间和API Token）。

**解决方案**：
```python
# app.py - 使用缓存装饰器
@st.cache_data
def parse_pdf(file_bytes, filename):
    """
    解析PDF文件（带缓存）
    注意：参数必须是可哈希的（bytes而非file对象）
    """
    # ... 解析逻辑 ...
    return df, summary

# 调用时传入bytes
file_bytes = uploaded_file.read()
df, summary = parse_pdf(file_bytes, uploaded_file.name)
```

**效果**：点击下载按钮时，直接从内存取数据，瞬间完成。

---

#### 陷阱3: HSBC多币种状态机重置

**场景**：HSBC的PDF是连续的，前3页是HKD，第4页开头变成USD。

**风险**：如果不重置`current_currency`，第4页的交易会被错误归类为HKD。

**解决方案**：
```python
# hsbc_parser.py
class HSBCParser(BaseParser):
    def parse(self, pdf_path):
        current_currency = None
        transactions = []
        
        for page in pdf.pages:
            text = page.extract_text()
            
            # 检测账户切换标志（必须在处理交易前）
            # 匹配: "HKD Savings", "USD Current", "CNY Savings" 等
            currency_match = re.search(
                r'(HKD|USD|CNY|EUR|GBP|AUD)\s+(Savings|Current)', 
                text
            )
            if currency_match:
                # ⚠️ 立即重置状态机
                current_currency = currency_match.group(1)
                logging.info(f"检测到账户切换: {current_currency}")
            
            # 然后再处理该页的交易
            page_transactions = self._extract_transactions(page)
            for tx in page_transactions:
                tx['currency'] = current_currency
            transactions.extend(page_transactions)
```

**关键**：一旦检测到包含 `Savings` 或 `Current` 的标题行，**立即**重置 `current_currency`。

---

## 五、输出规格

### 5.1 Excel文件结构

**文件命名**：`{原PDF文件名}_converted.xlsx`

**Sheet1: Transactions（交易记录）**

| Date | Account Currency | Payer | Payee | Debit | Credit | Balance | Reference | Description |
|------|------------------|-------|-------|-------|--------|---------|-----------|-------------|
| 2024-06-23 | HKD | Self | MONX TEAM LTD | 23500.00 | | 6632.99 | | Payout - Pay HKD 23500.00 to MONX TEAM LTD |
| 2024-07-30 | HKD | MDH INTERNATIONAL | Self | | 21635.00 | 28267.99 | INV 0016,0017 | Global Account Collection - MDH INTERNATIONAL... |

> ✅ **Excel友好**：Debit/Credit/Balance为纯数值，可直接使用`=SUM()`等公式。货币信息请参考Account Currency列。

**Sheet2: Summary（汇总信息）**

| 项目 | 值 |
|-----|---|
| 原始文件 | xxx.pdf |
| 银行 | Airwallex / HSBC |
| 账户币种 | HKD, USD, ... |
| 统计期间 | 2024-01-01 ~ 2024-12-31 |
| 期初余额 | 0.00 HKD |
| 期末余额 | 369.86 HKD |
| 总收入(Credit) | 633,081.56 HKD |
| 总支出(Debit) | 632,711.70 HKD |
| 交易笔数 | 156 |

### 5.2 格式化规则

| 字段 | 格式 | Excel单元格格式 | 示例 |
|-----|------|----------------|------|
| Date | YYYY-MM-DD | 日期格式 | 2024-06-23 |
| Account Currency | 文本 | 常规 | HKD |
| Debit/Credit/Balance | **纯数值**（2位小数） | 数值格式`#,##0.00` | 23500.00 |
| Payer/Payee | 文本 | 常规 | MONX TEAM LTD |
| Reference | 文本 | 常规 | INV 0016,0017 |
| Description | 文本（多行合并） | 常规 | Payout - Pay HKD 23500.00... |
| 空值 | 空单元格 | - | （不填0或N/A） |

> ⚠️ **重要变更**：金额列（Debit/Credit/Balance）不再包含货币符号，改为**纯数值**格式，便于Excel公式计算。货币类型请参考Account Currency列。

---

## 六、项目文件结构

```
Bank Statement Converter/
│
├── app.py                        # Streamlit主程序入口
├── config.py                     # 配置文件（含DeepSeek API Key）
│
├── src/                          # 源代码目录
│   ├── __init__.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base_parser.py        # 解析器基类
│   │   ├── airwallex_parser.py   # Airwallex解析器
│   │   ├── hsbc_parser.py        # HSBC解析器
│   │   └── ocr_parser.py         # OCR解析器（V2预留，暂不实现）
│   ├── normalizer.py             # 数据标准化模块
│   ├── exporter.py               # Excel导出模块
│   └── utils.py                  # 工具函数（日期解析、正则等）
│
├── logs/                         # 日志目录
│   └── converter.log
│
├── Airwallex/                    # 示例输入：Airwallex PDF
├── HSBC/                         # 示例输入：HSBC PDF
│
├── requirements.txt              # Python依赖
├── 启动转换器.bat                 # Windows一键启动脚本
├── 启动转换器.command             # Mac一键启动脚本
├── plan.md                       # 本文档
├── to_be_checked.md              # 需求确认文档
└── README.md                     # 使用说明
```

---

## 七、版本规划

### V1.0（当前版本）- 原生PDF解析
- 支持Airwallex、HSBC原生PDF对账单
- pdfplumber直接提取表格数据
- DeepSeek API智能解析Details字段

### V2.0（未来版本）- OCR扫描件支持 🔮

> ⚠️ **预留接口**：V1.0代码结构已为OCR功能预留扩展点

**计划支持的OCR服务**：
| 服务 | 说明 | 配置方式 |
|-----|------|---------|
| TextIn | 合合信息OCR，表格识别准确 | `TEXTIN_API_KEY` |
| 百度OCR | 百度云文字识别 | `BAIDU_API_KEY` + `BAIDU_SECRET_KEY` |

**预留代码结构**：
```python
# config.py - V2预留配置
# === OCR配置（V2功能，暂不启用）===
OCR_PROVIDER = ""  # 可选: "textin", "baidu", ""(不使用)
TEXTIN_API_KEY = ""
BAIDU_API_KEY = ""
BAIDU_SECRET_KEY = ""

# src/parsers/ocr_parser.py - V2预留解析器
class OCRParser(BaseParser):
    """OCR扫描件解析器 - V2实现"""
    def __init__(self):
        raise NotImplementedError("OCR功能将在V2版本实现")
```

---

## 八、实施阶段表（最小可实施任务分割）

### 📋 任务检查清单

> **规则提醒**：每个 ✅ 任务完成后必须：1）功能测试 2）用户确认 3）git commit

---

### Stage 1: 项目初始化
| # | 任务 | 预计时间 | 测试方法 | 状态 |
|---|------|---------|---------|------|
| 1.1 | 创建项目目录结构 | 5min | 目录存在检查 | ⬜ |
| 1.2 | 创建requirements.txt | 2min | `pip install -r requirements.txt` | ⬜ |
| 1.3 | 创建config.py（含API Key变量） | 5min | import无报错 | ⬜ |
| 1.4 | 初始化git仓库并关联远程 | 5min | `git remote -v` | ⬜ |
| 1.5 | **Stage 1 提交并推送** | - | `git push -u origin main` | ⬜ |

**Git仓库配置命令**：
```bash
git init
git remote add origin https://github.com/theflashkz89/Bank_statement_converter.git
git add .
git commit -m "Stage 1: 项目初始化"
git branch -M main
git push -u origin main
```

---

### Stage 2: 解析器基础框架
| # | 任务 | 预计时间 | 测试方法 | 状态 |
|---|------|---------|---------|------|
| 2.1 | 创建base_parser.py（抽象基类） | 10min | import无报错 | ⬜ |
| 2.2 | 创建utils.py（日期解析函数） | 15min | 单元测试：日期转换 | ⬜ |
| 2.3 | 创建utils.py（金额解析函数） | 10min | 单元测试：金额提取 | ⬜ |
| 2.4 | **Stage 2 提交** | - | `git commit & git push` | ⬜ |

---

### Stage 3: Airwallex解析器
| # | 任务 | 预计时间 | 测试方法 | 状态 |
|---|------|---------|---------|------|
| 3.1 | 实现PDF表格提取（pdfplumber） | 20min | 打印提取的原始数据 | ⬜ |
| 3.2 | 实现日期解析（"Jun 23 2024"格式） | 10min | 测试日期转换正确 | ⬜ |
| 3.3 | 实现Details正则解析（Payer/Payee/Ref） | 30min | 测试各类型Details | ⬜ |
| 3.4 | 实现DeepSeek批量解析（可选） | 20min | API调用测试 | ⬜ |
| 3.5 | 实现汇总信息提取 | 15min | 打印汇总数据 | ⬜ |
| 3.6 | 集成测试：完整解析1个Airwallex文件 | 15min | 输出DataFrame检查 | ⬜ |
| 3.7 | **Stage 3 提交** | - | `git commit & git push` | ⬜ |

---

### Stage 4: HSBC解析器
| # | 任务 | 预计时间 | 测试方法 | 状态 |
|---|------|---------|---------|------|
| 4.1 | 实现PDF表格提取（pdfplumber） | 20min | 打印提取的原始数据 | ⬜ |
| 4.2 | 实现多币种账户识别 | 20min | 测试识别HKD/USD账户 | ⬜ |
| 4.3 | 实现年份智能补充（含跨年处理） | 20min | 测试跨年日期 | ⬜ |
| 4.4 | 实现Transaction Details解析 | 20min | 测试Payee提取 | ⬜ |
| 4.5 | 集成测试：完整解析1个HSBC文件 | 15min | 输出DataFrame检查 | ⬜ |
| 4.6 | **Stage 4 提交** | - | `git commit & git push` | ⬜ |

---

### Stage 5: 数据标准化与导出
| # | 任务 | 预计时间 | 测试方法 | 状态 |
|---|------|---------|---------|------|
| 5.1 | 实现normalizer.py（字段映射） | 15min | 测试输出9列格式 | ⬜ |
| 5.2 | 实现exporter.py（Transactions Sheet） | 20min | 打开生成的Excel检查 | ⬜ |
| 5.3 | 实现exporter.py（Summary Sheet） | 15min | 检查汇总数据正确 | ⬜ |
| 5.4 | 集成测试：Airwallex → Excel | 10min | Excel完整性检查 | ⬜ |
| 5.5 | 集成测试：HSBC → Excel | 10min | Excel完整性检查 | ⬜ |
| 5.6 | **Stage 5 提交** | - | `git commit & git push` | ⬜ |

---

### Stage 6: Streamlit界面
| # | 任务 | 预计时间 | 测试方法 | 状态 |
|---|------|---------|---------|------|
| 6.1 | 创建app.py基础框架 | 10min | `streamlit run app.py` 启动 | ⬜ |
| 6.2 | 实现文件上传组件 | 15min | 上传PDF成功 | ⬜ |
| 6.3 | 实现解析触发与进度显示 | 15min | 点击按钮触发解析 | ⬜ |
| 6.4 | 实现数据预览表格 | 15min | DataFrame正确显示 | ⬜ |
| 6.5 | 实现汇总统计卡片 | 10min | 统计数据正确 | ⬜ |
| 6.6 | 实现Excel下载按钮 | 10min | 下载文件完整 | ⬜ |
| 6.7 | 实现日志显示区域 | 10min | 日志实时更新 | ⬜ |
| 6.8 | 界面美化与布局调整 | 15min | 视觉检查 | ⬜ |
| 6.9 | **Stage 6 提交** | - | `git commit & git push` | ⬜ |

---

### Stage 7: 启动脚本与文档
| # | 任务 | 预计时间 | 测试方法 | 状态 |
|---|------|---------|---------|------|
| 7.1 | 创建启动转换器.bat（Windows） | 5min | 双击启动测试 | ⬜ |
| 7.2 | 创建启动转换器.command（Mac） | 5min | - | ⬜ |
| 7.3 | 编写README.md使用说明 | 20min | 文档完整性检查 | ⬜ |
| 7.4 | **Stage 7 提交** | - | `git commit & git push` | ⬜ |

---

### Stage 8: 全量测试
| # | 任务 | 预计时间 | 测试方法 | 状态 |
|---|------|---------|---------|------|
| 8.1 | 测试全部Airwallex文件（6个） | 20min | 逐个检查Excel | ⬜ |
| 8.2 | 测试全部HSBC文件（12个） | 30min | 逐个检查Excel | ⬜ |
| 8.3 | 边缘情况测试（空文件、损坏文件等） | 15min | 错误处理正确 | ⬜ |
| 8.4 | 修复发现的问题 | 视情况 | 回归测试 | ⬜ |
| 8.5 | **Stage 8 提交（V1.0 Release）** | - | `git tag v1.0 & git push --tags` | ⬜ |

---

### 📊 总体时间估算

| Stage | 任务数 | 预计时间 |
|-------|-------|---------|
| Stage 1: 项目初始化 | 5 | 15min |
| Stage 2: 解析器基础框架 | 4 | 35min |
| Stage 3: Airwallex解析器 | 7 | 1h50min |
| Stage 4: HSBC解析器 | 6 | 1h35min |
| Stage 5: 数据标准化与导出 | 6 | 1h10min |
| Stage 6: Streamlit界面 | 9 | 1h40min |
| Stage 7: 启动脚本与文档 | 4 | 30min |
| Stage 8: 全量测试 | 5 | 1h+ |
| **总计** | **46** | **约8-10小时** |

---

## 九、需求确认汇总 ✅

| 类别 | 需求项 | 确认结果 |
|-----|-------|---------|
| **数据解析** | Payer/Payee提取 | DeepSeek API**批量**解析（15条/批，可降级为正则） |
| **数据解析** | UUID处理 | 不保留 |
| **数据解析** | 中文标签（如"转账支出"） | 保留在Description |
| **数据解析** | 多币种处理(HSBC) | 增加Account Currency列 |
| **数据解析** | HSBC跨年处理 | 智能判断年份（交易月份>账单月份时年份-1） |
| **输出格式** | 文件方式 | 每个PDF单独输出一个Excel |
| **输出格式** | 日期格式 | YYYY-MM-DD |
| **输出格式** | 金额格式 | **纯数值**（2位小数，无货币符号） |
| **输出格式** | 货币信息 | 通过Account Currency列标识 |
| **输出格式** | 缺失Payer/Payee | 填写"Unknown" |
| **输出格式** | 汇总Sheet | 需要 |
| **技术实现** | Python版本 | 3.11.9 |
| **技术实现** | 界面 | **Streamlit**（Web UI，支持数据预览） |
| **技术实现** | 启动方式 | 一键启动脚本（.bat/.command） |
| **技术实现** | 日志 | 需要 |
| **技术实现** | DeepSeek API Key | 代码中预留变量，用户自行填写 |

---

## 十、依赖清单

```
# requirements.txt
pdfplumber>=0.10.0
pandas>=2.0.0
openpyxl>=3.1.0
python-dateutil>=2.8.0
openai>=1.0.0
streamlit>=1.29.0
```

> 注：Streamlit应用通过启动脚本运行，无需PyInstaller打包。

---

## 十一、GUI界面设计（Streamlit）

### 10.1 界面布局

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏦 银行对账单转换器 v1.0                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📁 上传PDF文件                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  拖拽文件到此处，或点击上传                                           │   │
│  │  支持批量上传多个PDF文件                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  已上传: HSBC 2024 01.pdf, HSBC 2024 02.pdf, Airwallex_HKD.pdf (3个文件)   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        [ 🚀 开始解析 ]                                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  📊 解析结果预览                                                            │
│                                                                             │
│  📄 HSBC 2024 01.pdf  [识别: HSBC | 币种: HKD, USD | 交易: 45条]            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Date       │ Currency │ Payer   │ Payee        │ Debit   │ Credit  │   │
│  ├────────────┼──────────┼─────────┼──────────────┼─────────┼─────────┤   │
│  │ 2024-05-08 │ HKD      │ Unknown │ UBER *TRIP   │ 127.48  │         │   │
│  │ 2024-05-09 │ HKD      │ Unknown │ UBER *TRIP   │ 66.97   │         │   │
│  │ 2024-05-10 │ HKD      │ Unknown │ UBER *TRIP   │ 130.25  │         │   │
│  │ ...        │ ...      │ ...     │ ...          │ ...     │ ...     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  📈 汇总: 期初 187,191.60 | 期末 184,765.11 | 收入 0.00 | 支出 2,426.49     │
│                                                                             │
│  ┌────────────────┐                                                        │
│  │ ⬇️ 下载Excel   │  ← 确认无误后点击下载                                   │
│  └────────────────┘                                                        │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  📋 处理日志                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ [10:30:01] ✅ 开始处理: HSBC 2024 01.pdf                             │   │
│  │ [10:30:02] ✅ 识别银行类型: HSBC                                      │   │
│  │ [10:30:03] ✅ 发现2个币种账户: HKD, USD                               │   │
│  │ [10:30:05] ✅ 提取交易记录: 45条                                      │   │
│  │ [10:30:06] ✅ 解析完成，等待下载                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  状态: ✅ 解析完成  |  成功: 3  |  失败: 0  |  总计: 3                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 核心功能

| 功能 | 说明 |
|-----|------|
| **文件上传** | 支持拖拽上传、批量选择多个PDF |
| **实时预览** | 解析后的数据以表格形式展示，支持滚动查看 |
| **数据核对** | 财务可在界面上检查数据是否正确，再决定下载 |
| **汇总统计** | 显示期初/期末余额、总收入/支出 |
| **一键下载** | 确认无误后下载Excel文件 |
| **批量处理** | 多个文件依次处理，分别预览和下载 |
| **处理日志** | 实时显示处理进度和状态 |

### 10.3 启动方式

**方式一：直接运行（开发/调试）**
```bash
streamlit run app.py
```

**方式二：一键启动脚本（用户使用）**

创建 `启动转换器.bat`（Windows）：
```batch
@echo off
title 银行对账单转换器
cd /d "%~dp0"
start /b streamlit run app.py --server.headless true
timeout /t 2 >nul
start http://localhost:8501
```

创建 `启动转换器.command`（Mac）：
```bash
#!/bin/bash
cd "$(dirname "$0")"
streamlit run app.py --server.headless true &
sleep 2
open http://localhost:8501
```

**效果**：用户双击脚本，自动打开浏览器显示界面，感觉像打开普通软件。

### 10.4 Streamlit代码结构预览

```python
# app.py
import streamlit as st
import pandas as pd
from src.parsers import AirwallexParser, HSBCParser
from src.exporter import export_to_excel

st.set_page_config(page_title="银行对账单转换器", page_icon="🏦", layout="wide")
st.title("🏦 银行对账单转换器")

# 文件上传
uploaded_files = st.file_uploader(
    "上传PDF文件", 
    type=["pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("🚀 开始解析"):
        for file in uploaded_files:
            with st.spinner(f"正在处理: {file.name}"):
                # 解析PDF
                df, summary = parse_pdf(file)
                
                # 预览数据
                st.subheader(f"📄 {file.name}")
                st.dataframe(df, use_container_width=True)
                
                # 显示汇总
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("期初余额", f"{summary['opening_balance']:,.2f}")
                col2.metric("期末余额", f"{summary['closing_balance']:,.2f}")
                col3.metric("总收入", f"{summary['total_credit']:,.2f}")
                col4.metric("总支出", f"{summary['total_debit']:,.2f}")
                
                # 下载按钮
                excel_data = export_to_excel(df, summary)
                st.download_button(
                    label="⬇️ 下载Excel",
                    data=excel_data,
                    file_name=f"{file.name.replace('.pdf', '')}_converted.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
```

---

## 十二、优化说明（已采纳）

### 11.1 金额列Excel友好度优化 ✅

**问题**：原方案中Debit/Credit/Balance格式为`23,500.00 HKD`，Excel会将其识别为文本，无法进行SUM等计算。

**解决方案**：
- 金额列（Debit/Credit/Balance）改为**纯数值**格式
- 货币信息通过独立的`Account Currency`列标识
- Excel中设置数值格式`#,##0.00`显示千位分隔符

**效果**：用户可直接使用`=SUM(E:E)`等公式进行计算。

---

### 11.2 DeepSeek API批量处理优化 ✅

**问题**：原方案逐条调用API，500条记录需要~4分钟，且易触发Rate Limit。

**解决方案**：
- 采用批量处理模式，每批15条记录
- 500条记录：500次调用 → 34次调用
- 耗时：~250秒 → ~17秒（提升15倍）

**降级策略**：单批失败时自动降级为正则解析，不影响其他批次。

---

### 11.3 HSBC跨年日期处理 ✅

**问题**：月度账单可能跨年（如12月~1月），直接用账单年份会导致12月交易日期错误。

**解决方案**：
```
if 交易月份 > 账单月份 + 6:
    年份 = 账单年份 - 1
```

**示例**：
- 账单日期：2024年1月8日
- 交易"18 Dec" → 2023-12-18 ✓（而非错误的2024-12-18）
- 交易"5 Jan" → 2024-01-05 ✓

---

### 11.4 UI框架升级为Streamlit ✅

**问题**：Tkinter界面功能有限，无法预览解析结果，用户体验较差。

**解决方案**：
- 采用Streamlit Web框架
- 支持在界面上**预览解析后的Excel数据表格**
- 财务可先核对数据，确认无误后再下载
- 显示汇总统计（期初/期末余额、收入/支出）
- 通过启动脚本封装，双击即可使用

**用户体验**：
```
双击"启动转换器.bat" 
    → 自动打开浏览器
    → 上传PDF
    → 预览解析结果（可滚动查看）
    → 确认无误后下载Excel
```

---

### 12.5 Windows文件占用锁处理 ✅

**问题**：Excel文件被打开时，程序写入会报`PermissionError`崩溃。

**解决方案**：try-except捕获，提示用户"请先关闭已打开的Excel文件"。

---

### 12.6 Streamlit缓存机制 ✅

**问题**：Streamlit每次交互都会重跑脚本，导致重复解析PDF。

**解决方案**：使用`@st.cache_data`装饰器缓存解析结果。

---

### 12.7 HSBC多币种状态机重置 ✅

**问题**：跨页时currency变量未重置，导致交易归类错误。

**解决方案**：检测到"Savings/Current"标题时立即重置`current_currency`。

---

*文档状态: ✅ 待用户审核*  
*审核通过后从Stage 1开始开发*  
*最后更新: 2025-12-31*  
*已采纳: 7项优化建议 + 3条开发规则 + V2 OCR预留 + 46项最小任务分割*
