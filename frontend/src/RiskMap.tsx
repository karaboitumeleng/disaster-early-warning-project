import React, { useState } from 'react';

// Interface for risk data points across South Africa
export interface RiskLocation {
  id: string;
  name: string;
  province: string;
  riskLevel: 'High' | 'Medium' | 'Low';
  score: number;
  xPercent: number; 
  yPercent: number;
  details?: string;
}

// Interface for KPI summary items
export interface KpiCardData {
  title: string;
  value: string | number;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  subtitle: string;
}

// Sample risk data for South African provinces/cities
const DEFAULT_RISK_DATA: RiskLocation[] = [
  { id: '1', name: 'Johannesburg / Pretoria', province: 'Gauteng', riskLevel: 'High', score: 85, xPercent: 72, yPercent: 33, details: 'High population density & elevated fraud risks.' },
  { id: '2', name: 'Cape Town', province: 'Western Cape', riskLevel: 'Medium', score: 58, xPercent: 23, yPercent: 82, details: 'Moderate risk profile with localized activity.' },
  { id: '3', name: 'Durban', province: 'KwaZulu-Natal', riskLevel: 'High', score: 78, xPercent: 82, yPercent: 57, details: 'Elevated supply-chain and logistical risk score.' },
  { id: '4', name: 'Kimberley', province: 'Northern Cape', riskLevel: 'Low', score: 25, xPercent: 44, yPercent: 50, details: 'Low risk footprint and stable activity metrics.' },
  { id: '5', name: 'Gqeberha (PE)', province: 'Eastern Cape', riskLevel: 'Medium', score: 48, xPercent: 60, yPercent: 82, details: 'Average risk rating across regional nodes.' },
  { id: '6', name: 'Polokwane', province: 'Limpopo', riskLevel: 'Medium', score: 52, xPercent: 74, yPercent: 18, details: 'Cross-border transport route surveillance.' },
  { id: '7', name: 'Bloemfontein', province: 'Free State', riskLevel: 'Low', score: 32, xPercent: 57, yPercent: 52, details: 'Central hub with low anomaly counts.' },
];

// Sample KPI metrics calculated across regional data
const DEFAULT_KPI_DATA: KpiCardData[] = [
  {
    title: 'Average Risk Score',
    value: '54 / 100',
    change: '-3.2%',
    trend: 'down',
    subtitle: 'Moderate national exposure'
  },
  {
    title: 'High Risk Zones',
    value: '2 Regions',
    change: 'Gauteng & KZN',
    trend: 'neutral',
    subtitle: 'Requires priority audit'
  },
  {
    title: 'Active Monitored Nodes',
    value: '7 Cities',
    change: '100% Operational',
    trend: 'up',
    subtitle: 'Across 7 provinces'
  },
  {
    title: 'Assessed Entities',
    value: '1,420',
    change: '+14.8%',
    trend: 'up',
    subtitle: 'Active micro-enterprises'
  }
];

interface RiskMapProps {
  mapImageUrl?: string;
  locations?: RiskLocation[];
  kpiData?: KpiCardData[];
}

export const RiskMap: React.FC<RiskMapProps> = ({
  mapImageUrl = "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcRWP0KHG2Y7Q3ewGm-F3pxpU5vbe3f_Dv_jlPUtz6gd7Pn1xMahX3A9zGkGZ--P3cab8HYodmY9FmP8r_w",
  locations = DEFAULT_RISK_DATA,
  kpiData = DEFAULT_KPI_DATA
}) => {
  const [selectedLocation, setSelectedLocation] = useState<RiskLocation | null>(null);

  const getBadgeColor = (level: RiskLocation['riskLevel']) => {
    switch (level) {
      case 'High': return 'bg-red-500 text-white border-red-700';
      case 'Medium': return 'bg-amber-500 text-white border-amber-700';
      case 'Low': return 'bg-emerald-500 text-white border-emerald-700';
    }
  };

  const getMarkerPing = (level: RiskLocation['riskLevel']) => {
    switch (level) {
      case 'High': return 'bg-red-400';
      case 'Medium': return 'bg-amber-400';
      case 'Low': return 'bg-emerald-400';
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4 bg-slate-900 text-slate-100 rounded-xl shadow-xl border border-slate-800 space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white">South Africa Risk Overview</h2>
          <p className="text-xs text-slate-400">Offline static map & key performance metrics</p>
        </div>
        <div className="flex gap-4 text-xs">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-red-500"></span> High</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> Medium</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Low</span>
        </div>
      </div>

      {/* KPI Summary Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {kpiData.map((kpi, idx) => (
          <div key={idx} className="bg-slate-800/80 border border-slate-700/80 p-3 rounded-lg flex flex-col justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">{kpi.title}</span>
            <div className="my-1 flex items-baseline justify-between">
              <span className="text-lg font-extrabold text-white">{kpi.value}</span>
              {kpi.change && (
                <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                  kpi.trend === 'up' ? 'text-emerald-400 bg-emerald-950/60' :
                  kpi.trend === 'down' ? 'text-emerald-400 bg-emerald-950/60' :
                  'text-slate-300 bg-slate-700/50'
                }`}>
                  {kpi.change}
                </span>
              )}
            </div>
            <span className="text-[10px] text-slate-400">{kpi.subtitle}</span>
          </div>
        ))}
      </div>

      {/* Map Container */}
      <div className="relative w-full overflow-hidden rounded-lg bg-slate-950 flex items-center justify-center min-h-[400px]">
        {/* Map Image */}
        <img
          src={mapImageUrl}
          alt="Map of South Africa"
          className="w-full h-auto object-contain max-h-[600px] select-none opacity-90"
        />

        {/* Overlay Markers */}
        {locations.map((loc) => (
          <div
            key={loc.id}
            className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer group z-10"
            style={{ left: `${loc.xPercent}%`, top: `${loc.yPercent}%` }}
            onClick={() => setSelectedLocation(loc)}
          >
            {/* Pulsing indicator */}
            <span className={`absolute -inset-1 rounded-full animate-ping opacity-75 ${getMarkerPing(loc.riskLevel)}`}></span>
            
            {/* Marker Badge */}
            <button 
              className={`relative flex items-center justify-center px-2 py-0.5 rounded-full text-[10px] font-extrabold border shadow-lg transition-transform group-hover:scale-125 ${getBadgeColor(loc.riskLevel)}`}
            >
              {loc.score}
            </button>

            {/* Hover Tooltip */}
            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:flex flex-col items-center z-30 pointer-events-none">
              <div className="bg-slate-800 text-white text-xs rounded py-1 px-2.5 whitespace-nowrap border border-slate-700 shadow-xl">
                <p className="font-semibold">{loc.name}</p>
                <p className="text-[10px] text-slate-300">Risk Score: {loc.score}/100</p>
              </div>
              <div className="w-2 h-2 bg-slate-800 rotate-45 -mt-1 border-r border-b border-slate-700"></div>
            </div>
          </div>
        ))}
      </div>

      {/* Detail Card for Selected Location */}
      {selectedLocation && (
        <div className="p-4 rounded-lg bg-slate-800 border border-slate-700 flex justify-between items-start animate-fadeIn">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-lg text-white">{selectedLocation.name}</h3>
              <span className={`text-xs px-2 py-0.5 rounded font-semibold ${getBadgeColor(selectedLocation.riskLevel)}`}>
                {selectedLocation.riskLevel} Risk ({selectedLocation.score}/100)
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{selectedLocation.province} Province</p>
            <p className="text-sm text-slate-200 mt-2">{selectedLocation.details}</p>
          </div>
          <button
            onClick={() => setSelectedLocation(null)}
            className="text-slate-400 hover:text-white text-sm font-bold px-2 py-1"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
};

export default RiskMap;