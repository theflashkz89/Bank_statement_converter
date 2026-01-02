"""
工具函数模块 - 日期解析、金额解析等通用函数
"""
import re
from datetime import datetime
from dateutil import parser as date_parser
from typing import Optional


def parse_date_airwallex(date_str: str) -> Optional[str]:
    """
    解析Airwallex日期格式：如 "Jun 23 2024" -> "2024-06-23"
    
    参数:
        date_str: 日期字符串，如 "Jun 23 2024"
        
    返回:
        标准日期字符串 "YYYY-MM-DD"，解析失败返回None
    """
    if not date_str or not date_str.strip():
        return None
    
    try:
        # 使用dateutil解析，支持多种日期格式
        dt = date_parser.parse(date_str.strip())
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def parse_date_hsbc(date_str: str, statement_year: int, statement_month: int) -> Optional[str]:
    """
    解析HSBC日期格式：如 "8 May" -> "2024-05-08"（需要补充年份）
    
    参数:
        date_str: 日期字符串，如 "8 May" 或 "18 Dec"
        statement_year: 账单年份
        statement_month: 账单月份
        
    返回:
        标准日期字符串 "YYYY-MM-DD"，解析失败返回None
        
    逻辑:
        - 如果交易月份 > 账单月份 + 6，说明是上一年的交易（跨年处理）
    """
    if not date_str or not date_str.strip():
        return None
    
    try:
        # 解析日期（不包含年份）
        dt = date_parser.parse(date_str.strip(), default=datetime(statement_year, 1, 1))
        
        # 跨年判断：如果交易月份比账单月份大很多，说明是上一年的
        tx_month = dt.month
        if tx_month > statement_month + 6:
            # 交易月份比账单月份大超过6个月，说明是上一年的交易
            year = statement_year - 1
        else:
            year = statement_year
        
        # 重新构建日期
        result_dt = datetime(year, tx_month, dt.day)
        return result_dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def parse_amount(amount_str: str) -> Optional[float]:
    """
    解析金额字符串，去除货币符号和千位分隔符，转为纯数值
    
    参数:
        amount_str: 金额字符串，如 "23,500.00 HKD" 或 "30,132.99 HKD" 或 "23500.00"
        
    返回:
        浮点数金额，解析失败返回None
        
    示例:
        "23,500.00 HKD" -> 23500.00
        "30,132.99" -> 30132.99
        "64.90 HKD" -> 64.90
        "" -> None
    """
    if not amount_str or not amount_str.strip():
        return None
    
    try:
        # 去除货币符号（HKD, USD, CNY等）和空格
        cleaned = re.sub(r'[A-Z]{3}\s*$', '', amount_str.strip(), flags=re.IGNORECASE)
        cleaned = cleaned.strip()
        
        # 去除千位分隔符（逗号）
        cleaned = cleaned.replace(',', '')
        
        # 转换为浮点数
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_month(date_str: str) -> Optional[int]:
    """
    从日期字符串中提取月份数字
    
    参数:
        date_str: 日期字符串，如 "18 Dec" 或 "Jun 23 2024"
        
    返回:
        月份数字（1-12），解析失败返回None
    """
    if not date_str or not date_str.strip():
        return None
    
    try:
        dt = date_parser.parse(date_str.strip(), default=datetime(2024, 1, 1))
        return dt.month
    except (ValueError, TypeError):
        return None

