"use client";

import React, { useState, useCallback, useEffect, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import DashboardLayout from '@/components/layout/DashboardLayout';
import api from '@/lib/api';

const NODE_STYLES: Record<string, React.CSSProperties> = {
  Supplier: {
    background: 'rgba(59,130,246,0.12)',
    border: '2px solid #3b82f6',
    color: '#93c5fd',
    borderRadius: '12px',
    padding: '8px 16px',
    fontWeight: 600,
    fontSize: '12px',
    boxShadow: '0 0 12px rgba(59,130,246,0.2)',
  },
  Part: {
    background: 'rgba(168,85,247,0.12)',
    border: '2px solid #a855f7',
    color: '#d8b4fe',
    borderRadius: '12px',
    padding: '8px 16px',
    fontWeight: 600,
    fontSize: '12px',
    boxShadow: '0 0 12px rgba(168,85,247,0.2)',
  },
  Factory: {
    background: 'rgba(16,185,129,0.12)',
    border: '2px solid #10b981',
    color: '#6ee7b7',
    borderRadius: '12px',
    padding: '8px 16px',
    fontWeight: 600,
    fontSize: '12px',
    boxShadow: '0 0 12px rgba(16,185,129,0.2)',
  },
};

// Horizontal N-Tier layout: Suppliers (left) → Parts (centre) → Factories (right)
function computeLayout(backendNodes: any[]): Record<string, { x: number; y: number }> {
  const groups: Record<string, any[]> = { Supplier: [], Part: [], Factory: [] };
  for (const n of backendNodes) {
    (groups[n.label] ?? groups['Part']).push(n);
  }

  const positions: Record<string, { x: number; y: number }> = {};
  const yGap = 90;

  const placeGroup = (items: any[], x: number) => {
    const totalH = (items.length - 1) * yGap;
    items.forEach((n, i) => {
      positions[n.id] = { x, y: i * yGap - totalH / 2 };
    });
  };

  placeGroup(groups['Supplier'], 0);
  placeGroup(groups['Part'], 500);
  placeGroup(groups['Factory'], 1000);

  return positions;
}

function GraphCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [loading, setLoading] = useState(true);
  const { fitView } = useReactFlow();

  const fetchGraphData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/graph/data?limit=200');
      const { nodes: backendNodes, edges: backendEdges } = response.data;

      const positions = computeLayout(backendNodes);

      const formattedNodes: Node[] = backendNodes.map((n: any) => ({
        id: n.id.toString(),
        data: { label: n.name, nodeLabel: n.label },
        position: positions[n.id] ?? { x: Math.random() * 600, y: Math.random() * 400 },
        style: NODE_STYLES[n.label] ?? NODE_STYLES['Part'],
      }));

      const formattedEdges: Edge[] = backendEdges.map((e: any) => ({
        id: `e${e.source}-${e.target}`,
        source: e.source.toString(),
        target: e.target.toString(),
        label: e.type,
        animated: e.type === 'SUPPLIES',
        style: { stroke: e.type === 'CONSUMES' ? '#10b981' : '#475569', strokeWidth: 1.5 },
        labelStyle: { fill: '#64748b', fontSize: 9, fontWeight: 700 },
        labelBgStyle: { fill: '#0c0c0e', fillOpacity: 0.8 },
      }));

      setNodes(formattedNodes);
      setEdges(formattedEdges);
      setTimeout(() => fitView({ padding: 0.12, duration: 600 }), 100);
    } catch (err) {
      console.error('Failed to fetch graph data', err);
    } finally {
      setLoading(false);
    }
  }, [fitView, setNodes, setEdges]);

  useEffect(() => { fetchGraphData(); }, [fetchGraphData]);

  const onConnect = useCallback(
    (params: Connection | Edge) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-160px)] gap-6">
        {/* Graph Canvas */}
        <div className="flex-1 rounded-3xl overflow-hidden relative border border-[#1e293b]" style={{ background: '#0c0c0e' }}>
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center z-20 bg-[#0c0c0e]/80">
              <div className="text-slate-400 text-sm">Loading graph…</div>
            </div>
          )}

          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_: React.MouseEvent, node: Node) => setSelectedNode(node)}
            fitView
            style={{ background: '#0c0c0e' }}
          >
            <Background color="#1e293b" gap={24} />
            <Controls style={{ background: '#111113', border: '1px solid #1e293b', borderRadius: 12 }} />
            <MiniMap
              style={{ background: '#111113', border: '1px solid #1e293b', borderRadius: 12 }}
              nodeColor={(n) => {
                const label = (n.data as any)?.nodeLabel;
                return label === 'Supplier' ? '#3b82f6' : label === 'Factory' ? '#10b981' : '#a855f7';
              }}
              maskColor="rgba(0,0,0,0.6)"
            />
          </ReactFlow>

          {/* Legend */}
          <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
            <button
              onClick={fetchGraphData}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold shadow-lg transition-all"
            >
              Refresh View
            </button>
            <div className="flex flex-col gap-1 mt-2 bg-[#111113]/90 p-3 rounded-xl border border-[#1e293b] text-xs">
              <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-blue-500 inline-block"/> Supplier</span>
              <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-purple-500 inline-block"/> Part</span>
              <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-emerald-500 inline-block"/> Factory</span>
            </div>
          </div>
        </div>

        {/* Node Details Panel */}
        <div
          className="w-72 rounded-3xl p-6 border border-[#1e293b] transition-all duration-300"
          style={{
            background: '#111113',
            opacity: selectedNode ? 1 : 0,
            transform: selectedNode ? 'translateX(0)' : 'translateX(16px)',
            pointerEvents: selectedNode ? 'auto' : 'none',
          }}
        >
          {selectedNode && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-bold">Node Details</h3>
                <button onClick={() => setSelectedNode(null)} className="text-slate-500 hover:text-white text-lg">✕</button>
              </div>
              <div className="space-y-5">
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-1">Name</p>
                  <p className="font-semibold">{(selectedNode.data as any).label}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-1">Type</p>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                    (selectedNode.data as any).nodeLabel === 'Supplier' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                    (selectedNode.data as any).nodeLabel === 'Factory' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                  }`}>
                    {(selectedNode.data as any).nodeLabel}
                  </span>
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-1">System ID</p>
                  <p className="text-sm text-slate-400">#{selectedNode.id}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}

export default function GraphExplorer() {
  return (
    <ReactFlowProvider>
      <GraphCanvas />
    </ReactFlowProvider>
  );
}
