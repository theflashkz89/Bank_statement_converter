"""
Airwallex 对账单解析器
"""
import re
import logging
import pdfplumber
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_parser import BaseParser
from ..utils import parse_date_airwallex, parse_amount


class AirwallexParser(BaseParser):
    """Airwallex 对账单解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def identify_bank(self, pdf_path: str) -> str:
        """识别银行类型"""
        # 从文件名判断
        if "ASR_" in pdf_path.upper() or "airwallex" in pdf_path.lower():
            return "Airwallex"
        return "Unknown"
    
    def parse(self, pdf_path: str) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """
        解析 Airwallex PDF 对账单
        
        返回:
            (transactions_df, summary_dict)
        """
        self.logger.info(f"开始解析 Airwallex 文件: {pdf_path}")
        
        # 提取币种
        currency = self._extract_currency_from_filename(pdf_path)
        
        # 提取交易记录
        transactions = self._extract_transactions(pdf_path, currency)
        
        # 提取汇总信息（传入交易笔数，避免重复解析）
        summary = self._extract_summary(pdf_path, currency, len(transactions))
        
        # 转换为 DataFrame
        df = pd.DataFrame(transactions)
        
        self.logger.info(f"解析完成: 提取到 {len(transactions)} 条交易记录")
        
        return df, summary
    
    def _extract_currency_from_filename(self, pdf_path: str) -> str:
        """从文件名提取币种"""
        # 文件名格式: {序号}-{公司名}-ASR_{币种}_{开始日期}_{结束日期}.pdf
        match = re.search(r'ASR_([A-Z]{3})_', pdf_path)
        if match:
            return match.group(1)
        return "Unknown"
    
    def _extract_transactions(self, pdf_path: str, currency: str) -> List[Dict[str, Any]]:
        """提取交易记录"""
        transactions = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # 提取表格
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # 查找表头行
                    header_row_idx = None
                    for i, row in enumerate(table):
                        if row and len(row) >= 5:
                            # 检查是否是表头（包含 Date, Details, Credit, Debit, Balance）
                            row_text = ' '.join([str(cell) if cell else '' for cell in row]).upper()
                            if 'DATE' in row_text and 'DETAILS' in row_text:
                                header_row_idx = i
                                break
                    
                    if header_row_idx is None:
                        continue
                    
                    # 处理数据行
                    for row_idx in range(header_row_idx + 1, len(table)):
                        row = table[row_idx]
                        if not row or len(row) < 5:
                            continue
                        
                        # 跳过空行
                        if all(not cell or str(cell).strip() == '' for cell in row):
                            continue
                        
                        # 提取字段
                        date_str = str(row[0]).strip() if row[0] else ""
                        details_str = str(row[1]).strip() if row[1] else ""
                        credit_str = str(row[2]).strip() if row[2] else ""
                        debit_str = str(row[3]).strip() if row[3] else ""
                        balance_str = str(row[4]).strip() if row[4] else ""
                        
                        # 如果日期为空，可能是多行 Details 的延续，合并到上一条记录
                        if not date_str and transactions:
                            # 合并到上一条记录的 Details
                            last_tx = transactions[-1]
                            if details_str:
                                # 合并 Description
                                last_tx['Description'] = (last_tx.get('Description', '') + ' ' + details_str).strip()
                                
                                # 重新解析合并后的完整描述，提取 Reference、Payer、Payee 等信息
                                details_info = self._parse_details_with_regex(last_tx['Description'])
                                
                                # 如果字段是默认值，则用新解析的结果更新它们
                                if last_tx.get('Payer') == 'Unknown' and details_info.get('payer') != 'Unknown':
                                    last_tx['Payer'] = details_info.get('payer', 'Unknown')
                                
                                if last_tx.get('Payee') == 'Unknown' and details_info.get('payee') != 'Unknown':
                                    last_tx['Payee'] = details_info.get('payee', 'Unknown')
                                
                                # Reference 字段：如果之前为空，则更新
                                if not last_tx.get('Reference') and details_info.get('reference'):
                                    last_tx['Reference'] = details_info.get('reference', '')
                            continue
                        
                        # 解析日期
                        date = parse_date_airwallex(date_str)
                        if not date:
                            continue
                        
                        # 解析金额
                        credit = parse_amount(credit_str) if credit_str else None
                        debit = parse_amount(debit_str) if debit_str else None
                        balance = parse_amount(balance_str) if balance_str else None
                        
                        # 解析 Details 字段（正则解析）
                        details_info = self._parse_details_with_regex(details_str)
                        
                        # 构建交易记录
                        transaction = {
                            'Date': date,
                            'Account Currency': currency,
                            'Payer': details_info.get('payer', 'Unknown'),
                            'Payee': details_info.get('payee', 'Unknown'),
                            'Debit': debit if debit else '',
                            'Credit': credit if credit else '',
                            'Balance': balance if balance else '',
                            'Reference': details_info.get('reference', ''),
                            'Description': details_str
                        }
                        
                        transactions.append(transaction)
        
        return transactions
    
    def _parse_details_with_regex(self, details: str) -> Dict[str, str]:
        """
        使用正则表达式解析 Details 字段
        
        返回:
            {"payer": str, "payee": str, "reference": str}
        """
        if not details:
            return {"payer": "Unknown", "payee": "Unknown", "reference": ""}
        
        details_upper = details.upper()
        payer = "Unknown"
        payee = "Unknown"
        reference = ""
        
        # 1. Conversion 类型
        if "CONVERSION" in details_upper:
            payer = "Self"
            payee = "Unknown"
        
        # 2. Payout 类型: "Pay {币种} {金额} to {Payee}"
        elif "PAYOUT" in details_upper:
            payer = "Self"
            # 提取 "to" 后的公司名
            match = re.search(r'to\s+([A-Z][A-Z\s&.,-]+?)(?:\s*\||\s*$)', details, re.IGNORECASE)
            if match:
                payee = match.group(1).strip()
            else:
                payee = "Unknown"
        
        # 3. Global Account Collection 类型
        elif "GLOBAL ACCOUNT COLLECTION" in details_upper:
            payee = "Self"
            # 提取第一个 "|" 前的公司名作为 Payer
            parts = details.split('|')
            if len(parts) > 0:
                first_part = parts[0].strip()
                # 移除 "Global Account Collection" 前缀
                first_part = re.sub(r'Global Account Collection\s*', '', first_part, flags=re.IGNORECASE).strip()
                if first_part:
                    payer = first_part
                else:
                    payer = "Unknown"
            
            # 提取 Reference: "Ref: {内容}"
            ref_match = re.search(r'Ref:\s*([^|]+)', details, re.IGNORECASE)
            if ref_match:
                ref_text = ref_match.group(1).strip()
                # 过滤掉 UUID 格式的 ID
                ref_parts = []
                for part in ref_text.split(','):
                    part = part.strip()
                    # 跳过 UUID 格式（如 47b3c949-2154-45bc-adc5-1a8136221642）
                    if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', part, re.IGNORECASE):
                        ref_parts.append(part)
                reference = ', '.join(ref_parts)
        
        # 4. Fee 类型
        elif "FEE" in details_upper:
            payer = "Self"
            payee = "Airwallex"
        
        # 默认情况
        else:
            payer = "Unknown"
            payee = "Unknown"
        
        return {
            "payer": payer,
            "payee": payee,
            "reference": reference
        }
    
    def _extract_summary(self, pdf_path: str, currency: str, transaction_count: int) -> Dict[str, Any]:
        """
        提取汇总信息（仅从页眉/页脚文本提取，不解析表格）
        
        参数:
            pdf_path: PDF文件路径
            currency: 币种
            transaction_count: 交易笔数（由调用方传入，避免重复解析）
        """
        summary = {
            "原始文件": pdf_path,
            "银行": "Airwallex",
            "账户币种": currency,
            "统计期间": "",
            "期初余额": None,
            "期末余额": None,
            "总收入(Credit)": None,
            "总支出(Debit)": None,
            "交易笔数": transaction_count
        }
        
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() or ""
            
            # 提取期初余额: "Starting balance on {日期} {金额} {币种}"
            # 格式: "Starting balance on Jan 01 2024 0.00 HKD"
            start_match = re.search(
                rf'Starting balance on\s+([A-Za-z]+\s+\d+\s+\d+)\s+([\d,]+\.\d+)\s+{currency}',
                full_text,
                re.IGNORECASE
            )
            if start_match:
                start_date_str = start_match.group(1).strip()
                start_balance_str = start_match.group(2)
                # 直接解析纯数字字符串，不添加货币符号
                summary["期初余额"] = parse_amount(start_balance_str)
                # 解析开始日期
                start_date = parse_date_airwallex(start_date_str)
                if start_date:
                    summary["统计期间"] = start_date
            
            # 提取期末余额: "Ending balance on {日期} {金额} {币种}"
            # 格式: "Ending balance on Dec 31 2025 369.86 HKD"
            end_match = re.search(
                rf'Ending balance on\s+([A-Za-z]+\s+\d+\s+\d+)\s+([\d,]+\.\d+)\s+{currency}',
                full_text,
                re.IGNORECASE
            )
            if end_match:
                end_date_str = end_match.group(1).strip()
                end_balance_str = end_match.group(2)
                # 直接解析纯数字字符串，不添加货币符号
                summary["期末余额"] = parse_amount(end_balance_str)
                # 解析结束日期
                end_date = parse_date_airwallex(end_date_str)
                if end_date and summary["统计期间"]:
                    summary["统计期间"] = f"{summary['统计期间']} ~ {end_date}"
            
            # 提取总收入: "Total collections and other additions {金额} {币种}"
            # 格式: "Total collections and other additions 633,081.56 HKD"
            credit_match = re.search(
                rf'Total collections and other additions\s+([\d,]+\.\d+)\s+{currency}',
                full_text,
                re.IGNORECASE
            )
            if credit_match:
                # 直接解析纯数字字符串，不添加货币符号
                summary["总收入(Credit)"] = parse_amount(credit_match.group(1))
            
            # 提取总支出: "Total payouts and other subtractions {金额} {币种}"
            # 格式: "Total payouts and other subtractions 632,711.70 HKD"
            debit_match = re.search(
                rf'Total payouts and other subtractions\s+([\d,]+\.\d+)\s+{currency}',
                full_text,
                re.IGNORECASE
            )
            if debit_match:
                # 直接解析纯数字字符串，不添加货币符号
                summary["总支出(Debit)"] = parse_amount(debit_match.group(1))
        
        return summary

