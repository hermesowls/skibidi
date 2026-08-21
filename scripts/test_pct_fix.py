import re

text = "can take some RARE profits at 12%. De risk bio"

pct_match = re.search(r"(\d+(?:\.\d+)?)%", text)
text_no_pct = re.sub(r"\d+(?:\.\d+)?%\s*", "", text)

print("Original text:", text)
print("Text without percentage:", text_no_pct)

if pct_match:
    roi = float(pct_match.group(1))
    entry = 2.00
    exit_p = round(entry * (1.0 + roi / 100.0), 2)
    print(f"✓ Extracted Percentage ROI: {roi}%")
    print(f"✓ Entry Price: ${entry:.2f} -> Calculated Exit Price: ${exit_p:.2f} (Realized ROI: +{roi:.1f}%)")
