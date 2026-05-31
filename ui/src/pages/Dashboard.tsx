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
    <div className="h-[calc(100vh-12rem)] w-full relative">
      <div className="absolute top-0 left-0 z-10 space-y-2 lg:space-y-3 pointer-events-none group/title">
        <h1 className="text-3xl lg:text-5xl font-black tracking-luxury uppercase italic text-white/90 group-hover/title:text-white transition-colors duration-700">Network Map</h1>
        <div className="flex items-center space-x-2">
          <p className="text-[10px] lg:text-[12px] font-bold text-white/40 uppercase tracking-[0.3em]">Orchestrating autonomous distributed nodes</p>
          <Info className="w-3 h-3 text-white/10 group-hover/title:text-white/30 transition-colors" />
        </div>
      </div>

      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="h-full w-full glass rounded-3xl overflow-hidden mt-16 lg:mt-0"
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
          <Background color="rgba(255,255,255,0.03)" gap={30} size={1} />
          <Controls className="scale-75 lg:scale-100 origin-bottom-left" />
          <MiniMap 
            style={{ height: 80, width: 100 }}
            nodeColor="#333"
            maskColor="rgba(0,0,0,0.8)"
            className="!bg-black/80 !border-white/10 !rounded-2xl hidden sm:block"
          />
        </ReactFlow>
      </motion.div>
    </div>
  );
}
