import math
import re

def before(whereStr, whatStr):
    # Find first part and return slice before it.
    pos_a = whereStr.find(whatStr)
    if pos_a == -1: return ""
    return whereStr[0:pos_a]
    
def between(whereStr, whatStr1, whatStr2):
    # Find and validate before-part.
    pos_a = whereStr.find(whatStr1)
    if pos_a == -1: return ""
    # Find and validate after part.
    pos_b = whereStr.rfind(whatStr2)
    if pos_b == -1: return ""
    # Return middle part.
    adjusted_pos_a = pos_a + len(whatStr1)
    if adjusted_pos_a >= pos_b: return ""
    return whereStr[adjusted_pos_a:pos_b]

def after(whereStr, whatStr):
    # Find and validate first part.
    pos_a = whereStr.rfind(whatStr)
    if pos_a == -1: return ""
    # Returns chars after the found string.
    adjusted_pos_a = pos_a + len(whatStr)
    if adjusted_pos_a >= len(whereStr): return ""
    return whereStr[adjusted_pos_a:]

def decimalDegreeToDegMinStr(d):
#===============================
    return str(math.trunc(d))+'°'+'{:05.2f}'.format((abs(d)-math.trunc(abs(d)))*60.0)+'\''

def decimalLatToStr(d):
#======================
    h = 'N'
    if d < 0: 
        h = 'S'
    return str(math.trunc(abs(d)))+'°'+'{:05.2f}'.format((abs(d)-math.trunc(abs(d)))*60.0)+'\''+h

def decimalLonToStr(d):
#======================
    h = 'E'
    if d < 0:
        h = 'W'
    return str(math.trunc(abs(d))).zfill(3)+'°'+'{:05.2f}'.format((abs(d)-math.trunc(abs(d)))*60.0)+'\''+h
    
def latOrLonStrToDouble(S):
#==========================
    S = S.upper().strip()
    a = -1.0E-10
    if S != '':
        asign = 1.0
        if 'S' in S or 'W' in S:
            asign = -1.0
        res = re.match(r'(\d{1,3})\D(\d\d.\d\d)',S)
        if res != None:
            a = int(res[1])+float(res[2])/60
    return asign*a

def fourDigitLatOrLonToDecimalDegrees(S):
#========================================
    if type(s) is str:
        val = -1.0e-10
        coeff = 1
        if '-' in s or 'S' in s or 'W' in s:
            coeff = -1
        s = s.strip(" -NSEW")
        a,b = s.split('.')
        l = len(a)
        d = 0.0
        m = 0.0
        if l == 5:
            d = float(a[0:3])
            m = float(a[3:5])
        elif l == 4:
            d = float(a[0:2])   
            m = float(a[2:4])
        elif l == 3:
            d = float(a[0:1])   
            m = float(a[1:3])
        else:
            d = 0.0
            m = float(a)
        m = m + float('0.'+b)
        val = coeff*(d + m/60.0)
    else:
        val =  math.trunc(S/100)+(S-100*math.trunc(S/100))/60.0
    return val

def isDegMinStr(s):
    val = False
    if '°' in s:
        val = True
    return val