import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.test_improved_parser import parse_owls_alert

alerts = [
    ("Kian", "OPEN:\nVNET 12C 3/19exp .95 premium, i just want to feel something"),
    ("Jon",  "OPEN:\nRGTI 20C 10/16 Exp. at 2.15"),
    ("Kian", "OPEN:\n100% lotto biotech trade RARE 50C 11/20exp 2 premium, 0 stop"),
    ("Jon",  "OPEN:\nRKLB 100C 09/18 Exp at 3.80"),
    ("Jon",  "OPEN:\nFCX 75C 09/21 Exp at 3.0")
]

print("ANALYST ENTRY PREMIUM PARSING TEST:")
for analyst, a in alerts:
    sig = parse_owls_alert(a)
    p = sig['price']
    print(f"Analyst: {analyst:<5} | Ticker: {sig['ticker']:<5} {sig['strike']}C exp {sig['expiration']} | Entry Premium: ${p:.2f} | Total Contract Price: ${p*100:.2f}")
