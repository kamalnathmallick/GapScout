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
import { MapboxOverlay } from "@deck.gl/mapbox";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { ScatterplotLayer } from "@deck.gl/layers";
import { cellToLatLng } from "h3-js";
import { HexMetricOut, PlaceOut } from "@/lib/types";
import { MetricType, getMetricColor } from "@/lib/color-scale";

export interface GapMapRef {
  flyToHex: (h3Index: string) => void;
  getCanvasDataURL: () => string | null;
  setBasemapStyle: (styleUrl: string) => void;
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

  // Expose flyTo, canvas capture, and style switch to parent via ref
  useImperativeHandle(ref, () => ({
    flyToHex: (h3Index: string) => {
      try {
        const [lat, lon] = cellToLatLng(h3Index);
        mapRef.current?.flyTo({
          center: [lon, lat],
          zoom: 14.5,
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
  }));

  // Handle deck.gl layer updates
  const updateDeckLayers = useCallback(() => {
    if (!overlayRef.current) return;

    const layers = [];

    // 1. H3 Hexagons Layer
    if (hexes.length > 0) {
      layers.push(
        new H3HexagonLayer<HexMetricOut>({
          id: "h3-gap-layer",
          data: hexes,
          pickable: true,
          wireframe: false,
          filled: true,
          extruded: false,
          getHexagon: (d) => d.h3_index,
          getFillColor: (d) => getMetricColor(d, activeMetric, opacity),
          getLineColor: (d) =>
            selectedHex?.h3_index === d.h3_index ? [255, 255, 255, 255] : [255, 255, 255, 40],
          lineWidthMinPixels: selectedHex ? 2.5 : 1,
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
            getFillColor: [activeMetric, opacity],
            getLineColor: [selectedHex?.h3_index],
            lineWidthMinPixels: [selectedHex?.h3_index],
          },
        }),
      );
    }

    // 2. Business Markers Layer
    if (showMarkers && places.length > 0) {
      const validPlaces = places.filter((p) => p.longitude !== null && p.latitude !== null);
      layers.push(
        new ScatterplotLayer<PlaceOut>({
          id: "places-scatter-layer",
          data: validPlaces,
          pickable: true,
          opacity: 0.9,
          stroked: true,
          filled: true,
          radiusScale: 1,
          radiusMinPixels: 4,
          radiusMaxPixels: 10,
          lineWidthMinPixels: 1.5,
          getPosition: (d) => [d.longitude!, d.latitude!],
          getFillColor: [244, 63, 94, 220], // Coral / Rose
          getLineColor: [255, 255, 255, 220],
        }),
      );
    }

    overlayRef.current.setProps({ layers });
  }, [hexes, places, activeMetric, opacity, showMarkers, selectedHex, onSelectHex]);

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

    return () => {
      overlay.finalize();
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
    };
  }, [defaultCenter, updateDeckLayers, basemapStyle]);

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
          <div className="bg-slate-950/95 backdrop-blur-md border border-slate-700/80 rounded-xl px-3 py-2 text-xs shadow-2xl text-white font-mono space-y-1">
            <div className="flex items-center justify-between gap-3 text-[11px] text-slate-400">
              <span>H3 Hex</span>
              <span className="text-slate-200">{hoverInfo.object.h3_index.slice(0, 10)}...</span>
            </div>
            <div className="flex items-center justify-between gap-4 font-bold">
              <span>Opportunity Score</span>
              <span className="text-emerald-400 tabular-nums">
                {Math.round(hoverInfo.object.opportunity_score ?? 0)}/100
              </span>
            </div>
            <div className="flex items-center justify-between gap-4 text-[11px] text-slate-300">
              <span>Competitors</span>
              <span className="text-slate-100 tabular-nums">
                {hoverInfo.object.supply_count} businesses
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});
