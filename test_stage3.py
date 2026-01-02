"""
测试 Stage 3 - 验证多行 Details 解析逻辑修复
检查 Reference 字段是否从多行 Details 中正确提取
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.parsers.airwallex_parser import AirwallexParser


def main():
    """主测试函数"""
    # 获取项目根目录
    airwallex_dir = project_root / "Airwallex"
    
    if not airwallex_dir.exists():
        print(f"❌ 错误: 找不到 Airwallex 目录: {airwallex_dir}")
        return 1
    
    # 查找 PDF 文件
    pdf_files = list(airwallex_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ 错误: Airwallex 目录中没有找到 PDF 文件")
        return 1
    
    # 优先使用 HKD 文件（因为 plan.md 中的示例是 HKD，包含 Global Account Collection 的多行 Details）
    test_pdf = None
    for pdf in pdf_files:
        if "HKD" in pdf.name.upper():
            test_pdf = pdf
            break
    if not test_pdf:
        test_pdf = pdf_files[0]
    
    print("=" * 80)
    print(f"测试文件: {test_pdf.name}")
    print("=" * 80)
    
    try:
        # 创建解析器
        parser = AirwallexParser()
        
        # 解析 PDF
        print("\n正在解析 PDF...")
        df, summary = parser.parse(str(test_pdf))
        
        # 显示前 5 条交易记录（重点展示 Reference 字段）
        print("\n" + "=" * 80)
        print("前 5 条交易记录（重点检查 Reference 字段）:")
        print("=" * 80)
        
        if len(df) == 0:
            print("⚠️  警告: 没有提取到任何交易记录")
            return 1
        
        # 打印前 5 条（或全部，如果少于 5 条）
        num_records = min(5, len(df))
        
        for idx in range(num_records):
            row = df.iloc[idx]
            print(f"\n【交易 #{idx + 1}】")
            print(f"  日期: {row['Date']}")
            print(f"  账户币种: {row['Account Currency']}")
            print(f"  付款方 (Payer): {row['Payer']}")
            print(f"  收款方 (Payee): {row['Payee']}")
            print(f"  借方 (Debit): {row['Debit']}")
            print(f"  贷方 (Credit): {row['Credit']}")
            print(f"  余额 (Balance): {row['Balance']}")
            
            # 重点展示 Reference 字段
            reference = row['Reference']
            if reference:
                print(f"  ✅ 参考号 (Reference): {reference}")
            else:
                print(f"  ⚠️  参考号 (Reference): (空)")
            
            # 显示完整 Description（用于验证多行合并）
            description = row['Description']
            print(f"  描述 (Description): {description[:120]}...")  # 显示前120个字符
        
        # 检查是否有包含 Reference 的交易
        print("\n" + "=" * 80)
        print("Reference 字段提取统计:")
        print("=" * 80)
        
        ref_count = 0
        ref_examples = []
        for idx, row in df.iterrows():
            if row['Reference']:
                ref_count += 1
                if len(ref_examples) < 3:  # 只保存前3个示例
                    ref_examples.append({
                        'index': idx + 1,
                        'date': row['Date'],
                        'reference': row['Reference'],
                        'description': row['Description'][:100]
                    })
        
        print(f"  总交易数: {len(df)}")
        print(f"  包含 Reference 的交易数: {ref_count}")
        print(f"  Reference 提取率: {ref_count/len(df)*100:.1f}%")
        
        if ref_examples:
            print("\n  Reference 提取示例:")
            for ex in ref_examples:
                print(f"    - 交易 #{ex['index']} ({ex['date']}): {ex['reference']}")
                print(f"      Description: {ex['description']}...")
        
        # 显示 Summary 字典
        print("\n" + "=" * 80)
        print("Summary 字典:")
        print("=" * 80)
        for key, value in summary.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value} (类型: {type(value).__name__})")
            elif value is None:
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value}")
        
        print("\n" + "=" * 80)
        print(f"✅ 解析成功！共提取到 {len(df)} 条交易记录")
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

