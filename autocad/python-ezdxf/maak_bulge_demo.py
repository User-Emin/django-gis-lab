#!/usr/bin/env python3
"""Schrijft testdata/bulge-demo.dxf (fictief): een ruimte 6x4 m met een gebogen gevel (bulge 0.5) op laag 92.

De oefenplattegrond heeft geen ruimten met bogen; deze demo maakt het verschil zonder/met bulge zichtbaar.
"""

from pathlib import Path

import ezdxf

uit = Path(__file__).resolve().parent.parent / "testdata/bulge-demo.dxf"
doc = ezdxf.new("R2018", units=4)  # INSUNITS 4 = mm
doc.layers.add("92 Rust- en werkgebieden")
msp = doc.modelspace()
# punten (x, y, bulge); bulge op punt 2 = boog van (6500,500) naar (6500,4500), naar buiten (tegen de klok in)
msp.add_lwpolyline(
    [(500, 500, 0), (6500, 500, 0.5), (6500, 4500, 0), (500, 4500, 0)],
    format="xyb",
    close=True,
    dxfattribs={"layer": "92 Rust- en werkgebieden"},
)
msp.add_text("00.99", dxfattribs={"layer": "92 Rust- en werkgebieden", "insert": (3000, 2500)})
doc.saveas(uit)
print(f"geschreven: {uit}")
