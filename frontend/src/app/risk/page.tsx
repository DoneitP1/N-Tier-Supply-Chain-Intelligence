"use client";

import React, { useState, useEffect } from 'react';
import { AlertTriangle, Activity, Database, ShieldAlert, Loader2, ArrowRight } from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import api from '@/lib/api';
import { cn } from '@/lib/utils';

interface RiskScenario {
  supplier_name: string;
  duration_days: number;
  severity: 'low' | 'medium' | 'high';
}

interface RiskResult {
  cascading_impact_depth: number;
  impacted_factories: string[];
  total_impacted_nodes: number;
  bottlenecks: string[];
  weakest_links: Array<{
    supplier: string;
    part: string;
    stock: number;
    lead_time: number;
  }>;
}

export default function RiskSimulationPage() {
  const [suppliers, setSuppliers] = useState<string[]>([]);
  const [loadingSuppliers, setLoadingSuppliers] = useState(true);
  const [scenario, setScenario] = useState<RiskScenario>({
    supplier_name: '',
    duration_days: 30,
    severity: 'medium'
  });
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState<RiskResult | null>(null);

  useEffect(() => {
    const fetchSuppliers = async () => {
      try {
        const response = await api.get('/api/graph/nodes?label=Supplier');
        setSuppliers(response.data.map((s: any) => s.name));
      } catch (err) {
        console.error("Failed to fetch suppliers");
      } finally {
        setLoadingSuppliers(false);
      }
    };
    fetchSuppliers();
  }, []);

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scenario.supplier_name) return;

    setSimulating(true);
    try {
      const response = await api.post('/api/risk/simulate', scenario);
      setResult(response.data);
    } catch (err) {
      console.error("Simulation failed");
    } finally {
      setSimulating(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="xl:col-span-1">
          <h3 className="text-xl font-bold mb-6">Risk Scenario</h3>
          <form onSubmit={handleSimulate} className="glass p-6 rounded-3xl border border-[#1e293b] space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-400 mb-2">Target Supplier</label>
              {loadingSuppliers ? (
                <div className="h-12 bg-white/5 animate-pulse rounded-xl" />
              ) : (
                <select 
                  className="w-full h-12 bg-[#0d0d0f] border border-[#1e293b] rounded-xl px-4 text-sm focus:border-blue-500 outline-none transition-all"
                  value={scenario.supplier_name}
                  onChange={(e) => setScenario({ ...scenario, supplier_name: e.target.value })}
                >
                  <option value="">Select a supplier...</option>
                  {suppliers.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-slate-400 mb-2">Duration (Days)</label>
                <input 
                  type="number"
                  className="w-full h-12 bg-[#0d0d0f] border border-[#1e293b] rounded-xl px-4 text-sm focus:border-blue-500 outline-none transition-all"
                  value={scenario.duration_days}
                  onChange={(e) => setScenario({ ...scenario, duration_days: parseInt(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-400 mb-2">Severity</label>
                <select 
                  className="w-full h-12 bg-[#0d0d0f] border border-[#1e293b] rounded-xl px-4 text-sm focus:border-blue-500 outline-none transition-all"
                  value={scenario.severity}
                  onChange={(e) => setScenario({ ...scenario, severity: e.target.value as any })}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={simulating || !scenario.supplier_name}
              className="w-full py-4 bg-red-600 hover:bg-red-700 text-white rounded-2xl font-bold shadow-lg shadow-red-500/20 flex items-center justify-center space-x-2 disabled:opacity-50 transition-all transform active:scale-95"
            >
              {simulating ? <Loader2 className="animate-spin" size={20} /> : <Activity size={20} />}
              <span>{simulating ? 'Simulating...' : 'Run Propagation Analysis'}</span>
            </button>
          </form>
        </div>

        <div className="xl:col-span-2">
          <h3 className="text-xl font-bold mb-6">Impact Analysis</h3>
          {!result && !simulating ? (
            <div className="h-full flex flex-col items-center justify-center glass rounded-3xl p-12 text-center border-2 border-dashed border-[#1e293b]">
              <Database size={48} className="text-slate-700 mb-4" />
              <p className="text-slate-500">Select a supplier and start simulation to see cascading risk propagation.</p>
            </div>
          ) : simulating ? (
            <div className="h-full flex flex-col items-center justify-center glass rounded-3xl p-12 text-center">
              <Loader2 size={48} className="text-red-500 animate-spin mb-4" />
              <p className="text-slate-300 font-semibold animate-pulse">Analyzing N-Tier supply chain paths...</p>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="glass p-6 rounded-3xl border border-[#1e293b]">
                  <p className="text-xs font-bold text-slate-500 uppercase mb-1">Max Depth</p>
                  <p className="text-3xl font-bold text-red-500">{result?.cascading_impact_depth || 0} Tiers</p>
                </div>
                <div className="glass p-6 rounded-3xl border border-[#1e293b]">
                  <p className="text-xs font-bold text-slate-500 uppercase mb-1">Impacted Nodes</p>
                  <p className="text-3xl font-bold text-orange-500">{result?.total_impacted_nodes || 0}</p>
                </div>
                <div className="glass p-6 rounded-3xl border border-[#1e293b]">
                  <p className="text-xs font-bold text-slate-500 uppercase mb-1">Impacted Factories</p>
                  <p className="text-3xl font-bold text-blue-500">{result?.impacted_factories?.length || 0}</p>
                </div>
              </div>

              <div className="glass p-8 rounded-3xl border border-[#1e293b]">
                <h4 className="text-lg font-bold mb-6 flex items-center space-x-2">
                  <ShieldAlert className="text-red-500" size={20} />
                  <span>Weakest Links (Stock & Lead Time Exposure)</span>
                </h4>
                <div className="space-y-4">
                  {result?.weakest_links?.map((link, i) => (
                    <div key={i} className="flex items-center justify-between p-4 bg-white/[0.03] rounded-2xl border border-white/5">
                      <div>
                        <p className="font-bold">{link.supplier}</p>
                        <p className="text-xs text-slate-500">Supplying part: {link.part}</p>
                      </div>
                      <div className="text-right">
                        <div className="flex items-center space-x-4">
                          <div className="text-center">
                            <p className="text-[10px] font-bold text-slate-500 uppercase">Stock</p>
                            <p className={cn("font-mono font-bold", link.stock < 10 ? "text-red-500" : "text-emerald-500")}>
                                {link.stock} units
                            </p>
                          </div>
                          <div className="text-center">
                            <p className="text-[10px] font-bold text-slate-500 uppercase">Lead Time</p>
                            <p className="font-mono font-bold text-blue-500">{link.lead_time}d</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="glass p-8 rounded-3xl border border-[#1e293b]">
                <h4 className="text-lg font-bold mb-4">Propagation Chain Visualization</h4>
                <div className="flex flex-wrap items-center gap-4">
                  <div className="px-4 py-2 bg-red-600/10 border border-red-500/50 text-red-500 rounded-xl text-sm font-bold">
                    {scenario.supplier_name} (Origin)
                  </div>
                  <ArrowRight className="text-slate-700" size={16} />
                  <div className="px-4 py-2 bg-[#1e293b] rounded-xl text-sm font-bold">N-Tier Propagation</div>
                  <ArrowRight className="text-slate-700" size={16} />
                   <div className="px-4 py-2 bg-blue-600/10 border border-blue-500/50 text-blue-500 rounded-xl text-sm font-bold">
                    {result?.impacted_factories?.length || 0} Factories Affected
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
