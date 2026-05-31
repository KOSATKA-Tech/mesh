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

  const { data: meshData, isLoading, error } = useQuery({
    queryKey: ['mesh-topology'],
    queryFn: async () => {
      const [nodesResp, policiesResp] = await Promise.all([
        axios.get('/api/v1/nodes/'),
        axios.get('/api/v1/policies/'),
      ]);
      return { nodes: nodesResp.data, policies: policiesResp.data };
    },
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (meshData) {
      const flowNodes = meshData.nodes.map((node: any, idx: number) => ({
        id: node.id.toString(),
        type: 'agent',
        position: node.position || { x: idx * 250, y: 150 },
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
            color: 'var(--foreground)',
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
    <div className="flex h-[60vh] items-center justify-center">
       <div className="text-[13px] font-black uppercase tracking-luxury animate-pulse opacity-20 italic">Synchronizing Fleet...</div>
    </div>
  );

  if (error) return (
    <div className="flex h-[60vh] items-center justify-center text-center">
       <div className="space-y-4">
          <p className="text-red-500 font-bold uppercase tracking-widest">Topology Link Failure</p>
          <p className="text-[10px] opacity-40 uppercase">Check API authorization and connectivity.</p>
       </div>
    </div>
  );

  return (
    <div className="flex flex-col h-[calc(100vh-14rem)] lg:h-[calc(100vh-16rem)] w-full relative space-y-12">
      <div className="flex-none space-y-2 lg:space-y-4 pointer-events-none group/title">
        <h1 className="text-5xl lg:text-8xl font-black tracking-tighter uppercase italic opacity-95 group-hover/title:opacity-100 transition-all duration-700">Network Map</h1>
        <div className="flex items-center space-x-4">
          <p className="text-[11px] lg:text-[14px] font-bold opacity-40 uppercase tracking-[0.4em]">Orchestrating autonomous distributed nodes</p>
          <Info className="w-5 h-5 opacity-10 group-hover/title:opacity-30 transition-opacity" />
        </div>
      </div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.998 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex-1 min-h-0 glass rounded-[60px] overflow-hidden shadow-[0_40px_100px_rgba(0,0,0,0.5)] relative border-border"
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.1}
          maxZoom={4}
        >
          <Background gap={40} size={1} color="var(--border)" />
          <Controls 
            showInteractive={false} 
            className="!m-12 scale-125" 
          />
          <MiniMap 
            style={{ height: 160, width: 240 }}
            nodeColor="var(--primary)"
            maskColor="var(--background)"
            className="!bg-card/80 !border-border !rounded-[45px] hidden lg:block !m-12 shadow-2xl backdrop-blur-3xl"
          />
        </ReactFlow>
      </motion.div>
    </div>
  );
}
