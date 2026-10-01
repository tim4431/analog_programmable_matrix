# Initial assembly request

Requested quantity: **2 assembled boards**, top-side SMT, using PCB D / enclosure M3. Bare-board production quantity and any spare boards are to be selected in the quote. No order has been created, submitted, or paid.

The JLCPCB browser tab could not be operated because this session did not expose the required browser-control tool. The Gerber, BOM and placement files are prepared in [`output/jlcpcb_rev_d`](../output/jlcpcb_rev_d). This file records preparation status, not a JLCPCB quote or inventory reservation.

## Remaining selections

- Match the 24 BOM rows with blank LCSC codes. The eight IC types and the passive specifications must retain their specified package, tolerance, voltage and power ratings.
- Confirm availability for two boards plus JLCPCB's assembly attrition allowance. LCSC retail stock and cached public pages do not establish JLCPCB assembly stock.
- Review vendor library rotations against `PIN1_ORIENTATION_REFERENCE.csv` and `assembly_front.svg`.
- Obtain CAM acceptance for the via-in-pad fill/cap requirements before releasing the order.
- Fit the listed manual items, regulator heatsinks/insulation, Pico sockets, and enclosure hardware separately.

## Supply risks and alternatives to check

| Part | Needed for 2 boards, before attrition | Finding / next action |
| --- | ---: | --- |
| OPA810ID | 32 | The reel version OPA810IDR is listed as LCSC C1852077, but the public listing reports out of stock. Check JLCPCB sourcing or consignment for the same part. |
| ADA4899-1YRDZ | 32 | Public listings give inconsistent tube stock. ADA4899-1YRDZ-R7 / C654316 is a same-package reel option to check; the ADI ordering guide identifies the same RD-8-1 package. |
| AD5544BRSZ | 10 | C649815 is an identity match; confirm JLCPCB stock. AD5544BRSZ-REEL7 / C649816 is a sourcing candidate, subject to package and stock confirmation. |
| THS3091DDAR | 8 | C181226 identifies the required PowerPAD package. Do not substitute THS3091DR, which lacks that exposed pad. |

No functional circuit substitutions have been made. Prefer the same device in equivalent packing when available. A different amplifier or multiplying DAC requires electrical and stability review before changing the assembly BOM.

Public sources checked during preparation (2026-10-01; some search snapshots are older): [OPA810IDR listing](https://www.lcsc.com/product-image/C1852077.html), [ADA4899 tube listing](https://www.lcsc.com/product-image/C654315.html), [ADA4899 reel listing](https://www.lcsc.com/product-detail/operational-amplifier_analog-devices-ada4899-1yrdz-r7_C654316.html), [ADI ordering guide](https://www.analog.com/media/en/technical-documentation/data-sheets/ADA4899-1.pdf), [AD5544 reel listing](https://www.lcsc.com/product-detail/C649816.html), [THS3091 listing](https://www.lcsc.com/product-image/C181226.html?whichImg=0).
