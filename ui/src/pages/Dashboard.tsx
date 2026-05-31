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
import { motion, AnimatePresence } from 'framer-motion';
import { Info } from 'lucide-react';
import { NodeComponent } from '../components/NodeComponent';

const Tooltip = ({ text }: { text: string }) => (
  <motion.div
    initial={{ opacity: 0, y: 5, scale: 0.98 }}
    animate={{ opacity: 1, y: 0, scale: 1 }}
    exit={{ opacity: 0, y: 3, scale: 0.98 }}
    className="absolute z-50 px-3 py-1.5 bg-primary text-primary-foreground text-[9px] font-black uppercase tracking-widest rounded-lg shadow-2xl pointer-events-none -top-10 left-0 whitespace-nowrap"
  >
    {text}
    <div className="absolute -bottom-1 left-4 w-2 h-2 bg-primary rotate-45" />
  </motion.div>
);

const nodeTypes = {
  agent: NodeComponent,
};

export default function Dashboard() {
  const queryClient = useQueryClient();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isInfoHovered, setIsInfoHovered] = useState(false);

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
    <div className="flex h-full items-center justify-center">
       <div className="text-[10px] font-black uppercase tracking-luxury animate-pulse opacity-10 italic">Synchronizing Fleet...</div>
    </div>
  );

  if (error) return (
    <div className="flex h-full items-center justify-center text-center">
       <div className="space-y-4">
          <p className="text-red-500 font-bold uppercase tracking-widest text-[10px]">Topology Link Failure</p>
          <p className="text-[8px] opacity-40 uppercase px-10">Check API authorization and connectivity.</p>
       </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full w-full relative space-y-4">
      <div className="flex-none space-y-1 group/title relative">
        <h1 className="text-3xl lg:text-5xl font-black tracking-tighter uppercase italic opacity-95 group-hover/title:opacity-100 transition-opacity duration-700">Network Map</h1>
        <div className="flex items-center space-x-3 relative">
          <p className="text-[9px] lg:text-[10px] font-bold opacity-30 uppercase tracking-[0.3em]">Orchestrating distributed nodes</p>
          <div 
            className="pointer-events-auto cursor-help relative flex items-center"
            onMouseEnter={() => setIsInfoHovered(true)}
            onMouseLeave={() => setIsInfoHovered(false)}
          >
            <Info className="w-3 h-3 opacity-10 group-hover/title:opacity-30 transition-opacity" />
            <AnimatePresence>
              {isInfoHovered && <Tooltip text="Visualizing active transmission paths." />}
            </AnimatePresence>
          </div>
        </div>
      </div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.998 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex-1 min-h-0 glass rounded-3xl overflow-hidden shadow-2xl relative border-border"
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
          minZoom={0.05}
          maxZoom={4}
        >
          <Background gap={30} size={1} color="var(--border)" />
          <Controls 
            showInteractive={false} 
            className="!m-4" 
          />
          <MiniMap 
            style={{ height: 80, width: 120 }}
            nodeColor="var(--primary)"
            maskColor="var(--background)"
            className="!bg-card/60 !border-border !rounded-2xl hidden lg:block !m-4 shadow-xl backdrop-blur-2xl"
          />
        </ReactFlow>
      </motion.div>
    </div>
  );
}
