"""
解析器基类 - 所有银行对账单解析器的抽象基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd


class BaseParser(ABC):
    """银行对账单解析器抽象基类"""
    
    @abstractmethod
    def parse(self, pdf_path: str) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """
        解析PDF对账单文件
        
        参数:
            pdf_path: PDF文件路径
            
        返回:
            (transactions_df, summary_dict)
            - transactions_df: 交易记录DataFrame，包含9列标准字段
            - summary_dict: 汇总信息字典
        """
        pass
    
    @abstractmethod
    def identify_bank(self, pdf_path: str) -> str:
        """
        识别银行类型
        
        参数:
            pdf_path: PDF文件路径
            
        返回:
            银行类型标识（如 "Airwallex", "HSBC"）
        """
        pass



