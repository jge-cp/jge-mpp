# Import Issues to Revisit

## Color Mismatch (Variant Fallback)

When a lot's fabric style matches a base Multicam FA but the lot is actually for a different variant (e.g., Multicam Black), the color lookup fails because the eval sheet uses variant-specific colors that don't exist under the matched FA's variant.

| Partner | Lot ID | Fabric Style | Issue |
|---------|--------|-------------|-------|
| Brookwood (BKWD) | BKWD-LOT-0060 | NYCO VTX - MCBlack | Matched to base MC FA (BKWD-FA-0074) instead of Black variant. 9 colors not found (Olive 205, Gray 206, Black 207 × 3 samples). |
| Hampton (HMTN) | HMTN-LOT-0026 | 25910L 80% Nylon x 20% Spandex - MC | Eval sheet used MC Black colors (Olive 205, Gray 206, Black 207) but lot matched to MC FA. 9 colors not found. |

## Colors Not Found (Variant Colors Missing from DB)

Some FA evaluation sheets reference variant-specific color names that don't exist in the `VariantColor` table. The evaluations are still created, but those color evaluation rows are skipped.

| Partner | FAs Affected | Variant | Missing Colors |
|---------|-------------|---------|----------------|
| Jinchen (JNCN) | JNCN-FA-0016, 0017, 0020, 0021, 0022, 0025 | Alpine / Tropic | Light Tan 170, Urban Tan 171, Olive 172, Light Coyote 173, Highland 174 |
| Jinchen (JNCN) | JNCN-FA-0030 | Arid | White 124, Light Gray 125, Medium Gray 126 |
| Car-Mel (CRML) | All FAs and all 41 Lots | All variants (Narrow goods) | Narrow color codes use "W" suffix (e.g., Cream 524W, Olive 527W, Black 207W) — not in DB. 0 color evals created for this partner. |

## Unlinked Lots (No Parent FA Found)

Many historic lots could not be linked to a parent FA because:
1. Fabric style strings don't exactly match between FA and Lot workbooks (tabs, extra spaces, suffixes like " - MC -")
2. The parent FA is itself historic with no evaluation data

**Future fix:** Use the "Sheet Name Generated" column to match between FA and Lot workbooks instead of fabric style string matching.

| Partner | Count | Notes |
|---------|-------|-------|
| Jiaxi (JXI) | 86 lots skipped | Mostly NYCO RIP-STOP, 98/2 COTTON/SPANDEX TWILL, 65/35 p/c rip, Cotton Twill, 600D Polyester variants |
| Milliken (MLK) | 15 lots (initial run) | Fixed with suffix stripping; remainder linked on re-run |
| Hampton (HMTN) | 2 lots skipped (rows 29, 32) | Fabric style "520ENS Nylon Spandex" not found — FA workbook has "594ENS" (likely typo in lot sheet) |
