# Memory Rev C mill (2014)

The 2005 Rev C, re-routed in 2014 for milling the PCB.
It was saved from a newer Eagle, so the file is XML; `fab/` holds its CAM job.

Compared with the 2005 Rev C board (`../rev-c/fusion-export/mem3-c.brd`, compared 2026-10-05):

| | 2005 Rev C | 2014 mill |
|---|---|---|
| Parts, positions, values | 50 parts | identical |
| Connectivity | 92 nets | identical |
| Board outline | 140 × 96 mm | identical |
| Track segments (top / bottom) | 1007 / 623 | 868 / 503 |
| Vias | 165 | 132 |
| Track width | 10 mil | 10 mil |

The circuit is unchanged; only the routing differs, with fewer vias to drill and pin by hand.
Nothing in the tree shows whether it was actually milled.
