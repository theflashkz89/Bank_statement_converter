"""
Stage 2 测试脚本 - 测试 utils.py 中的日期解析和金额解析函数
"""
import sys
from src.utils import parse_date_airwallex, parse_date_hsbc, parse_amount, parse_month


def test_date_parsing():
    """测试日期解析函数"""
    print("=" * 60)
    print("测试日期解析函数")
    print("=" * 60)
    
    # 测试 Airwallex 格式
    print("\n1. 测试 parse_date_airwallex (Airwallex格式: 'Jun 23 2024')")
    test_cases_airwallex = [
        ("Jun 23 2024", "2024-06-23"),
        ("Jul 30 2024", "2024-07-30"),
        ("Dec 31 2024", "2024-12-31"),
        ("Jan 1 2024", "2024-01-01"),
        ("", None),  # 空字符串
    ]
    
    passed = 0
    failed = 0
    for input_date, expected in test_cases_airwallex:
        result = parse_date_airwallex(input_date)
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"  {status} 输入: '{input_date}' -> 输出: {result} (期望: {expected})")
    
    # 测试 HSBC 格式
    print("\n2. 测试 parse_date_hsbc (HSBC格式: '8 May'，需要补充年份)")
    test_cases_hsbc = [
        # (日期字符串, 账单年份, 账单月份, 期望输出)
        ("8 May", 2024, 5, "2024-05-08"),
        ("18 Dec", 2024, 1, "2023-12-18"),  # 跨年测试：1月账单中的12月交易应该是去年
        ("5 Jan", 2024, 1, "2024-01-05"),
        ("10 May", 2024, 5, "2024-05-10"),
        ("31 Dec", 2024, 1, "2023-12-31"),  # 跨年测试
        ("", 2024, 5, None),  # 空字符串
    ]
    
    for input_date, stmt_year, stmt_month, expected in test_cases_hsbc:
        result = parse_date_hsbc(input_date, stmt_year, stmt_month)
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"  {status} 输入: '{input_date}' (账单: {stmt_year}-{stmt_month:02d}) -> 输出: {result} (期望: {expected})")
    
    print(f"\n日期解析测试结果: ✅ 通过 {passed} 个 | ❌ 失败 {failed} 个")
    return failed == 0


def test_amount_parsing():
    """测试金额解析函数"""
    print("\n" + "=" * 60)
    print("测试金额解析函数")
    print("=" * 60)
    
    print("\n测试 parse_amount (去除货币符号和千位分隔符)")
    test_cases_amount = [
        ("23,500.00 HKD", 23500.00),
        ("30,132.99 HKD", 30132.99),
        ("64.90 HKD", 64.90),
        ("6,632.99 HKD", 6632.99),
        ("23500.00", 23500.00),  # 无货币符号
        ("30,132.99", 30132.99),  # 无货币符号，有千位分隔符
        ("0.00 HKD", 0.00),
        ("", None),  # 空字符串
        ("   ", None),  # 空白字符串
    ]
    
    passed = 0
    failed = 0
    for input_amount, expected in test_cases_amount:
        result = parse_amount(input_amount)
        # 浮点数比较，允许小误差
        if expected is None:
            match = result is None
        else:
            match = result is not None and abs(result - expected) < 0.01
        
        status = "✅" if match else "❌"
        if match:
            passed += 1
        else:
            failed += 1
        print(f"  {status} 输入: '{input_amount}' -> 输出: {result} (期望: {expected})")
    
    print(f"\n金额解析测试结果: ✅ 通过 {passed} 个 | ❌ 失败 {failed} 个")
    return failed == 0


def test_month_parsing():
    """测试月份提取函数"""
    print("\n" + "=" * 60)
    print("测试月份提取函数")
    print("=" * 60)
    
    print("\n测试 parse_month (从日期字符串提取月份)")
    test_cases_month = [
        ("18 Dec", 12),
        ("8 May", 5),
        ("Jun 23 2024", 6),
        ("Jan 1 2024", 1),
        ("", None),
    ]
    
    passed = 0
    failed = 0
    for input_date, expected in test_cases_month:
        result = parse_month(input_date)
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"  {status} 输入: '{input_date}' -> 输出: {result} (期望: {expected})")
    
    print(f"\n月份提取测试结果: ✅ 通过 {passed} 个 | ❌ 失败 {failed} 个")
    return failed == 0


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Stage 2 功能测试 - utils.py 工具函数")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("日期解析", test_date_parsing()))
    results.append(("金额解析", test_amount_parsing()))
    results.append(("月份提取", test_month_parsing()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查代码")
        return 1


if __name__ == "__main__":
    sys.exit(main())

