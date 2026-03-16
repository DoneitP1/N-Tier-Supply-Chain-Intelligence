"use client";

import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node
} from 'reactflow';
import 'reactflow/dist/style.css';
import DashboardLayout from '@/components/layout/DashboardLayout';
import api from '@/lib/api';
import { cn } from '@/lib/utils';

const initialNodes: Node[] = [];
const initialEdges: Edge[] = [];

export default function GraphExplorer() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  const onConnect = useCallback(
    (params: Connection | Edge) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  const fetchGraphData = async () => {
    try {
      const response = await api.get('/api/graph/data?limit=50');
      const { nodes: backendNodes, edges: backendEdges } = response.data;

      const formattedNodes: Node[] = backendNodes.map((n: any, index: number) => ({
        id: n.id.toString(),
        data: { label: n.name },
        position: { x: Math.random() * 800, y: Math.random() * 500 },
        className: cn(
          "px-4 py-2 rounded-lg border-2 font-semibold shadow-xl",
          n.label === 'Supplier' ? "border-blue-500 bg-blue-500/10 text-blue-500" :
          n.label === 'Part' ? "border-purple-500 bg-purple-500/10 text-purple-500" :
          "border-slate-500 bg-slate-500/10 text-slate-500"
        ),
        type: 'default',
        // Attach full info for sidepanel
        info: n
      }));

      const formattedEdges: Edge[] = backendEdges.map((e: any) => ({
        id: `e${e.source}-${e.target}`,
        source: e.source.toString(),
        target: e.target.toString(),
        label: e.type,
        animated: e.type === 'SUPPLIES',
        style: { stroke: '#475569' },
        labelStyle: { fill: '#94a3b8', fontSize: 10, fontWeight: 700 }
      }));

      setNodes(formattedNodes);
      setEdges(formattedEdges);
    } catch (err) {
      console.error("Failed to fetch graph data", err);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, []);

  const onNodeClick = (_: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  };

  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-160px)] gap-6">
        <div className="flex-1 glass rounded-3xl overflow-hidden relative border border-[#1e293b]">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            fitView
            className="bg-[#0c0c0e]"
          >
            <Background color="#1e293b" gap={20} />
            <Controls className="bg-[#111113] border-[#1e293b] text-white fill-white" />
            <MiniMap className="bg-[#111113] border-[#1e293b]" nodeColor="#3b82f6" maskColor="rgba(0,0,0,0.5)" />
          </ReactFlow>
          
          <div className="absolute top-4 left-4 z-10">
            <button 
              onClick={fetchGraphData}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold shadow-lg shadow-blue-500/20 transition-all"
            >
              Refresh View
            </button>
          </div>
        </div>

        {/* Selected Node Details Panel */}
        <div className={cn(
          "w-80 glass rounded-3xl p-6 transition-all border border-[#1e293b]",
          selectedNode ? "opacity-100 translate-x-0" : "opacity-0 translate-x-10 pointer-events-none"
        )}>
          {selectedNode && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold">Node Details</h3>
                <button onClick={() => setSelectedNode(null)} className="text-slate-500 hover:text-white">✕</button>
              </div>
              
              <div className="space-y-6">
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-widest font-bold">Entity Name</p>
                  <p className="text-lg font-semibold mt-1">{(selectedNode.data as any).label}</p>
                </div>

                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-widest font-bold">Type</p>
                  <span className="inline-block mt-2 px-3 py-1 bg-blue-500/10 text-blue-500 border border-blue-500/20 rounded-full text-xs font-bold">
                    {(selectedNode as any).info?.label || 'Unknown'}
                  </span>
                </div>

                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-widest font-bold">System ID</p>
                  <p className="text-sm font-medium mt-1 text-slate-400">#{(selectedNode as any).id}</p>
                </div>

                <div className="pt-6 border-t border-[#1e293b]">
                  <button className="w-full py-3 bg-[#1e293b] hover:bg-[#2d3a4f] text-white rounded-xl text-sm font-semibold transition-all mb-3">
                    View In Inventory
                  </button>
                  <button className="w-full py-3 bg-red-500/5 hover:bg-red-500/10 text-red-500 border border-red-500/10 rounded-xl text-sm font-semibold transition-all">
                    Remove from Map
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}

