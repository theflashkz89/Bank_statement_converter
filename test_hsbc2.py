"""
HSBC 解析器集成测试脚本
验证 HSBC 解析器是否工作正常
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.parsers.hsbc_parser import HSBCParser


def main():
    """主测试函数"""
    print("=" * 80)
    print("HSBC 解析器集成测试")
    print("=" * 80)
    
    # 查找 HSBC 文件夹
    hsbc_dir = project_root / "HSBC"
    
    if not hsbc_dir.exists():
        print(f"\n❌ 错误: 找不到 HSBC 目录: {hsbc_dir}")
        print("   请创建 HSBC 文件夹并放入 PDF 文件")
        return 1
    
    # 查找 PDF 文件
    pdf_files = list(hsbc_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"\n❌ 错误: HSBC 目录中没有找到 PDF 文件")
        print(f"   目录路径: {hsbc_dir}")
        print("   请将 HSBC PDF 文件放入该目录")
        return 1
    
    # 使用第一个 PDF 文件
    test_pdf = pdf_files[0]
    print(f"\n📄 测试文件: {test_pdf.name}")
    print(f"   完整路径: {test_pdf}")
    
    try:
        # 创建解析器
        parser = HSBCParser()
        
        # 提取账单日期（用于显示）
        statement_date = parser._extract_statement_date(str(test_pdf))
        print(f"\n📅 识别到的账单日期: {statement_date.strftime('%Y-%m-%d')}")
        
        # 解析 PDF
        print("\n⏳ 正在解析 PDF...")
        df, summary = parser.parse(str(test_pdf))
        
        # 打印交易总笔数
        print(f"\n📊 交易总笔数: {len(df)}")
        
        # 打印前 5 条交易详细数据
        print("\n" + "=" * 80)
        print("前 5 条交易详细数据:")
        print("=" * 80)
        
        if len(df) == 0:
            print("⚠️  警告: 没有提取到任何交易记录")
            return 1
        
        num_records = min(5, len(df))
        
        for idx in range(num_records):
            row = df.iloc[idx]
            print(f"\n【交易 #{idx + 1}】")
            print(f"  Date (日期): {row['Date']}")
            print(f"  Account Currency (账户币种): {row['Account Currency']}")
            print(f"  Payee (收款方): {row['Payee']}")
            print(f"  Debit (借方): {row['Debit'] if row['Debit'] else '(空)'}")
            print(f"  Credit (贷方): {row['Credit'] if row['Credit'] else '(空)'}")
            print(f"  Balance (余额): {row['Balance'] if row['Balance'] else '(空)'}")
            print(f"  Description (描述): {row['Description'][:80]}...")  # 只显示前80个字符
        
        # 打印汇总信息
        print("\n" + "=" * 80)
        print("汇总信息 (Summary):")
        print("=" * 80)
        for key, value in summary.items():
            if isinstance(value, (int, float)):
                if value is not None:
                    print(f"  {key}: {value:,.2f}" if isinstance(value, float) else f"  {key}: {value}")
                else:
                    print(f"  {key}: {value}")
            elif value is None:
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value}")
        
        print("\n" + "=" * 80)
        print("✅ 测试完成！")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 错误: 解析失败")
        print(f"错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

