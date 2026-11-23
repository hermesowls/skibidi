#!/usr/bin/env python3
"""
Flowseeker Dual-Panel Visual Tape Chart Generator.

Generates pixel-perfect, high-resolution Flowseeker contract drilldown charts matching
the authentic dark institutional tape aesthetic:
  - Top Bar: Contract Drilldown | Ticker Strike Type Expiration - DTE | Spot Price & Change
  - Left Panel: CONTRACT FLOW (Vol, OI, Avg, Prem, OTM%, Vol/OI, Contract Ratio, Flow Prints & Glow Spline)
  - Right Panel: NET PREMIUM (Total Vol, Notional, Net Flow, NCP, NPP, Sentiment Bar, Cumulative Net Curves)
"""

import math
import random
import os
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Load standard system TrueType font or fallback."""
    font_names = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Monaco.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fn in font_names:
        if os.path.exists(fn):
            try:
                return ImageFont.truetype(fn, size)
            except Exception:
                pass
    return ImageFont.load_default()


def generate_flowseeker_chart(
    ticker: str,
    strike: float,
    call_put: str,
    expiration: str,
    premium_usd: float = 1_500_000.0,
    dte: Optional[int] = None,
    spot_price: Optional[float] = None,
    spot_change_pct: Optional[float] = None,
    output_path: Optional[str] = None,
) -> str:
    """
    Renders high-resolution (1280x640) Flowseeker dual-panel contract drilldown visual tape.
    """
    ticker = ticker.upper().strip()
    call_put = "CALL" if call_put.upper().startswith("C") else "PUT"
    cp_char = "C" if call_put == "CALL" else "P"
    
    if dte is None:
        dte = 30
    if spot_price is None or spot_price <= 0:
        # Realistic spot estimation relative to strike
        if call_put == "CALL":
            spot_price = strike * 0.95  # 5% OTM
        else:
            spot_price = strike * 1.05  # 5% OTM
    if spot_change_pct is None:
        spot_change_pct = 1.25 if call_put == "CALL" else -1.45

    # Derive deterministic realistic metrics seeded by ticker+strike
    seed_val = int(sum(ord(c) for c in ticker) * 1000 + strike * 10)
    rng = random.Random(seed_val)

    is_call = call_put == "CALL"
    vol = rng.randint(2_800, 18_500)
    oi = rng.randint(450, 6_200)
    vol_oi = round(vol / max(1, oi), 2)
    avg_price = round(premium_usd / (vol * 100), 2) if vol > 0 else 14.50
    avg_price = max(0.50, min(120.0, avg_price))
    
    otm_pct = abs((strike - spot_price) / spot_price) * 100

    ask_pct = rng.randint(55, 88) if is_call else rng.randint(15, 45)
    bid_pct = 100 - ask_pct
    ask_count = int(vol * (ask_pct / 100.0))
    bid_count = vol - ask_count
    mid_count = rng.randint(50, 400)

    # Net Premium Metrics
    tot_vol = int(vol * rng.uniform(25.0, 75.0))
    tot_prem = premium_usd * rng.uniform(8.0, 28.0)
    bull_pct = ask_pct if is_call else (100 - ask_pct)
    bear_pct = 100 - bull_pct

    # Palette
    BG_COLOR = (11, 15, 23)          # #0B0F17
    PANEL_BG = (14, 19, 29)          # #0E131D
    BORDER_COLOR = (30, 41, 59)      # #1E293B
    TEXT_WHITE = (241, 245, 249)     # #F1F5F9
    TEXT_MUTED = (148, 163, 184)     # #94A3B8
    TEXT_DIM = (100, 116, 139)       # #64748B
    GREEN_ASK = (38, 166, 154)       # #26A69A / Emerald
    RED_BID = (239, 83, 80)          # #EF5350 / Rose
    CYAN_LINE = (0, 229, 255)        # #00E5FF
    PURPLE_ACCENT = (168, 85, 247)   # #A855F7
    GRID_COLOR = (22, 30, 44)        # Subdued grid
    WATERMARK = (26, 36, 52)         # Flowseeker watermark

    W, H = 1280, 620
    im = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(im)

    font_title = _get_font(15, bold=True)
    font_bold = _get_font(12, bold=True)
    font_body = _get_font(11, bold=False)
    font_small = _get_font(10, bold=False)
    font_watermark = _get_font(52, bold=True)

    # 1. Top Bar
    draw.rectangle([(0, 0), (W, 44)], fill=(8, 11, 18))
    draw.line([(0, 44), (W, 44)], fill=BORDER_COLOR, width=1)

    # Top Bar Text
    top_str_left = f"Contract Drilldown  |  {ticker} {strike:g} {cp_char} {expiration} - {dte} DTE  |  {ticker} ${spot_price:.2f}"
    change_str = f" ({spot_change_pct:+.2f}%)"
    draw.text((20, 14), top_str_left, fill=TEXT_WHITE, font=font_title)
    
    # Measure and draw colored change
    left_bbox = draw.textbbox((20, 14), top_str_left, font=font_title)
    change_color = GREEN_ASK if spot_change_pct >= 0 else RED_BID
    draw.text((left_bbox[2] + 4, 14), change_str, fill=change_color, font=font_title)

    # Top Bar Right buttons
    draw.rounded_rectangle([(W - 130, 10), (W - 80, 34)], radius=4, fill=(22, 30, 46))
    draw.text((W - 120, 15), "1D ▾", fill=TEXT_WHITE, font=font_bold)
    draw.rounded_rectangle([(W - 70, 10), (W - 20, 34)], radius=4, fill=(22, 30, 46))
    draw.text((W - 60, 15), "5min ▾", fill=TEXT_WHITE, font=font_bold)

    # Panel Layout Dimensions
    P_MARGIN = 14
    P_GAP = 14
    P_W = (W - 2 * P_MARGIN - P_GAP) // 2
    P_TOP = 56
    P_BOTTOM = H - P_MARGIN

    # 2. LEFT PANEL: CONTRACT FLOW
    p1_left = P_MARGIN
    p1_right = p1_left + P_W
    draw.rounded_rectangle([(p1_left, P_TOP), (p1_right, P_BOTTOM)], radius=10, fill=PANEL_BG, outline=BORDER_COLOR, width=1)

    # Panel 1 Header
    draw.text((p1_left + 16, P_TOP + 14), "CONTRACT FLOW", fill=TEXT_WHITE, font=font_bold)
    draw.rounded_rectangle([(p1_right - 100, P_TOP + 10), (p1_right - 60, P_TOP + 30)], radius=4, fill=(22, 30, 46))
    draw.text((p1_right - 92, P_TOP + 13), "1D ▾", fill=TEXT_MUTED, font=font_small)
    draw.rounded_rectangle([(p1_right - 52, P_TOP + 10), (p1_right - 12, P_TOP + 30)], radius=4, fill=(22, 30, 46))
    draw.text((p1_right - 46, P_TOP + 13), "5min ▾", fill=TEXT_MUTED, font=font_small)

    # Panel 1 Metrics
    metrics_p1 = f"Vol: {vol:,}   OI: {oi:,}   Avg: ${avg_price:.2f}   Prem: ${premium_usd:,.0f}   OTM: {otm_pct:.0f}%   Vol/OI: {vol_oi}   Multi: 0%"
    draw.text((p1_left + 16, P_TOP + 40), metrics_p1, fill=TEXT_MUTED, font=font_small)

    # Contract Ratio Bar
    bar_y = P_TOP + 62
    bar_w = P_W - 32
    draw.text((p1_left + 16, bar_y - 2), "Contract Ratio", fill=TEXT_DIM, font=font_small)
    
    ratio_bar_y = bar_y + 16
    draw.rounded_rectangle([(p1_left + 16, ratio_bar_y), (p1_left + 16 + bar_w, ratio_bar_y + 6)], radius=3, fill=(30, 41, 59))
    bid_w = int(bar_w * (bid_pct / 100.0))
    draw.rounded_rectangle([(p1_left + 16, ratio_bar_y), (p1_left + 16 + bid_w, ratio_bar_y + 6)], radius=3, fill=RED_BID)
    draw.rounded_rectangle([(p1_left + 16 + bid_w, ratio_bar_y), (p1_left + 16 + bar_w, ratio_bar_y + 6)], radius=3, fill=GREEN_ASK)

    draw.text((p1_left + 16, ratio_bar_y + 10), f"Bid {bid_pct}%", fill=RED_BID, font=font_small)
    draw.text((p1_right - 60, ratio_bar_y + 10), f"Ask {ask_pct}%", fill=GREEN_ASK, font=font_small)

    # Legend Row
    leg_y = ratio_bar_y + 28
    draw.ellipse([(p1_left + 16, leg_y + 2), (p1_left + 22, leg_y + 8)], fill=RED_BID)
    draw.text((p1_left + 26, leg_y), f"Bid: {bid_count:,}", fill=TEXT_MUTED, font=font_small)

    draw.ellipse([(p1_left + 110, leg_y + 2), (p1_left + 116, leg_y + 8)], fill=TEXT_DIM)
    draw.text((p1_left + 120, leg_y), f"Mid: {mid_count:,}", fill=TEXT_MUTED, font=font_small)

    draw.ellipse([(p1_left + 190, leg_y + 2), (p1_left + 196, leg_y + 8)], fill=GREEN_ASK)
    draw.text((p1_left + 200, leg_y), f"Ask: {ask_count:,}", fill=TEXT_MUTED, font=font_small)

    # Chart Box P1
    c1_x1, c1_y1 = p1_left + 16, leg_y + 22
    c1_x2, c1_y2 = p1_right - 16, P_BOTTOM - 26
    draw.rectangle([(c1_x1, c1_y1), (c1_x2, c1_y2)], fill=(10, 14, 22), outline=(22, 30, 44), width=1)

    # Watermark P1
    draw.text((c1_x1 + (c1_x2 - c1_x1)//2 - 120, c1_y1 + (c1_y2 - c1_y1)//2 - 30), "Flowseeker", fill=WATERMARK, font=font_watermark)

    # Grid Lines
    for gy in range(c1_y1 + 40, c1_y2, 50):
        draw.line([(c1_x1, gy), (c1_x2, gy)], fill=GRID_COLOR, width=1)
    for gx in range(c1_x1 + 80, c1_x2, 110):
        draw.line([(gx, c1_y1), (gx, c1_y2)], fill=GRID_COLOR, width=1)

    # Generate Synthetic Order Flow Spikes & Glow Path
    num_pts = 42
    pts = []
    base_val = avg_price * 0.8
    val = base_val
    for i in range(num_pts):
        px = c1_x1 + int((i / (num_pts - 1)) * (c1_x2 - c1_x1 - 40))
        val += rng.uniform(-0.6, 0.9) if is_call else rng.uniform(-0.9, 0.6)
        val = max(avg_price * 0.4, val)
        py = c1_y2 - 20 - int(((val - avg_price * 0.4) / (avg_price * 1.6)) * (c1_y2 - c1_y1 - 60))
        py = max(c1_y1 + 20, min(c1_y2 - 20, py))
        pts.append((px, py))

        # Volume bars at bottom
        if rng.random() > 0.45:
            bar_h = rng.randint(15, 140)
            bar_color = GREEN_ASK if rng.random() < (ask_pct / 100.0) else RED_BID
            draw.rectangle([(px - 3, c1_y2 - bar_h), (px + 3, c1_y2 - 2)], fill=bar_color)

    # Draw Smooth Glow Spline for Contract Mark
    for i in range(len(pts) - 1):
        # Outer glow
        draw.line([pts[i], pts[i+1]], fill=(0, 180, 216), width=3)
        # Inner sharp line
        draw.line([pts[i], pts[i+1]], fill=CYAN_LINE, width=1)
        # Print dots
        if i % 3 == 0:
            draw.ellipse([(pts[i][0]-2, pts[i][1]-2), (pts[i][0]+2, pts[i][1]+2)], fill=TEXT_WHITE)

    # P1 X-Axis Labels
    draw.text((c1_x1 + 10, c1_y2 + 6), "Aug 24", fill=TEXT_DIM, font=font_small)
    draw.text((c1_x1 + 160, c1_y2 + 6), "11:30", fill=TEXT_DIM, font=font_small)
    draw.text((c1_x1 + 320, c1_y2 + 6), "13:30", fill=TEXT_DIM, font=font_small)
    draw.text((c1_x2 - 60, c1_y2 + 6), "15:30", fill=TEXT_DIM, font=font_small)

    # P1 Y-Axis Prices
    draw.text((c1_x2 - 45, c1_y1 + 15), f"${avg_price * 1.5:.2f}", fill=TEXT_DIM, font=font_small)
    draw.text((c1_x2 - 45, c1_y1 + 85), f"${avg_price * 1.1:.2f}", fill=TEXT_DIM, font=font_small)
    draw.text((c1_x2 - 45, c1_y1 + 155), f"${avg_price * 0.7:.2f}", fill=TEXT_DIM, font=font_small)
    draw.text((c1_x2 - 45, c1_y2 - 30), f"${avg_price * 0.4:.2f}", fill=TEXT_DIM, font=font_small)

    # 3. RIGHT PANEL: NET PREMIUM
    p2_left = p1_right + P_GAP
    p2_right = p2_left + P_W
    draw.rounded_rectangle([(p2_left, P_TOP), (p2_right, P_BOTTOM)], radius=10, fill=PANEL_BG, outline=BORDER_COLOR, width=1)

    # Panel 2 Header
    draw.text((p2_left + 16, P_TOP + 14), "NET PREMIUM ▾", fill=TEXT_WHITE, font=font_bold)
    draw.rounded_rectangle([(p2_right - 100, P_TOP + 10), (p2_right - 60, P_TOP + 30)], radius=4, fill=(22, 30, 46))
    draw.text((p2_right - 92, P_TOP + 13), "1D ▾", fill=TEXT_MUTED, font=font_small)
    draw.rounded_rectangle([(p2_right - 75, P_TOP + 10), (p2_right - 12, P_TOP + 30)], radius=4, fill=(22, 30, 46))
    draw.text((p2_right - 70, P_TOP + 13), "Single-leg ▾", fill=TEXT_MUTED, font=font_small)

    # Panel 2 Metrics
    net_val_m = round(premium_usd * (0.8 if is_call else -0.8) / 1_000_000.0, 2)
    ncp_m = round(premium_usd * 0.9 / 1_000_000.0, 2)
    npp_k = round(premium_usd * 0.15 / 1_000.0, 1)
    metrics_p2 = f"Vol: {tot_vol:,}   Prem: ${tot_prem/1_000_000:.2f}M   Net: {net_val_m:+.2f}M   NCP: {ncp_m:+.2f}M   NPP: {npp_k:+.1f}K"
    draw.text((p2_left + 16, P_TOP + 40), metrics_p2, fill=TEXT_MUTED, font=font_small)

    # Net Sentiment Bar
    draw.text((p2_left + 16, bar_y - 2), "Net Sentiment", fill=TEXT_DIM, font=font_small)
    draw.rounded_rectangle([(p2_left + 16, ratio_bar_y), (p2_left + 16 + bar_w, ratio_bar_y + 6)], radius=3, fill=(30, 41, 59))
    bear_w = int(bar_w * (bear_pct / 100.0))
    draw.rounded_rectangle([(p2_left + 16, ratio_bar_y), (p2_left + 16 + bear_w, ratio_bar_y + 6)], radius=3, fill=RED_BID)
    draw.rounded_rectangle([(p2_left + 16 + bear_w, ratio_bar_y), (p2_left + 16 + bar_w, ratio_bar_y + 6)], radius=3, fill=GREEN_ASK)

    draw.text((p2_left + 16, ratio_bar_y + 10), f"Bearish {bear_pct}%", fill=RED_BID, font=font_small)
    draw.text((p2_right - 70, ratio_bar_y + 10), f"Bullish {bull_pct}%", fill=GREEN_ASK, font=font_small)

    # Panel 2 Legend Row
    draw.ellipse([(p2_left + 16, leg_y + 2), (p2_left + 22, leg_y + 8)], fill=GREEN_ASK)
    draw.text((p2_left + 26, leg_y), f"Call Bought: ${premium_usd*0.6/1_000_000:.1f}M", fill=TEXT_MUTED, font=font_small)

    draw.ellipse([(p2_left + 160, leg_y + 2), (p2_left + 166, leg_y + 8)], fill=(183, 28, 28))
    draw.text((p2_left + 170, leg_y), f"Call Sold: ${premium_usd*0.2/1_000_000:.1f}M", fill=TEXT_MUTED, font=font_small)

    draw.ellipse([(p2_left + 290, leg_y + 2), (p2_left + 296, leg_y + 8)], fill=RED_BID)
    draw.text((p2_left + 300, leg_y), f"Put Bought: ${premium_usd*0.3/1_000_000:.1f}M", fill=TEXT_MUTED, font=font_small)

    # Chart Box P2
    c2_x1, c2_y1 = p2_left + 16, leg_y + 22
    c2_x2, c2_y2 = p2_right - 16, P_BOTTOM - 26
    draw.rectangle([(c2_x1, c2_y1), (c2_x2, c2_y2)], fill=(10, 14, 22), outline=(22, 30, 44), width=1)

    # Watermark P2
    draw.text((c2_x1 + (c2_x2 - c2_x1)//2 - 120, c2_y1 + (c2_y2 - c2_y1)//2 - 30), "Flowseeker", fill=WATERMARK, font=font_watermark)

    # Grid Lines P2
    for gy in range(c2_y1 + 40, c2_y2, 50):
        draw.line([(c2_x1, gy), (c2_x2, gy)], fill=GRID_COLOR, width=1)
    for gx in range(c2_x1 + 80, c2_x2, 110):
        draw.line([(gx, c2_y1), (gx, c2_y2)], fill=GRID_COLOR, width=1)

    # Center Zero Dotted Line
    zero_y = c2_y1 + (c2_y2 - c2_y1) // 2
    for zx in range(c2_x1, c2_x2, 8):
        draw.line([(zx, zero_y), (zx + 4, zero_y)], fill=(50, 65, 85), width=1)

    # Net Call Flow Curve & Net Put Flow Curve
    net_call_pts = []
    net_put_pts = []
    price_pts = []
    
    call_accum = 0
    put_accum = 0
    price_accum = spot_price

    for i in range(num_pts):
        px = c2_x1 + int((i / (num_pts - 1)) * (c2_x2 - c2_x1 - 40))
        
        # Cumulative Call Curve
        call_accum += rng.uniform(0.1, 1.2) if is_call else rng.uniform(-0.8, 0.4)
        ncy = zero_y - int(call_accum * 6)
        ncy = max(c2_y1 + 25, min(c2_y2 - 25, ncy))
        net_call_pts.append((px, ncy))

        # Cumulative Put Curve
        put_accum += rng.uniform(-0.9, 0.3) if is_call else rng.uniform(0.2, 1.4)
        npy = zero_y - int(put_accum * 5)
        npy = max(c2_y1 + 25, min(c2_y2 - 25, npy))
        net_put_pts.append((px, npy))

        # Price Curve
        price_accum += rng.uniform(-0.4, 0.6) if is_call else rng.uniform(-0.6, 0.3)
        ppy = zero_y - int((price_accum - spot_price) * 15)
        ppy = max(c2_y1 + 20, min(c2_y2 - 20, ppy))
        price_pts.append((px, ppy))

    # Draw Put Curve (Red)
    for i in range(len(net_put_pts) - 1):
        draw.line([net_put_pts[i], net_put_pts[i+1]], fill=(180, 50, 50), width=2)
        draw.line([net_put_pts[i], net_put_pts[i+1]], fill=RED_BID, width=1)

    # Draw Call Curve (Green)
    for i in range(len(net_call_pts) - 1):
        draw.line([net_call_pts[i], net_call_pts[i+1]], fill=(25, 120, 100), width=2)
        draw.line([net_call_pts[i], net_call_pts[i+1]], fill=GREEN_ASK, width=1)

    # Draw Price Trajectory (Cyan)
    for i in range(len(price_pts) - 1):
        draw.line([price_pts[i], price_pts[i+1]], fill=(0, 160, 200), width=2)
        draw.line([price_pts[i], price_pts[i+1]], fill=CYAN_LINE, width=1)

    # P2 X-Axis Labels
    draw.text((c2_x1 + 10, c2_y2 + 6), "Aug 24", fill=TEXT_DIM, font=font_small)
    draw.text((c2_x1 + 160, c2_y2 + 6), "11:30", fill=TEXT_DIM, font=font_small)
    draw.text((c2_x1 + 320, c2_y2 + 6), "13:30", fill=TEXT_DIM, font=font_small)
    draw.text((c2_x2 - 60, c2_y2 + 6), "15:30", fill=TEXT_DIM, font=font_small)

    # P2 Y-Axis Net Premium Values
    draw.text((c2_x1 + 6, c2_y1 + 15), "+$15M", fill=TEXT_DIM, font=font_small)
    draw.text((c2_x1 + 6, zero_y - 6), "$0", fill=TEXT_DIM, font=font_small)
    draw.text((c2_x1 + 6, c2_y2 - 30), "-$10M", fill=TEXT_DIM, font=font_small)

    # P2 Y-Axis Price Values
    draw.text((c2_x2 - 45, c2_y1 + 15), f"${spot_price * 1.04:.2f}", fill=TEXT_DIM, font=font_small)
    draw.text((c2_x2 - 45, zero_y - 6), f"${spot_price:.2f}", fill=TEXT_DIM, font=font_small)
    draw.text((c2_x2 - 45, c2_y2 - 30), f"${spot_price * 0.96:.2f}", fill=TEXT_DIM, font=font_small)

    # Output Saving
    if not output_path:
        out_dir = Path.home() / ".hermes" / "flow_charts"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / f"flowseeker_{ticker}_{strike:.0f}{cp_char}.png")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    im.save(output_path, "PNG", quality=95)
    return output_path


if __name__ == "__main__":
    out = generate_flowseeker_chart(
        ticker="AAPL",
        strike=325.0,
        call_put="C",
        expiration="2026-11-20",
        premium_usd=1_900_000.0,
        dte=88,
        spot_price=310.51,
        spot_change_pct=0.38,
    )
    print(f"Generated Flowseeker chart: {out}")
