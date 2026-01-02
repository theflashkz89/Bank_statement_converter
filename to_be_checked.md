# 待确认事项清单 - To Be Checked

> **说明**：请在每个问题后面直接填写您的回复，完成后告诉我即可。

---

## 一、格式分析确认

### 1.1 HSBC 对账单结构 ✅ 已分析

| 原始列名 | 中文 | 映射到 | 备注 |
|---------|------|-------|------|
| Date | 日期 | Date | 格式："8 May"，需补充年份 |
| Transaction Details | 进支详情 | Description + Payee | 包含商户名和交易类型 |
| Deposit | 存入 | Credit | |
| Withdrawal | 提取 | Debit | |
| Balance | 结余 | Balance | |
| ❌ 无 | - | Payer | 需从Details提取或留空 |
| ❌ 无 | - | Reference | HSBC无此字段 |

**请确认**：
- [ ] HSBC的年份信息在哪里获取？（页眉有"8 June 2024"，是否所有交易都是该月份？）
  > 您的回复：不是，HSBC有date,在第一列

- [ ] "转账支出"这类中文标签是否需要保留在Description中？
  > 您的回复：需要

---

### 1.2 Airwallex 对账单结构 ✅ 已分析

| 原始列名 | 映射到 | 备注 |
|---------|-------|------|
| Date | Date | 格式："Jun 23 2024" |
| Details | Description | 包含交易类型+子信息 |
| Credit | Credit | 收入 |
| Debit | Debit | 支出 |
| Balance | Balance | |
| Details子字段 | Payee | 如"to MONX TEAM LTD" |
| Details子字段 | Payer | 如"MDH INTERNATIONAL HONG KONG" |
| Details中的Ref | Reference | 如"Ref: INV 0016,0017,0019,0020" |

**请确认**：
- [ ] Airwallex的Details字段包含丰富信息，是否需要智能解析提取Payer/Payee？
  > 您的回复：需要

- [ ] Reference中的长UUID（如"47b3c949-2154-45bc-adc5-1a8136221642"）是否需要保留？
  > 您的回复：不需要

---

## 二、技术实现确认

### 2.1 PDF解析方式
- [ ] 两份PDF都是**原生PDF**（可直接提取文本），非扫描件，对吗？
  > 您的回复：是

### 2.2 DeepSeek API 使用场景
基于目前分析，两种对账单都是**结构化表格**，pdfplumber可以直接提取。

**DeepSeek API可能的用途**：
1. 从Details字段智能提取Payer/Payee（可选）
2. 自动识别银行类型（可选）
3. 处理异常/非标准格式（备用）

- [ ] 您是否希望使用DeepSeek API来智能解析Details字段？
  > 您的回复：可以

- [ ] 如果使用，请提供DeepSeek API Key或确认使用方式：
  > 您的回复：api

---

## 三、输出需求确认

### 3.1 输出文件格式
- [ ] 每个PDF单独输出一个Excel？还是合并所有文件到一个Excel（多Sheet）？
  > 您的回复：单独输出

### 3.2 Payer/Payee 处理策略
当无法明确识别Payer/Payee时：
- [ ] **选项A**：留空
- [ ] **选项B**：填写"Unknown"
- [ ] **选项C**：填写交易类型（如"UBER *TRIP"）

  > 您的选择：Unknown

### 3.3 日期格式
- [ ] 输出日期格式：`YYYY-MM-DD`（如2024-06-23），可以吗？
  > 您的回复：可以

### 3.4 金额格式
- [ ] 是否保留千位分隔符？（如 23,500.00 vs 23500.00）
  > 您的回复：保留

- [ ] 是否保留货币符号？（如 "23,500.00 HKD" vs "23500.00"）
  > 您的回复：对

---

## 四、运行环境确认

- [ ] Python版本？（推荐3.8+）
  > 您的回复：你自己查

- [ ] 是否需要打包成独立exe程序？（无需安装Python即可运行）
  > 您的回复：需要,pyinstaller

- [ ] 是否需要图形界面（GUI）？还是命令行即可？
  > 您的回复：GUI

---

## 五、其他需求

- [ ] 是否需要生成处理日志？
  > 您的回复：需要

- [ ] 是否需要汇总Sheet（期初余额、期末余额、总收入、总支出）？
  > 您的回复：需要

- [ ] 还有其他特殊需求吗？
  > 您的回复：

---

## 分析总结（基于截图）

### HSBC 对账单特点：
```
账户类型：HSBC Sprint Account HKD Savings（港元储蓄）
表格结构：Date | Transaction Details | Deposit | Withdrawal | Balance
日期格式：日 月（如 "8 May"），年份在页眉
交易描述：两行格式 - 第一行商户信息，第二行交易类型（如"转账支出"）
特点：
  - B/F BALANCE = 承前转结（期初余额）
  - POS MDC = 销售点交易
  - 无独立的Reference列
```

### Airwallex 对账单特点：
```
账户类型：HKD Account（港元账户）
表格结构：Date | Details | Credit | Debit | Balance
日期格式：月 日 年（如 "Jun 23 2024"）
交易类型：
  - Conversion = 货币转换
  - Payout = 付款
  - Global Account Collection = 全球账户收款
  - Fee = 手续费
特点：
  - Details包含丰富信息（交易方、Reference、金额说明）
  - 有明确的期初/期末余额汇总
  - 包含账户唯一标识（UUID）
```

---

*请填写上述问题后通知我，我们即可开始开发！*

---

## ✅ 需求确认汇总（已完成）

| 项目 | 确认结果 |
|-----|---------|
| **HSBC日期** | Date列在第一列，包含日期信息 |
| **中文标签** | 保留"转账支出"等标签 |
| **Airwallex解析** | 需要智能解析Payer/Payee |
| **UUID** | 不保留 |
| **PDF类型** | 原生PDF |
| **DeepSeek API** | 使用（需配置API Key） |
| **输出格式** | 每个PDF单独输出一个Excel |
| **Payer/Payee缺失** | 填写"Unknown" |
| **日期格式** | YYYY-MM-DD |
| **千位分隔符** | 保留 |
| **货币符号** | 保留 |
| **Python版本** | 3.11.9 ✅ |
| **打包方式** | PyInstaller打包exe |
| **界面** | GUI图形界面 |
| **日志** | 需要 |
| **汇总Sheet** | 需要 |

**状态：✅ 需求确认完成，可以开始开发！**

