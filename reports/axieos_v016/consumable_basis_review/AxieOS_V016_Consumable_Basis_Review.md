# AxieOS V0.16 — Consolidated consumable sale-basis review

**Decision:** 24 of 24 sale-basis cases remain unresolved. No cost basis, realized profit, or PHP recovery is accepted by this review.

## Scope and findings

- The 24 queued sale hashes each match exactly one saved ACI outbound transfer and one CONSUMABLE/ASSET_SALE accounting row, with the same token ID and quantity.
- The 26 corroborated CocoChoco purchase hashes each match one saved ACI inbound transfer. Those purchases represent 120 Regular (token ID 1) and 29 Premium (token ID 2) gross units.
- The 24 sales represent 42 Regular and 27 Premium gross units. Every sale has both a prior corroborated paid inflow and another prior inbound transfer of the same token ID.
- The other inbound transfers have mixed or unverified acquisition routes. Their basis cannot be assumed to be zero. The 2026-03-04 to 2026-05-12 export interval and opening inventory remain unresolved.
- Gross prior inflows below are **not available balances**: sales, burns, transfers, and other outflows can deplete inventory. A sale hash cannot uniquely identify which fungible units were disposed. A lot policy plus supported opening/provenance evidence is required before accepting basis.

## All 24 sale cases

| Sale UTC | Token ID | Units out | Prior corroborated paid units in (gross) | Prior other units in (gross) | Sale hash |
| --- | ---: | ---: | ---: | ---: | --- |
| 2026-07-19 08:08:51 | 2 | 1 | 1 | 99 | `0x5a46c7058a14ee6444b874606f7a4969511d71e53f2a5149849e79afc801ba43` |
| 2026-07-20 03:56:37 | 2 | 1 | 2 | 99 | `0x2bb83d5b39a54268fe12cde98cfb00eadca9e6c305d023514fcbda59b5ff5e87` |
| 2026-07-22 04:31:49 | 2 | 4 | 6 | 99 | `0xdc5131f5a7f07ef6e6d3ccfae53933eb3f436a4ff142471dd7176d699b799855` |
| 2026-07-24 03:47:47 | 2 | 1 | 7 | 99 | `0x42ac0a3ba7148e49c815a66da54f59310a945778ac343e323356e787c4dc3005` |
| 2026-07-26 04:24:47 | 2 | 1 | 8 | 100 | `0x9234deddf489357df0003aba68cf0e341247e9f19fb1819e6e815b45c8b41f0b` |
| 2026-07-30 03:28:57 | 2 | 1 | 9 | 101 | `0x3d271c68c5fd9cfbb265fded24af52ed2e82dcd31f2e8e063435b7749f750202` |
| 2026-07-31 04:20:15 | 2 | 1 | 10 | 101 | `0x9bf013e552fd91fcbcaffe6dc4fbeb950f28563b8e5f3ea596189749d0836829` |
| 2026-08-03 03:46:11 | 2 | 1 | 11 | 102 | `0xa79e4179e2519ec6a890597d90dd896e1b53fc0a6c90985ac03035f827867348` |
| 2026-08-04 03:17:57 | 2 | 1 | 12 | 102 | `0xff12d99d5af68dd2ea7a62b04c071e950e4cbeb1eb943571d21a09996f7b99a0` |
| 2026-08-06 04:00:17 | 2 | 3 | 15 | 102 | `0x620ddba8b33aa026d05acd096dbb7fc2ae13db5c2b9d778fd488cec39191ad56` |
| 2026-08-06 04:05:23 | 2 | 1 | 16 | 102 | `0x2af8cd12d10193dc5105c349b6800245d892ebca3173e2ecee0c38d208a49b92` |
| 2026-08-07 03:34:21 | 2 | 1 | 17 | 103 | `0x52374a870640737caf37175b390bc45008e093c301ca67c05b6df112ecc08706` |
| 2026-08-08 03:44:01 | 1 | 1 | 60 | 888 | `0xf3004531b438079d2bd27ea66feba664d3a30abdfec06091976a801bace1f6b9` |
| 2026-08-08 03:44:13 | 1 | 1 | 60 | 888 | `0x84d12abc1f402b223649f763d4f4baa2c74e3d61fcfa7d047fe8fe4b74b2683a` |
| 2026-08-08 18:22:15 | 2 | 1 | 18 | 103 | `0xdf2147ea4ea55d8386c68ce2a939244eb1f28d81d91b2bc947469adfcd139174` |
| 2026-08-12 06:28:29 | 2 | 2 | 21 | 106 | `0x36e3b6892b8e8e1891b8d73e7e1a8c1fa740b364da82dee4c2fc74232edd5b8d` |
| 2026-08-14 03:33:41 | 2 | 1 | 22 | 107 | `0x0d313cdd8479bc8f7d1f35ec7edb8b54e5aeffd719bff21227c54e628f090c1c` |
| 2026-08-16 04:56:21 | 2 | 1 | 23 | 107 | `0x56f2f3ead16b190c504e7a0ab71c14a3ff99656cd6c1dd5bf7467027d232eab9` |
| 2026-08-20 04:20:05 | 2 | 4 | 29 | 108 | `0x0101cff8969f4800cd10b0241c388257cb7485b1337971a76c3cb465880d9350` |
| 2026-08-20 04:21:41 | 2 | 1 | 29 | 108 | `0xce120597e92cbaef6526b3e32645c585afadab5a8bae374d01ed7f9d6a54d617` |
| 2026-08-21 03:31:03 | 1 | 10 | 105 | 957 | `0x0c47b253d0ec041ce91f6b115505c0c66eb21f596fc23372d72f16f2bab0a0cf` |
| 2026-08-21 03:31:05 | 1 | 15 | 105 | 957 | `0x6c3814285cebcf084f81b6c3c0dc90f3e4fb1eaad9da1342899d0e14f95dd0d9` |
| 2026-08-22 11:07:57 | 1 | 8 | 120 | 957 | `0xae61961731e2ee63da09e6131f9fff60f6de89976d9b52e1155f8e0075210773` |
| 2026-08-22 11:10:11 | 1 | 7 | 120 | 957 | `0x478e077dc792df75dc0c8ed94e17ee4012ef129318a3e1b2f1f031e0cf7ada8e` |

## Release boundary

This resolves the review **classification** for the 24 cases: their sale identity and token quantity are supported, while paid lot allocation and realized profit remain **UNKNOWN**. Keep them out of accepted P&L. The 26 closed Axie trade pairs are a separate cohort and must not be merged into these 24 consumable sales. The V0.16 operational dashboard may remain released with scoped observed wallet flows. Unified Finance stays **HOLD**; Checkpoint 96 stays **OPEN**.

No database opened; no database writes; no network calls. This report is an offline crosswalk of saved JSON evidence.

## Source integrity

- BM: `AxieOS_V014_Task136BM_Finance_Resolution_Batch_20261104T053256_758175Z_506d83.json` — SHA-256 `44125805b6f98992e33588c7dfbb3fe42bff2fd9b3a2d735c557bef810caf0e9`
- F: `AxieOS_V014_Task136F_Consumable_Transfer_Evidence_20261030T081304_450317Z_6952a1.json` — SHA-256 `dfaebe6dc3476d04c98183299cd8b7ebdce3b7eb8a28414e4d80da8471df56e8`
- BO: `AxieOS_V014_Task136BO_Consumable_Purchase_History_20261104T080009_820432Z_6b4ff0.json` — SHA-256 `83426a88d1081b744d95f4999fc8af1eb980b811d761afbf9761512155001772`
