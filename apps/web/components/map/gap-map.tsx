"use client";

import React, {
  useEffect,
  useRef,
  useState,
  useCallback,
  useImperativeHandle,
  forwardRef,
} from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

// Configure MapLibre web worker location for Next.js / Turbopack
if (typeof window !== "undefined") {
  maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
}
import { MapboxOverlay } from "@deck.gl/mapbox";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import { cellToLatLng, cellToChildren, cellToParent } from "h3-js";
import { HexMetricOut, PlaceOut } from "@/lib/types";
import { MetricType, getMetricColor } from "@/lib/color-scale";

export interface GapMapRef {
  flyToHex: (h3Index: string) => void;
  getCanvasDataURL: () => string | null;
  setBasemapStyle: (styleUrl: string) => void;
  setZoomLevel: (zoom: number) => void;
}

interface GapMapProps {
  hexes: HexMetricOut[];
  places?: PlaceOut[];
  activeMetric: MetricType;
  opacity: number;
  showMarkers: boolean;
  selectedHex: HexMetricOut | null;
  onSelectHex: (hex: HexMetricOut) => void;
  basemapStyle?: string;
  resolution?: number;
  onResolutionChange?: (res: number) => void;
}

export const GapMap = forwardRef<GapMapRef, GapMapProps>(function GapMap(
  {
    hexes,
    places = [],
    activeMetric,
    opacity,
    showMarkers,
    selectedHex,
    onSelectHex,
    basemapStyle = "https://tiles.openfreemap.org/styles/dark",
    resolution = 8,
    onResolutionChange,
  },
  ref,
) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);

  const [hoverInfo, setHoverInfo] = useState<{
    object: HexMetricOut | null;
    x: number;
    y: number;
  } | null>(null);

  // Progressive subdivision and aggregation based on H3 resolution
  const displayHexes = React.useMemo<HexMetricOut[]>(() => {
    if (!hexes || hexes.length === 0) return [];

    if (resolution === 9) {
      // Subdivide each hex into 7 child Res-9 sub-hexes (Progressive Street-level View)
      const subHexes: HexMetricOut[] = [];
      for (const h of hexes) {
        try {
          const children = cellToChildren(h.h3_index, 9);
          for (let i = 0; i < children.length; i++) {
            const child = children[i];
            if (!child) continue;
            subHexes.push({
              ...h,
              id: `${h.id || h.h3_index}-c${i}`,
              h3_index: child,
              resolution: 9,
            });
          }
        } catch {
          subHexes.push(h);
        }
      }
      return subHexes;
    }

    if (resolution === 7) {
      // Coarser City-level view: group hexes into parent Res-7 cells
      const parentMap = new Map<string, HexMetricOut>();
      for (const h of hexes) {
        try {
          const parentIdx = cellToParent(h.h3_index, 7);
          if (!parentMap.has(parentIdx)) {
            parentMap.set(parentIdx, {
              ...h,
              id: `p7-${parentIdx}`,
              h3_index: parentIdx,
              resolution: 7,
            });
          }
        } catch {
          parentMap.set(h.h3_index, h);
        }
      }
      return Array.from(parentMap.values());
    }

    // Default: Neighborhood Res 8
    return hexes;
  }, [hexes, resolution]);

  // Center calculation from hexes
  const defaultCenter = React.useMemo<[number, number]>(() => {
    if (hexes.length > 0 && hexes[0]?.h3_index) {
      try {
        const [lat, lon] = cellToLatLng(hexes[0].h3_index);
        return [lon, lat];
      } catch {
        return [77.63, 12.97]; // Bangalore default
      }
    }
    return [77.63, 12.97];
  }, [hexes]);

  // Expose flyTo, canvas capture, style switch, and zoom to parent via ref
  useImperativeHandle(ref, () => ({
    flyToHex: (h3Index: string) => {
      try {
        const [lat, lon] = cellToLatLng(h3Index);
        mapRef.current?.flyTo({
          center: [lon, lat],
          zoom: resolution === 9 ? 15.2 : 14.2,
          speed: 1.4,
          essential: true,
        });
      } catch {
        // Fallback
      }
    },
    getCanvasDataURL: () => {
      if (!mapRef.current) return null;
      try {
        return mapRef.current.getCanvas().toDataURL("image/png");
      } catch {
        return null;
      }
    },
    setBasemapStyle: (styleUrl: string) => {
      if (mapRef.current) {
        mapRef.current.setStyle(styleUrl);
      }
    },
    setZoomLevel: (zoom: number) => {
      if (mapRef.current) {
        mapRef.current.zoomTo(zoom, { duration: 800 });
      }
    },
  }));

  // Handle deck.gl layer updates
  const updateDeckLayers = useCallback(() => {
    if (!overlayRef.current) return;

    const layers = [];

    // 1. H3 Hexagons Layer (using displayHexes for progressive subdivision)
    if (displayHexes.length > 0) {
      layers.push(
        new H3HexagonLayer<HexMetricOut>({
          id: "h3-gap-layer",
          data: displayHexes,
          pickable: true,
          wireframe: false,
          filled: true,
          extruded: false,
          getHexagon: (d) => d.h3_index,
          getFillColor: (d) => getMetricColor(d, activeMetric, opacity),
          getLineColor: (d) =>
            selectedHex?.h3_index === d.h3_index ? [255, 255, 255, 255] : [255, 255, 255, 40],
          lineWidthMinPixels: selectedHex ? 2.5 : resolution === 9 ? 0.75 : 1,
          onHover: (info) => {
            if (info.object) {
              setHoverInfo({
                object: info.object as HexMetricOut,
                x: info.x,
                y: info.y,
              });
            } else {
              setHoverInfo(null);
            }
          },
          onClick: (info) => {
            if (info.object) {
              onSelectHex(info.object as HexMetricOut);
            }
          },
          updateTriggers: {
            getFillColor: [activeMetric, opacity, resolution],
            getLineColor: [selectedHex?.h3_index],
            lineWidthMinPixels: [selectedHex?.h3_index, resolution],
          },
        }),
      );
    }

    // 2. Business Markers & Street-Level Rating Pills
    const shouldShowPins = showMarkers || resolution === 9;
    if (shouldShowPins && places.length > 0) {
      const validPlaces = places.filter((p) => p.longitude !== null && p.latitude !== null);

      // Pin dot marker
      layers.push(
        new ScatterplotLayer<PlaceOut>({
          id: "places-scatter-layer",
          data: validPlaces,
          pickable: true,
          opacity: 0.95,
          stroked: true,
          filled: true,
          radiusScale: 1,
          radiusMinPixels: resolution === 9 ? 5 : 4,
          radiusMaxPixels: 12,
          lineWidthMinPixels: 1.5,
          getPosition: (d) => [d.longitude!, d.latitude!],
          getFillColor: [244, 63, 94, 230], // Coral / Rose
          getLineColor: [255, 255, 255, 230],
        }),
      );

      // Star rating badge pills (Stitch V1 / V2 street pins)
      const placesWithRating = validPlaces.filter(
        (p) => p.rating !== null && p.rating !== undefined,
      );
      if (placesWithRating.length > 0) {
        layers.push(
          new TextLayer<PlaceOut>({
            id: "places-rating-pill-layer",
            data: placesWithRating,
            pickable: false,
            getPosition: (d) => [d.longitude!, d.latitude!],
            getText: (d) => `★ ${d.rating?.toFixed(1)}`,
            getSize: resolution === 9 ? 11 : 9.5,
            getColor: [255, 255, 255, 255],
            getBackgroundColor: [15, 23, 42, 230],
            background: true,
            backgroundPadding: [4, 2, 4, 2],
            fontFamily: "JetBrains Mono, monospace",
            fontWeight: 600,
            getPixelOffset: [0, -14],
            billboard: true,
          }),
        );
      }
    }

    overlayRef.current.setProps({ layers });
  }, [
    displayHexes,
    places,
    activeMetric,
    opacity,
    showMarkers,
    resolution,
    selectedHex,
    onSelectHex,
  ]);

  // Handle basemap style switch
  useEffect(() => {
    if (mapRef.current && basemapStyle) {
      mapRef.current.setStyle(basemapStyle);
    }
  }, [basemapStyle]);

  // Initialize MapLibre GL
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: basemapStyle,
      center: defaultCenter,
      zoom: 12.8,
      canvasContextAttributes: { preserveDrawingBuffer: true }, // Required for PNG canvas export
      attributionControl: false,
    });

    map.addControl(
      new maplibregl.AttributionControl({
        compact: true,
        customAttribution: "OpenFreeMap | OpenStreetMap",
      }),
      "bottom-right",
    );

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");

    const overlay = new MapboxOverlay({
      layers: [],
    });

    map.addControl(overlay as unknown as maplibregl.IControl);
    overlayRef.current = overlay;
    mapRef.current = map;

    map.on("load", () => {
      updateDeckLayers();
    });

    map.on("styledata", () => {
      updateDeckLayers();
    });

    // Progressive zoom-in subdivision listener
    const handleZoomEnd = () => {
      if (!mapRef.current || !onResolutionChange) return;
      const currentZoom = mapRef.current.getZoom();
      if (currentZoom >= 14.5 && resolution !== 9) {
        onResolutionChange(9);
      } else if (currentZoom < 12.0 && resolution !== 7) {
        onResolutionChange(7);
      } else if (currentZoom >= 12.0 && currentZoom < 14.5 && resolution !== 8) {
        onResolutionChange(8);
      }
    };

    map.on("zoomend", handleZoomEnd);

    return () => {
      overlay.finalize();
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
    };
  }, [defaultCenter, updateDeckLayers, basemapStyle, onResolutionChange, resolution]);

  // Update deck layers when state changes
  useEffect(() => {
    updateDeckLayers();
  }, [updateDeckLayers]);

  return (
    <div className="relative w-full h-full min-h-[500px]">
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Floating Hover Tooltip */}
      {hoverInfo && hoverInfo.object && (
        <div
          className="absolute z-30 pointer-events-none transform -translate-x-1/2 -translate-y-full mb-3"
          style={{ left: hoverInfo.x, top: hoverInfo.y }}
        >
          <div className="glass-panel bg-white/95 dark:bg-slate-950/95 border border-slate-200/90 dark:border-slate-700/80 rounded-xl px-3 py-2 text-xs shadow-2xl text-slate-900 dark:text-white font-mono space-y-1">
            <div className="flex items-center justify-between gap-3 text-[11px] text-slate-500 dark:text-slate-400">
              <span>H3 Hex</span>
              <span className="text-slate-700 dark:text-slate-200 font-semibold">
                {hoverInfo.object.h3_index.slice(0, 10)}...
              </span>
            </div>
            <div className="flex items-center justify-between gap-4 font-bold">
              <span>Opportunity Score</span>
              <span className="text-emerald-600 dark:text-emerald-400 tabular-nums">
                {Math.round(hoverInfo.object.opportunity_score ?? 0)}/100
              </span>
            </div>
            <div className="flex items-center justify-between gap-4 text-[11px] text-slate-600 dark:text-slate-300">
              <span>Competitors</span>
              <span className="text-slate-900 dark:text-slate-100 tabular-nums font-semibold">
                {hoverInfo.object.supply_count} businesses
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});
