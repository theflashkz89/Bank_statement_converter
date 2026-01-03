"""
HSBC 对账单解析器
"""
import re
import logging
import pdfplumber
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from .base_parser import BaseParser
# 确保 utils 中有这些函数
from ..utils import parse_date_hsbc, parse_amount, parse_month


class HSBCParser(BaseParser):
    """HSBC 对账单解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def identify_bank(self, pdf_path: str) -> str:
        """识别银行类型"""
        if "HSBC" in pdf_path.upper():
            return "HSBC"
        return "Unknown"
    
    def parse(self, pdf_path: str) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """解析 HSBC PDF 对账单"""
        self.logger.info(f"开始解析 HSBC 文件: {pdf_path}")
        
        statement_date = self._extract_statement_date(pdf_path)
        
        # 提取交易记录
        transactions = self._extract_transactions(pdf_path, statement_date)
        
        # 提取汇总信息
        summary = self._extract_summary(pdf_path, transactions, len(transactions))
        
        df = pd.DataFrame(transactions)
        self.logger.info(f"解析完成: 提取到 {len(transactions)} 条交易记录")
        
        return df, summary
    
    def _extract_statement_date(self, pdf_path: str) -> datetime:
        """提取账单日期"""
        filename = Path(pdf_path).stem
        match = re.search(r'(\d{4})\s+(\d{1,2})', filename)
        if match:
            return datetime(int(match.group(1)), int(match.group(2)), 1)
        
        match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
        if match:
            return datetime(int(match.group(1)), int(match.group(2)), 1)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) > 0:
                    first_page_text = pdf.pages[0].extract_text() or ""
                    date_match = re.search(
                        r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})',
                        first_page_text, re.IGNORECASE
                    )
                    if date_match:
                        day = int(date_match.group(1))
                        month_str = date_match.group(2).lower()
                        year = int(date_match.group(3))
                        month_map = {
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                        }
                        return datetime(year, month_map.get(month_str, 1), day)
        except Exception as e:
            self.logger.warning(f"无法从PDF提取日期: {e}")
        
        return datetime.now()
    
    def _extract_transactions(self, pdf_path: str, statement_date: datetime) -> List[Dict[str, Any]]:
        """提取交易记录"""
        transactions = []
        # 状态机：记录当前处理的币种，默认为 Unknown
        current_currency = "Unknown"
        # 运行余额：用于计算每笔交易的Balance
        running_balance = {}  # {currency: balance}
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ""
                
                # 策略 1: 尝试表格提取 (HSBC 只有少部分格式支持表格)
                tables = page.extract_tables()
                if tables and len(tables) > 0 and len(tables[0]) > 2:
                    # 如果能提取到清晰的表格，使用表格逻辑
                    # 即使是表格模式，也需要检查页眉的币种以初始化状态
                    currency_match = re.search(r'(HKD|USD|CNY|EUR|GBP|AUD)\s+(Savings|Current)', page_text, re.IGNORECASE)
                    if currency_match:
                        current_currency = currency_match.group(1).upper()
                    
                    self._parse_tables(tables, current_currency, statement_date, transactions, running_balance)
                
                else:
                    # 策略 2: 文本流解析 (HSBC 主力解析模式)
                    # 重点：传入当前的 transactions 列表和 current_currency，并允许函数返回更新后的币种
                    current_currency = self._extract_transactions_from_text(
                        page_text, current_currency, statement_date, transactions, running_balance
                    )
        
        return transactions

    def _parse_tables(self, tables, currency, statement_date, transactions, running_balance: Dict[str, float]):
        """表格模式解析辅助函数"""
        for table in tables:
            if not table or len(table) < 2: continue
            
            # 寻找表头
            header_idx = -1
            for i, row in enumerate(table):
                row_str = "".join([str(c) for c in row if c]).upper()
                if "DATE" in row_str and "DETAILS" in row_str:
                    header_idx = i
                    break
            
            if header_idx == -1: continue

            for row in table[header_idx+1:]:
                if not row or len(row) < 4: continue
                # 简单过滤空行
                if all(not str(c).strip() for c in row if c): continue

                date_str = str(row[0]).strip() if row[0] else ""
                details_str = str(row[1]).strip() if row[1] else ""
                
                # HSBC Savings 表格通常: Date, Details, Deposit(存入), Withdrawal(提取), Balance
                # 注意列索引可能因对齐问题略有不同，这里按标准处理
                col_deposit = str(row[2]).strip() if row[2] else ""
                col_withdrawal = str(row[3]).strip() if len(row) > 3 and row[3] else ""
                col_balance = str(row[4]).strip() if len(row) > 4 and row[4] else ""

                if not date_str and transactions:
                    # 处理多行描述
                    transactions[-1]['Description'] += f" {details_str}"
                    continue

                date = parse_date_hsbc(date_str, statement_date.year, statement_date.month)
                if not date: continue

                # 提取金额
                debit = parse_amount(col_withdrawal) if col_withdrawal else ''
                credit = parse_amount(col_deposit) if col_deposit else ''
                
                # 计算Balance
                if col_balance:
                    # 如果表格中有Balance，使用表格中的
                    final_balance = parse_amount(col_balance)
                else:
                    # 基于运行余额计算
                    if currency not in running_balance:
                        running_balance[currency] = 0.0
                    credit_val = credit if credit else 0.0
                    debit_val = debit if debit else 0.0
                    final_balance = running_balance[currency] + credit_val - debit_val
                
                # 更新运行余额
                running_balance[currency] = final_balance

                tx = {
                    'Date': date,
                    'Account Currency': currency,
                    'Payer': 'Unknown',
                    'Payee': self._parse_transaction_details(details_str)['payee'],
                    'Debit': debit,
                    'Credit': credit,
                    'Balance': final_balance,
                    'Reference': '',
                    'Description': details_str
                }
                transactions.append(tx)

    def _extract_transactions_from_text(self, text: str, current_currency: str, 
                                       statement_date: datetime, 
                                       transactions: List[Dict[str, Any]],
                                       running_balance: Dict[str, float]) -> str:
        """
        从文本解析交易，支持行级币种切换
        返回: 更新后的 current_currency
        
        关键修复：同一天可能有多个交易，每个交易以POS MDC、CR TO等标识开始
        """
        lines = text.split('\n')
        
        # 临时变量，用于构建多行交易
        curr_date_str = None
        curr_details = []
        curr_balance = None
        
        # 交易类型标识模式（用于识别新交易）
        transaction_patterns = [
            r'^POS\s+MDC\s*\(',  # POS MDC (日期)
            r'^CR\s+TO\s+',       # CR TO
            r'^CASH\s+REBATE',   # CASH REBATE
            r'^B/F\s+BALANCE',   # B/F BALANCE
            r'^CREDIT\s+INTEREST',  # CREDIT INTEREST
            r'^PAID\s+BY',        # PAID BY
        ]
        
        # 识别包含Deposit和Balance的行（通常是新交易）
        # 格式：N10906097777(09JAN24) 2,000.00 220,760.08
        def is_deposit_with_balance(line: str) -> bool:
            """检查是否是包含Deposit金额和Balance的行"""
            # 匹配：字母数字(日期) 金额 余额
            pattern = r'[A-Z0-9]+\(\d{2}[A-Z]{3}\d{2}\)\s+[\d,]+\.[\d]{2}\s+[\d,]+\.[\d]{2}'
            return bool(re.search(pattern, line))
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # [Fix 1] 逐行检测币种切换
            curr_match = re.search(r'(HKD|USD|CNY|EUR|GBP|AUD)\s+(Savings|Current)', line, re.IGNORECASE)
            if curr_match:
                current_currency = curr_match.group(1).upper()
                self.logger.info(f"检测到账户切换: {current_currency}")
                continue # 标题行跳过
            
            # 跳过无用页眉
            if "Page" in line and "of" in line: continue
            if "Balance Brought Forward" in line: continue
            if "Date TransactionDetails" in line: continue  # 表头行

            # [Fix] 匹配日期行 (交易开始)
            date_match = re.match(r'^(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)', line, re.IGNORECASE)
            
            if date_match:
                # 遇到新日期，先保存上一条交易（如果存在）
                if curr_date_str and curr_details:
                    self._save_text_transaction(curr_date_str, curr_details, curr_balance, current_currency, statement_date, transactions, running_balance)
                
                # 初始化新交易
                curr_date_str = date_match.group(1)
                
                # 截取日期后的部分作为 Details
                rest = line[len(curr_date_str):].strip()
                
                # [Fix 2] 提取行末余额，并从 Details 中剔除，防止被误判为金额
                # 匹配行末的数字 (例如 123,456.78)，后面可能跟 CR/DR 标记
                balance_match = re.search(r'([\d,]+\.\d{2})[A-Z]*$', rest)
                
                if balance_match:
                    curr_balance = parse_amount(balance_match.group(1))
                    # 关键修复：从 rest 中移除余额部分
                    rest = rest[:balance_match.start()].strip()
                else:
                    curr_balance = None # 这一行没有余额，可能在后续行
                
                curr_details = [rest] if rest else []
                
            else:
                # 不是日期行，检查是否是新的交易标识（同一天内的第二个交易）
                if curr_date_str and curr_details:
                    # 检查这一行是否是新的交易类型标识
                    is_new_transaction = False
                    for pattern in transaction_patterns:
                        if re.match(pattern, line, re.IGNORECASE):
                            is_new_transaction = True
                            break
                    
                    # 检查是否是包含Deposit和Balance的行（通常是新交易）
                    if not is_new_transaction:
                        # 匹配：字母数字(日期) 金额 余额
                        deposit_balance_pattern = r'[A-Z0-9]+\(\d{2}[A-Z]{3}\d{2}\)\s+[\d,]+\.[\d]{2}\s+[\d,]+\.[\d]{2}'
                        if re.search(deposit_balance_pattern, line):
                            is_new_transaction = True
                    
                    if is_new_transaction:
                        # 这是同一天内的新交易，先保存上一条交易
                        self._save_text_transaction(curr_date_str, curr_details, curr_balance, current_currency, statement_date, transactions, running_balance)
                        # 开始新交易（使用相同的日期）
                        curr_details = [line]
                        curr_balance = None
                        continue
                
                # 不是新交易，属于上一条交易的 Details
                if curr_date_str:
                    # 检查这一行是否包含Balance
                    # Balance通常出现在行末，且是较大的数字
                    balance_match = re.search(r'([\d,]+\.\d{2})[A-Z]*$', line)
                    if balance_match:
                        potential_balance = parse_amount(balance_match.group(1))
                        # 如果这个数字很大（>1000），且行比较短，可能是Balance
                        if potential_balance and potential_balance > 1000 and len(line) < 30:
                            # 可能是余额行
                            curr_balance = potential_balance
                            # 从line中移除余额部分，剩余部分加入Details
                            remaining = line[:balance_match.start()].strip()
                            if remaining:
                                curr_details.append(remaining)
                        else:
                            # 是 Details 的一部分
                            curr_details.append(line)
                    else:
                        # 是 Details 的一部分
                        curr_details.append(line)
        
        # 循环结束，保存最后一条交易
        if curr_date_str and curr_details:
             self._save_text_transaction(curr_date_str, curr_details, curr_balance, current_currency, statement_date, transactions, running_balance)
             
        return current_currency

    def _save_text_transaction(self, date_str, details_list, balance, currency, statement_date, transactions, running_balance: Dict[str, float]):
        """构建并保存文本交易"""
        full_details = " ".join(details_list)
        
        # 尝试从详情中提取金额
        # 注意：Details中可能包含多个数字（Withdrawal/Credit金额和Balance）
        amounts = re.findall(r'([\d,]+\.\d{2})', full_details)
        
        debit, credit = '', ''
        extracted_balance = None
        
        # 从Details中提取Balance（通常是最后一个大数字，或者明确标记的）
        # 如果Details中包含Balance，优先使用提取的Balance
        if balance is not None:
            extracted_balance = balance
        elif amounts:
            # 检查最后一个数字是否是Balance
            # Balance通常出现在行末，且可能比较大
            last_amount = parse_amount(amounts[-1])
            # 如果最后一个数字很大（可能是Balance），且前面还有其他数字，则可能是Balance
            if len(amounts) > 1:
                # 有多个数字，最后一个可能是Balance
                prev_amount = parse_amount(amounts[-2]) if len(amounts) >= 2 else None
                # 如果最后一个数字明显大于前一个，可能是Balance
                if prev_amount and last_amount > prev_amount * 10:
                    extracted_balance = last_amount
                    # 移除Balance，剩下的数字是交易金额
                    amounts = amounts[:-1]
        
        # 获取当前运行余额
        if currency not in running_balance:
            running_balance[currency] = 0.0
        current_balance = running_balance[currency]
        
        if amounts:
            # 取最后一个数字作为交易金额（已排除Balance）
            amount_val = parse_amount(amounts[-1])
            
            # 判断方向：优先根据交易类型标识判断，然后根据Balance变化
            is_credit = False
            
            # 首先检查明确的交易类型标识
            # Credit关键词：明确的收入标识
            credit_keywords = ['CREDIT', 'DEPOSIT', 'INTEREST', 'REBATE', 'PAID BY', '转账收入', '轉賬收入', 'CASH REBATE']
            # Debit关键词：明确的支出标识
            debit_keywords = ['WITHDRAWAL', '轉賬支出', '转账支出', 'POS MDC', 'CR TO']
            
            has_credit_keyword = any(k in full_details.upper() for k in credit_keywords)
            has_debit_keyword = any(k in full_details.upper() for k in debit_keywords)
            
            if has_credit_keyword:
                is_credit = True
            elif has_debit_keyword:
                is_credit = False
            elif extracted_balance is not None:
                # 如果没有明确标识，根据Balance变化判断
                # 如果提取到了Balance，根据Balance变化判断
                if extracted_balance > current_balance:
                    is_credit = True  # Balance增加 = Credit
                elif extracted_balance < current_balance:
                    is_credit = False  # Balance减少 = Debit
                # 如果Balance不变，默认是Debit（POS MDC通常是支出）
            else:
                # 如果既没有Balance也没有关键词，默认是Debit（POS MDC通常是支出）
                is_credit = False
            
            if is_credit:
                credit = amount_val
            else:
                debit = amount_val
        
        # 计算Balance：如果提取到了Balance，使用提取的；否则基于运行余额计算
        if extracted_balance is not None:
            # 使用提取的Balance
            final_balance = extracted_balance
        else:
            # 基于运行余额计算
            credit_val = credit if credit else 0.0
            debit_val = debit if debit else 0.0
            final_balance = current_balance + credit_val - debit_val
        
        # 更新运行余额
        running_balance[currency] = final_balance
        
        # 解析日期
        date = parse_date_hsbc(date_str, statement_date.year, statement_date.month)
        if not date: return

        # 提取 Payee
        details_info = self._parse_transaction_details(full_details)

        tx = {
            'Date': date,
            'Account Currency': currency,
            'Payer': 'Unknown',
            'Payee': details_info.get('payee', 'Unknown'),
            'Debit': debit,
            'Credit': credit,
            'Balance': final_balance,
            'Reference': '',
            'Description': details_info.get('description', full_details)
        }
        transactions.append(tx)
    
    def _parse_transaction_details(self, details: str) -> Dict[str, str]:
        """解析 Transaction Details 字段"""
        if not details:
            return {"payee": "Unknown", "description": ""}
        
        # 这里的 details 已经是合并后的单行字符串，或者我们需要重新拆分？
        # 为了兼容之前的逻辑，我们简单分割一下，虽然可能不准确
        # 在文本模式下，details 已经被合并成一行了，这里尽量提取
        
        payee = "Unknown"
        description = details
        
        # 尝试提取 Payee：通常是全大写字母，可能在日期后面
        # 这是一个简化处理，V2 版本可以用 NER 或 AI 优化
        parts = details.split()
        if len(parts) > 1:
             # 假设前几个词可能是 Payee，直到遇到数字或特定符号
             possible_payee = []
             for part in parts:
                 if re.match(r'[A-Z0-9\*\.]+', part) and not re.match(r'\d+\.\d+', part):
                     possible_payee.append(part)
                 else:
                     break
             if possible_payee:
                 payee = " ".join(possible_payee)
        
        return {
            "payee": payee,
            "description": description
        }
    
    def _extract_payee_from_details(self, details: str) -> Optional[str]:
        return None # 辅助函数，暂不使用
    
    def _extract_summary(self, pdf_path: str, transactions: List[Dict[str, Any]], transaction_count: int) -> Dict[str, Any]:
        """提取汇总信息"""
        currencies = set()
        for tx in transactions:
            currency = tx.get('Account Currency', 'Unknown')
            if currency != 'Unknown':
                currencies.add(currency)
        
        opening_balance = None
        closing_balance = None
        
        if transactions:
            first_balance = transactions[0].get('Balance')
            if first_balance: opening_balance = first_balance
            
            last_balance = transactions[-1].get('Balance')
            if last_balance: closing_balance = last_balance
        
        total_credit = sum(tx.get('Credit', 0) or 0 for tx in transactions)
        total_debit = sum(tx.get('Debit', 0) or 0 for tx in transactions)
        
        period = ""
        if transactions:
            start_date = transactions[0].get('Date', '')
            end_date = transactions[-1].get('Date', '')
            if start_date and end_date:
                period = f"{start_date} ~ {end_date}"
        
        return {
            "原始文件": pdf_path,
            "银行": "HSBC",
            "账户币种": ', '.join(sorted(currencies)) if currencies else "Unknown",
            "统计期间": period,
            "期初余额": opening_balance,
            "期末余额": closing_balance,
            "总收入(Credit)": total_credit if total_credit > 0 else None,
            "总支出(Debit)": total_debit if total_debit > 0 else None,
            "交易笔数": transaction_count
        }
