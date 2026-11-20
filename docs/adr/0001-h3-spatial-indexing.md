# ADR 0001: H3 Hexagonal Spatial Indexing vs Rectangular Grid

## Status
Accepted

## Context
GapScout analyzes local commercial saturation and underservice across geographic neighborhoods. Spatial data requires partitioning continuous two-dimensional city coordinates into discrete spatial bins for supply-demand aggregation and boundary visualization.

The primary alternatives evaluated were:
1. **Raw rectangular latitude/longitude bounding grid (Quadtree / GeoHash / standard squares)**.
2. **Uber's H3 Discrete Global Grid System (Hexagonal Hierarchical Spatial Index)**.

## Decision
We chose **Uber H3 (resolution 8, ~460m edge length / 0.74 km² area)** as the fundamental spatial unit for gap intelligence.

## Consequences & Trade-offs
### Advantages:
- **Uniform Adjacency & Equidistant Neighbors:** Unlike square tiles where diagonal neighbors share only a vertex and are $\sqrt{2} \times$ farther away, every adjacent H3 hexagon shares a complete edge and is equidistant from the center ($k=1$ grid ring has 6 identical neighbors). This ensures smooth spatial smoothing and realistic spatial decay without distortion.
- **Isotropic Smoothing:** Hexagons minimize quantization error when computing spatial competitor density, footfall anchors, and boundary transitions.
- **Hierarchical Nesting:** H3 allows seamless aggregation from resolution 8 (micro-neighborhood) to resolution 7 or 6 (borough/city-wide) through simple bitwise index shifts.
- **Compact Index Representation:** H3 indexes are stored as 64-bit integers or 15-character hex strings, enabling ultra-fast database indexing and joining in PostgreSQL.

### Trade-offs & Mitigations:
- **Non-Standard Visualization:** Hexagonal polygons require conversion to GeoJSON for rendering on standard web maps. Mitigated by using `@deck.gl/geo-layers` (`H3HexagonLayer`) and MapLibre GL for client-side GPU-accelerated rendering.
