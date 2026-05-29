import { useCallback, useEffect } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  MiniMap, 
  useNodesState, 
  useEdgesState, 
  MarkerType,
  type Connection,
  type Edge
} from 'reactflow';
import 'reactflow/dist/style.css';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Zap, Shield, Globe } from 'lucide-react';
import { motion } from 'framer-motion';

// --- Custom Node Components ---

const MasterNode = ({ data }: any) => (
  <div className="px-4 py-3 rounded-2xl bg-primary text-primary-foreground border-2 border-primary/50 shadow-[0_0_20px_rgba(255,255,255,0.1)] min-w-[180px]">
    <div className="flex items-center space-x-2 mb-2">
      <Zap className="h-5 w-5 fill-current" />
      <span className="font-bold text-lg">MASTER</span>
    </div>
    <div className="text-xs opacity-80 font-mono">{data.address}</div>
  </div>
);

const MeshNode = ({ data }: any) => {
  const isOnline = data.status === 'online';
  const roleIcon = data.role === 'exit' ? <Globe className="h-4 w-4" /> : <Shield className="h-4 w-4" />;
  
  return (
    <div className={`px-4 py-3 rounded-2xl bg-card border-2 ${isOnline ? 'border-green-500/50' : 'border-red-500/50'} shadow-xl min-w-[200px]`}>
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center space-x-2">
          {roleIcon}
          <span className="font-bold">{data.name}</span>
        </div>
        <div className={`h-2 w-2 rounded-full ${isOnline ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' : 'bg-red-500 animate-pulse'}`} />
      </div>
      
      <div className="grid grid-cols-2 gap-2 text-[10px] text-muted-foreground uppercase font-semibold">
        <div>CPU: <span className={data.metrics?.cpu_usage_percent > 80 ? 'text-red-400' : 'text-foreground'}>{data.metrics?.cpu_usage_percent || 0}%</span></div>
        <div>RAM: <span className="text-foreground">{data.metrics?.memory_usage_percent || 0}%</span></div>
        <div>DISK: <span className="text-foreground">{data.metrics?.disk_usage_percent || 0}%</span></div>
        <div>TEMP: <span className="text-foreground">{data.metrics?.temperature ? `${data.metrics.temperature}°C` : 'N/A'}</span></div>
      </div>
      
      <div className="mt-3 pt-2 border-t border-border flex justify-between items-center">
        <span className="text-[10px] font-mono opacity-50">{data.address}</span>
        <span className="text-[9px] bg-primary/10 text-primary px-2 py-0.5 rounded-full uppercase">{data.role}</span>
      </div>
    </div>
  );
};

const nodeTypes = {
  master: MasterNode,
  mesh: MeshNode,
};

// --- Main Component ---

export default function Dashboard() {
  const queryClient = useQueryClient();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const { data: meshData, isLoading } = useQuery({
    queryKey: ['mesh-nodes'],
    queryFn: async () => {
      const resp = await axios.get('/api/v1/nodes/');
      return resp.data;
    },
    refetchInterval: 10000,
  });

  const updateUpstream = useMutation({
    mutationFn: async ({ nodeId, upstreamIds }: { nodeId: number, upstreamIds: number[] }) => {
      await axios.put(`/api/v1/nodes/${nodeId}/upstreams`, upstreamIds);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mesh-nodes'] }),
  });

  useEffect(() => {
    if (!meshData) return;

    const newNodes = meshData.map((node: any, idx: number) => ({
      id: node.id.toString(),
      type: 'mesh',
      position: { x: 250 * (idx % 3), y: 150 * Math.floor(idx / 3) },
      data: { ...node },
    }));

    // Add static Master node
    newNodes.push({
      id: 'master',
      type: 'master',
      position: { x: -300, y: 150 },
      data: { address: window.location.origin },
    });

    const newEdges: Edge[] = [];
    meshData.forEach((node: any) => {
      const upstreams = node.metadata_json?.upstreams || [];
      if (node.upstream_id && !upstreams.includes(node.upstream_id)) {
        upstreams.push(node.upstream_id);
      }

      upstreams.forEach((uId: number) => {
        newEdges.push({
          id: `e${node.id}-${uId}`,
          source: node.id.toString(),
          target: uId.toString(),
          animated: true,
          style: { stroke: '#6366f1', strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' },
        });
      });
    });

    setNodes(newNodes);
    setEdges(newEdges);
  }, [meshData, setNodes, setEdges]);

  const onConnect = useCallback((params: Connection) => {
    if (!params.source || !params.target) return;
    
    const nodeId = parseInt(params.source);
    const upstreamId = parseInt(params.target);
    
    const node = meshData?.find((n: any) => n.id === nodeId);
    const currentUpstreams = node?.metadata_json?.upstreams || [];
    
    if (!currentUpstreams.includes(upstreamId)) {
      updateUpstream.mutate({ 
        nodeId, 
        upstreamIds: [...currentUpstreams, upstreamId] 
      });
    }
  }, [meshData, updateUpstream]);

  if (isLoading) return <div className="flex h-full items-center justify-center">Deploying sensors...</div>;

  return (
    <div className="h-[calc(100vh-10rem)] w-full relative">
      <div className="absolute top-0 left-0 z-10 space-y-1 lg:space-y-2 pointer-events-none">
        <h1 className="text-2xl lg:text-4xl font-bold tracking-tighter">NETWORK MAP</h1>
        <p className="text-[10px] lg:text-sm text-muted-foreground italic">Drag connections to route traffic dynamically</p>
      </div>

      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="h-full w-full bg-card/20 rounded-2xl lg:rounded-3xl border border-border overflow-hidden shadow-inner mt-12 lg:mt-0"
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
          <Background color="#333" gap={20} />
          <Controls className="bg-popover border-border fill-foreground scale-75 lg:scale-100 origin-bottom-left" />
          <MiniMap 
            style={{ height: 80, width: 100 }}
            nodeColor="#6366f1"
            maskColor="rgba(0,0,0,0.5)"
            className="bg-card border border-border rounded-xl hidden sm:block"
          />
        </ReactFlow>
      </motion.div>
    </div>
  );
}

