M=97
def pred(base_c, d_units):  # d_units: list of (delta_digit, place_power) in tail numeric digits; weight -3*10^p
    return (base_c + sum(d*-3*pow(10,p,M) for d,p in d_units))%M
print("AC-0010",pred(14,[(-1,0),(1,1)]))
print("AC-0011",pred(14,[(1,1)]))
print("AC-0100",pred(14,[(-1,0),(1,2)]))
print("AC-0003",pred(14,[(2,0)]),"AC-0005",pred(14,[(4,0)]))
# TRANSFER 1->2 from 100000(12): amounts of 6 digits only
for a in (110000,150000,200000,999999): print(a,pred(12,[((a-100000)//10**4 ,4)]) if a%10**4==0 else None)
print("-3 mod97",(-3)%M,"10^2 mod97",pow(10,2,M))
