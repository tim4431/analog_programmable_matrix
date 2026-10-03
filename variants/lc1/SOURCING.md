# LC1 component cost and sourcing

Checked 2 October 2026. These are supplier catalog observations, **not a new JLCPCB assembly quote, reserved inventory, or an order change**. The existing Revision D order selection has not been replaced.

The original quote supplied in the conversation was $1,295 for SMT components for **two boards**, including $669.41 for ten AD5544 DACs. LC1 replaces those ten parts with 32 DAC7811 and two MCP4728 parts.

| Two-board quantity | Supplier identity | Observed unit price | Extended |
| --- | --- | --- | --- |
| 32 × DAC7811IDGSR | [LCSC C390090](https://www.lcsc.com/product-detail/C390090.html) | $3.7509 at 30+ | $120.03 |
| 2 × MCP4728T-E/UN | [LCSC C478093](https://www.lcsc.com/product-detail/C478093.html) | $2.6369 at 1+ | $5.27 |
| New DAC total | | | **$125.30** |
| Original quoted DAC total | 10 × AD5544BRSZ | | **$669.41** |
| DAC-only reduction | | | **$544.11** |

The DAC reduction alone is approximately 42% of the original quoted SMT component budget. Do not subtract it and call the result a final board price: replacement amplifier/switch prices, attrition quantities, extended-part fees, sourcing charges, PCB fabrication, assembly, hand-fitted parts, shipping and tax remain to be quoted.

Package consolidation does not always save component dollars. Twenty TMUX6136PWR at the observed 10+ price of $5.1557 total $103.11, versus the old quote's $97.93 for forty TMUX6219. Their benefit here is ten fewer packages per board. [LCSC C2673380](https://www.lcsc.com/product-detail/C2673380.html)

## Parts requiring attention before an order

| Part | Identity / status |
| --- | --- |
| DAC7811IDGSR | C390090; catalog displayed 569 pieces. Need 32 plus assembly attrition. |
| MCP4728T-E/UN | C478093; catalog displayed 20,797 pieces. Need 2 plus attrition. Default address must be 0x60. |
| TMUX6136PWR | C2673380; catalog displayed 206 pieces. Need 20 plus attrition. |
| OPA2810IDR | C1849413 identifies the SOIC-8 device, but JLC assembly availability and price are **unconfirmed**. Need 16 plus attrition. TI/DigiKey/Mouser sourcing may be needed. |
| OPA4197IPWR | TI [C2057327](https://www.lcsc.com/product-detail/C2057327.html); catalog displayed **only 1 piece**, insufficient for two boards even before attrition. Need sourcing/replenishment. Do not select a different manufacturer with a similar ordering code. |

Stock can change between catalog access and checkout, and LCSC stock does not guarantee availability in the JLC assembly parts pool. Check each selected part in a fresh JLC quote. A different tape/reel suffix may be acceptable after confirming the exact manufacturer, package, grade and electrical specifications. A different amplifier family needs renewed analysis; it is not a silent substitute.

The original precision 49.9 Ω output resistor quote also has room for purchasing optimization. Preserve 0.1% tolerance, at least 1 W continuous rating, suitable temperature coefficient, and the 2512 footprint. No cheaper exact resistor has been qualified in this variant, so no resistor saving is claimed.

## Primary design references

- [TI DAC7811 datasheet](https://www.ti.com/lit/ds/symlink/dac7811.pdf)
- [TI OPA2810 datasheet](https://www.ti.com/lit/ds/symlink/opa2810.pdf)
- [TI TMUX6136 datasheet](https://www.ti.com/lit/ds/symlink/tmux6136.pdf)
- [TI OPA197/2197/4197 datasheet](https://www.ti.com/lit/ds/symlink/opa197.pdf)
- [Microchip MCP4728 datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/22187E.pdf)
