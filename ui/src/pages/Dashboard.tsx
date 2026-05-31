import { useState, useCallback, useEffect } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  MiniMap, 
  applyNodeChanges, 
  applyEdgeChanges, 
  addEdge,
  type Connection,
  type Edge,
  type Node,
  type NodeChange,
  type EdgeChange,
  MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Info } from 'lucide-react';
import { NodeComponent } from '../components/NodeComponent';

const nodeTypes = {
  agent: NodeComponent,
};

export default function Dashboard() {
  const queryClient = useQueryClient();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  const { data: meshData, isLoading } = useQuery({
    queryKey: ['mesh-topology'],
    queryFn: async () => {
      const [nodesResp, linksResp] = await Promise.all([
        axios.get('/api/v1/nodes/'),
        axios.get('/api/v1/policies/'), // Corrected endpoint
      ]);
      return { nodes: nodesResp.data, policies: linksResp.data };
    },
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (meshData) {
      const flowNodes = meshData.nodes.map((node: any, idx: number) => ({
        id: node.id.toString(),
        type: 'agent',
        position: node.position || { x: idx * 250, y: 100 },
        data: { 
          label: node.name, 
          status: node.status, 
          provider_type: node.provider_type,
          role: node.role,
          stats: node.last_stats 
        },
      }));

      const flowEdges = meshData.nodes
        .filter((n: any) => n.upstream_id)
        .map((n: any) => ({
          id: `e-${n.upstream_id}-${n.id}`,
          source: n.upstream_id.toString(),
          target: n.id.toString(),
          className: 'edge-animated',
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: 'rgba(255,255,255,0.2)',
          },
        }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    }
  }, [meshData]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const updateUpstream = useMutation({
    mutationFn: async ({ nodeId, upstreamId }: { nodeId: string, upstreamId: string }) => {
      await axios.put(`/api/v1/nodes/${nodeId}/upstreams`, [parseInt(upstreamId)]);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mesh-topology'] }),
  });

  const onConnect = useCallback(
    (params: Connection) => {
      if (params.source && params.target) {
        updateUpstream.mutate({ nodeId: params.target, upstreamId: params.source });
        setEdges((eds) => addEdge({ ...params, className: 'edge-animated' }, eds));
      }
    },
    [updateUpstream]
  );

  if (isLoading) return (
    <div className="flex h-[70vh] items-center justify-center">
       <div className="text-[10px] font-bold uppercase tracking-luxury animate-pulse text-white/20 italic">Synchronizing Fleet...</div>
    </div>
  );

  return (
    <div className="flex flex-col h-[calc(100vh-10rem)] w-full relative space-y-6">
      <div className="flex-none space-y-2 lg:space-y-3 pointer-events-none group/title">
        <h1 className="text-4xl lg:text-6xl font-black tracking-luxury uppercase italic text-white/95 group-hover/title:text-white transition-colors duration-700">Network Map</h1>
        <div className="flex items-center space-x-3">
          <p className="text-[12px] lg:text-[14px] font-bold text-white/50 uppercase tracking-[0.3em]">Orchestrating autonomous distributed nodes</p>
          <Info className="w-4 h-4 text-white/20 group-hover/title:text-white/50 transition-colors" />
        </div>
      </div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex-1 min-h-0 glass rounded-[40px] overflow-hidden border border-white/10 shadow-2xl relative"
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
        >
          <Background color="rgba(255,255,255,0.05)" gap={40} size={1} />
          <Controls className="!bg-black/80 !border-white/10 !rounded-2xl !p-1" />
          <MiniMap 
            style={{ height: 100, width: 140 }}
            nodeColor="#555"
            maskColor="rgba(0,0,0,0.7)"
            className="!bg-black/90 !border-white/10 !rounded-3xl hidden sm:block !m-4"
          />
        </ReactFlow>
      </motion.div>
    </div>
  );
}
