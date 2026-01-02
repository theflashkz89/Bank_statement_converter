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
                    
                    self._parse_tables(tables, current_currency, statement_date, transactions)
                
                else:
                    # 策略 2: 文本流解析 (HSBC 主力解析模式)
                    # 重点：传入当前的 transactions 列表和 current_currency，并允许函数返回更新后的币种
                    current_currency = self._extract_transactions_from_text(
                        page_text, current_currency, statement_date, transactions
                    )
        
        return transactions

    def _parse_tables(self, tables, currency, statement_date, transactions):
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

                tx = {
                    'Date': date,
                    'Account Currency': currency,
                    'Payer': 'Unknown',
                    'Payee': self._parse_transaction_details(details_str)['payee'],
                    'Debit': parse_amount(col_withdrawal) if col_withdrawal else '',
                    'Credit': parse_amount(col_deposit) if col_deposit else '',
                    'Balance': parse_amount(col_balance) if col_balance else '',
                    'Reference': '',
                    'Description': details_str
                }
                transactions.append(tx)

    def _extract_transactions_from_text(self, text: str, current_currency: str, 
                                       statement_date: datetime, 
                                       transactions: List[Dict[str, Any]]) -> str:
        """
        从文本解析交易，支持行级币种切换
        返回: 更新后的 current_currency
        """
        lines = text.split('\n')
        
        # 临时变量，用于构建多行交易
        curr_date_str = None
        curr_details = []
        curr_balance = None
        
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

            # [Fix] 匹配日期行 (交易开始)
            date_match = re.match(r'^(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)', line, re.IGNORECASE)
            
            if date_match:
                # 遇到新日期，先保存上一条交易（如果存在）
                if curr_date_str:
                    self._save_text_transaction(curr_date_str, curr_details, curr_balance, current_currency, statement_date, transactions)
                
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
                # 不是日期行，属于上一条交易的 Details
                if curr_date_str:
                    # 检查这一行是否是独立的余额行
                    # 特征：纯数字或带有 BALANCE 关键字
                    balance_match = re.search(r'([\d,]+\.\d{2})[A-Z]*$', line)
                    if balance_match and (len(line) < 20 or "BALANCE" in line.upper()):
                         # 假设它是余额行
                        curr_balance = parse_amount(balance_match.group(1))
                    else:
                        # 是 Details 的一部分
                        curr_details.append(line)
        
        # 循环结束，保存最后一条交易
        if curr_date_str:
             self._save_text_transaction(curr_date_str, curr_details, curr_balance, current_currency, statement_date, transactions)
             
        return current_currency

    def _save_text_transaction(self, date_str, details_list, balance, currency, statement_date, transactions):
        """构建并保存文本交易"""
        full_details = " ".join(details_list)
        
        # 尝试从详情中提取金额
        # 此时 full_details 应该已经被剔除了 Balance，剩下的数字是 Debit 或 Credit
        amounts = re.findall(r'([\d,]+\.\d{2})', full_details)
        
        debit, credit = '', ''
        
        if amounts:
            # 简单逻辑：取最后一个数字作为金额
            amount_val = parse_amount(amounts[-1])
            
            # 判断方向：根据关键词
            is_credit = False
            keywords = ['CREDIT', 'CR ', 'DEPOSIT', 'INTEREST', 'REBATE']
            if any(k in full_details.upper() for k in keywords):
                is_credit = True
            
            if is_credit:
                credit = amount_val
            else:
                debit = amount_val
        
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
            'Balance': balance if balance is not None else '',
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
