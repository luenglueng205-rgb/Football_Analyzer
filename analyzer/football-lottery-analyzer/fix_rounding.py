from decimal import Decimal, ROUND_HALF_EVEN

def calc_jingcai_prize(odds_list):
    prod = Decimal('1.0')
    for o in odds_list:
        prod *= Decimal(str(o))
    
    # 竞彩公式是 2 * 乘积
    prize = Decimal('2.0') * prod
    # 保留两位小数，采用银行家舍入
    rounded = prize.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    return float(rounded)

print(calc_jingcai_prize([1.65, 1.75]))
print(calc_jingcai_prize([1.65, 1.46]))
print(calc_jingcai_prize([1.75, 1.46]))
print(calc_jingcai_prize([1.65, 1.75, 1.46]))
