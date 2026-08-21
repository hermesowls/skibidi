import re

def calculate_trim_weight(text: str) -> tuple:
    """Return (trimmed_ratio, remaining_ratio) based on qualitative or quantitative notes."""
    combined = text.lower()
    
    # Check for explicit fraction (e.g. 6/10, 1/2, 3/4)
    frac_match = re.search(r"(\d+)/(\d+)", combined)
    if frac_match:
        n = float(frac_match.group(1))
        d = float(frac_match.group(2))
        if d > 0 and n <= d:
            trim_r = n / d
            return trim_r, 1.0 - trim_r
            
    # Check qualitative runner / leave runner keywords
    if any(k in combined for k in ["runner", "runners", "leave runner", "free runner"]):
        return 0.85, 0.15  # 85% trimmed, 15% runner remaining
        
    # Standard trim default
    return 0.15, 0.85  # 15% trimmed, 85% remaining

test_cases = [
    "sold 6/10 RKLB at 4.20",
    "can take some RARE profits at 12%. De risk bio",
    "Sold another RKLB at 6.60! One free runner for ER",
    "sold 1/2 FCX at 3.30"
]

print("WEIGHTED TRIM RATIO TEST:\n")
for t in test_cases:
    trim_r, rem_r = calculate_trim_weight(t)
    print(f"Text: '{t}'")
    print(f"  -> Trimmed: {trim_r*100:.1f}% | Remaining Runner: {rem_r*100:.1f}%\n")
