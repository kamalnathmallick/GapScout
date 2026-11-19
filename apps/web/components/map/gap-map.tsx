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
}

interface GapMapProps {
  hexes: HexMetricOut[];
  places?: PlaceOut[];
  activeMetric: MetricType;
  opacity: number;
  showMarkers: boolean;
  selectedHex: HexMetricOut | null;
  onSelectHex: (hex: HexMetricOut) => void;
}

export const GapMap = forwardRef<GapMapRef, GapMapProps>(function GapMap(
  { hexes, places = [], activeMetric, opacity, showMarkers, selectedHex, onSelectHex },
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
        return [77.63, 12.97]; // Indiranagar default
      }
    }
    return [77.63, 12.97];
  }, [hexes]);

  // Expose flyTo and canvas capture to parent via ref
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
          lineWidthMinPixels: selectedHex ? 2 : 1,
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
          lineWidthMinPixels: 1,
          getPosition: (d) => [d.longitude!, d.latitude!],
          getFillColor: [244, 63, 94, 220], // Coral / Rose
          getLineColor: [255, 255, 255, 200],
        }),
      );
    }

    overlayRef.current.setProps({ layers });
  }, [hexes, places, activeMetric, opacity, showMarkers, selectedHex, onSelectHex]);

  // Initialize MapLibre GL
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: "https://tiles.openfreemap.org/styles/liberty",
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

    return () => {
      overlay.finalize();
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
    };
  }, [defaultCenter, updateDeckLayers]);

  // Update deck layers when state changes
  useEffect(() => {
    updateDeckLayers();
  }, [updateDeckLayers]);

  return (
    <div className="relative w-full h-full min-h-[600px] overflow-hidden bg-gray-950">
      <div
        ref={mapContainerRef}
        data-testid="maplibre-container"
        className="w-full h-full absolute inset-0"
      />

      {/* Hover Tooltip */}
      {hoverInfo && hoverInfo.object && (
        <div
          data-testid="hex-tooltip"
          className="absolute z-40 pointer-events-none p-3 rounded-xl bg-gray-950/95 border border-gray-800 shadow-2xl text-xs text-white max-w-xs backdrop-blur-sm -translate-x-1/2 -translate-y-full mb-3"
          style={{
            left: `${hoverInfo.x}px`,
            top: `${hoverInfo.y}px`,
          }}
        >
          <div className="flex items-center justify-between gap-3 mb-1.5 pb-1 border-b border-gray-800">
            <span className="font-mono text-[10px] text-gray-400">
              {hoverInfo.object.h3_index.slice(0, 10)}...
            </span>
            <span className="font-bold text-emerald-400">
              Score: {Math.round(hoverInfo.object.opportunity_score ?? 0)}/100
            </span>
          </div>

          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-gray-300">
            <div>
              <span className="text-gray-500">Supply:</span>{" "}
              <strong>{hoverInfo.object.supply_count}</strong>
            </div>
            <div>
              <span className="text-gray-500">Density:</span>{" "}
              <strong>
                {hoverInfo.object.density_per_km2
                  ? hoverInfo.object.density_per_km2.toFixed(1)
                  : "0"}
                /km²
              </strong>
            </div>
            <div>
              <span className="text-gray-500">Avg Rating:</span>{" "}
              <strong>
                {hoverInfo.object.avg_rating ? `${hoverInfo.object.avg_rating.toFixed(1)}★` : "N/A"}
              </strong>
            </div>
            <div>
              <span className="text-gray-500">Demand:</span>{" "}
              <strong>
                {hoverInfo.object.demand_proxy ? Math.round(hoverInfo.object.demand_proxy) : "0"}
              </strong>
            </div>
          </div>

          {hoverInfo.object.explanation?.top_reasons?.[0] && (
            <p className="mt-2 text-[10px] text-indigo-300 italic border-t border-gray-800/80 pt-1">
              &quot;{hoverInfo.object.explanation.top_reasons[0]}&quot;
            </p>
          )}
        </div>
      )}
    </div>
  );
});
