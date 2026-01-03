"""
数据标准化模块 - 确保输出9列标准表头，处理缺失值
"""
import pandas as pd
from typing import Dict, Any
import logging


logger = logging.getLogger(__name__)


# 标准表头（9列）
STANDARD_COLUMNS = [
    'Date',
    'Account Currency',
    'Payer',
    'Payee',
    'Debit',
    'Credit',
    'Balance',
    'Reference',
    'Description'
]


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    标准化DataFrame，确保输出9列标准表头
    
    参数:
        df: 原始DataFrame（可能列名不标准或缺失列）
        
    返回:
        标准化后的DataFrame，包含9列标准字段
    """
    logger.info("开始标准化DataFrame...")
    
    # 创建新的DataFrame，确保包含所有标准列
    normalized_df = pd.DataFrame()
    
    # 1. Date - 确保是字符串格式 YYYY-MM-DD
    if 'Date' in df.columns:
        normalized_df['Date'] = df['Date'].astype(str)
    else:
        normalized_df['Date'] = ''
        logger.warning("缺少 Date 列，使用空字符串填充")
    
    # 2. Account Currency - 文本
    if 'Account Currency' in df.columns:
        normalized_df['Account Currency'] = df['Account Currency'].fillna('Unknown').astype(str)
    else:
        normalized_df['Account Currency'] = 'Unknown'
        logger.warning("缺少 Account Currency 列，使用 'Unknown' 填充")
    
    # 3. Payer - 文本，缺失值填 "Unknown"
    if 'Payer' in df.columns:
        normalized_df['Payer'] = df['Payer'].fillna('Unknown').astype(str)
    else:
        normalized_df['Payer'] = 'Unknown'
        logger.warning("缺少 Payer 列，使用 'Unknown' 填充")
    
    # 4. Payee - 文本，缺失值填 "Unknown"
    if 'Payee' in df.columns:
        normalized_df['Payee'] = df['Payee'].fillna('Unknown').astype(str)
    else:
        normalized_df['Payee'] = 'Unknown'
        logger.warning("缺少 Payee 列，使用 'Unknown' 填充")
    
    # 5. Debit - 纯数值，空值保持为空（不填0）
    if 'Debit' in df.columns:
        normalized_df['Debit'] = _normalize_amount_column(df['Debit'])
    else:
        normalized_df['Debit'] = None
        logger.warning("缺少 Debit 列，使用 None 填充")
    
    # 6. Credit - 纯数值，空值保持为空（不填0）
    if 'Credit' in df.columns:
        normalized_df['Credit'] = _normalize_amount_column(df['Credit'])
    else:
        normalized_df['Credit'] = None
        logger.warning("缺少 Credit 列，使用 None 填充")
    
    # 7. Balance - 纯数值，空值保持为空（不填0）
    if 'Balance' in df.columns:
        normalized_df['Balance'] = _normalize_amount_column(df['Balance'])
    else:
        normalized_df['Balance'] = None
        logger.warning("缺少 Balance 列，使用 None 填充")
    
    # 8. Reference - 文本，空值保持为空字符串
    if 'Reference' in df.columns:
        normalized_df['Reference'] = df['Reference'].fillna('').astype(str)
    else:
        normalized_df['Reference'] = ''
        logger.warning("缺少 Reference 列，使用空字符串填充")
    
    # 9. Description - 文本，空值保持为空字符串
    if 'Description' in df.columns:
        normalized_df['Description'] = df['Description'].fillna('').astype(str)
    else:
        normalized_df['Description'] = ''
        logger.warning("缺少 Description 列，使用空字符串填充")
    
    # 确保列顺序为标准顺序
    normalized_df = normalized_df[STANDARD_COLUMNS]
    
    logger.info(f"标准化完成: {len(normalized_df)} 条记录，{len(normalized_df.columns)} 列")
    
    return normalized_df


def _normalize_amount_column(series: pd.Series) -> pd.Series:
    """
    标准化金额列，确保是纯数值格式
    
    参数:
        series: 金额列（可能是字符串、数值或空值）
        
    返回:
        标准化后的Series（float类型，空值保持为NaN）
    """
    result = pd.Series(dtype=float)
    
    for idx, value in series.items():
        if pd.isna(value) or value == '' or value is None:
            # 空值保持为NaN（不填0）
            result.loc[idx] = None
        elif isinstance(value, (int, float)):
            # 已经是数值，直接使用
            result.loc[idx] = float(value)
        elif isinstance(value, str):
            # 字符串，尝试转换为数值
            value_clean = value.strip()
            if value_clean == '':
                result.loc[idx] = None
            else:
                try:
                    # 尝试直接转换
                    result.loc[idx] = float(value_clean)
                except ValueError:
                    # 如果失败，可能是包含货币符号，尝试提取数字
                    import re
                    # 提取数字（包括小数点）
                    numbers = re.findall(r'[\d,]+\.?\d*', value_clean)
                    if numbers:
                        # 取最后一个数字（通常是金额）
                        num_str = numbers[-1].replace(',', '')
                        try:
                            result.loc[idx] = float(num_str)
                        except ValueError:
                            logger.warning(f"无法解析金额: {value}，设为 None")
                            result.loc[idx] = None
                    else:
                        logger.warning(f"无法解析金额: {value}，设为 None")
                        result.loc[idx] = None
        else:
            logger.warning(f"未知的金额类型: {type(value)}, 值: {value}，设为 None")
            result.loc[idx] = None
    
    return result


def normalize_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化汇总信息字典
    
    参数:
        summary: 原始汇总信息字典
        
    返回:
        标准化后的汇总信息字典
    """
    normalized_summary = {}
    
    # 标准字段映射
    field_mapping = {
        '原始文件': '原始文件',
        '银行': '银行',
        '账户币种': '账户币种',
        '统计期间': '统计期间',
        '期初余额': '期初余额',
        '期末余额': '期末余额',
        '总收入(Credit)': '总收入(Credit)',
        '总支出(Debit)': '总支出(Debit)',
        '交易笔数': '交易笔数'
    }
    
    for key, value in summary.items():
        # 如果key在映射中，使用标准key
        standard_key = field_mapping.get(key, key)
        
        # 处理数值字段
        if standard_key in ['期初余额', '期末余额', '总收入(Credit)', '总支出(Debit)', '交易笔数']:
            if value is None or value == '':
                normalized_summary[standard_key] = None
            elif isinstance(value, (int, float)):
                normalized_summary[standard_key] = value
            else:
                # 尝试转换为数值
                try:
                    normalized_summary[standard_key] = float(value)
                except (ValueError, TypeError):
                    logger.warning(f"无法转换 {standard_key} 为数值: {value}")
                    normalized_summary[standard_key] = None
        else:
            # 文本字段
            if value is None:
                normalized_summary[standard_key] = ''
            else:
                normalized_summary[standard_key] = str(value)
    
    # 确保所有标准字段都存在
    for key in field_mapping.values():
        if key not in normalized_summary:
            if key in ['期初余额', '期末余额', '总收入(Credit)', '总支出(Debit)']:
                normalized_summary[key] = None
            elif key == '交易笔数':
                normalized_summary[key] = 0
            else:
                normalized_summary[key] = ''
    
    return normalized_summary



