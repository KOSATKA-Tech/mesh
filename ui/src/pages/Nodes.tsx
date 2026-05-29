import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { RefreshCw, Trash2 } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Nodes() {
  const { data: nodes, isLoading, refetch } = useQuery({
    queryKey: ['nodes-list'],
    queryFn: async () => {
      const resp = await axios.get('/api/v1/nodes/');
      return resp.data;
    }
  });

  if (isLoading) return <div>Scanning perimeter...</div>;

  return (
    <div className="space-y-8 pb-10">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl lg:text-4xl font-bold tracking-tighter">NODES</h1>
          <p className="text-sm text-muted-foreground italic">Fleet Inventory & Host Statistics</p>
        </div>
        <button 
          onClick={() => refetch()}
          className="flex items-center space-x-2 bg-secondary text-secondary-foreground px-4 py-2 rounded-lg font-bold hover:bg-secondary/80 transition-all w-full sm:w-auto justify-center"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Refresh Fleet</span>
        </button>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-border bg-card/30 backdrop-blur-md">
        <table className="w-full text-left border-collapse min-w-[600px]">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-4 lg:px-6 py-4 text-[10px] lg:text-xs font-bold uppercase tracking-widest text-muted-foreground">Status</th>
              <th className="px-4 lg:px-6 py-4 text-[10px] lg:text-xs font-bold uppercase tracking-widest text-muted-foreground">Node Name</th>
              <th className="px-4 lg:px-6 py-4 text-[10px] lg:text-xs font-bold uppercase tracking-widest text-muted-foreground">Role</th>
              <th className="px-4 lg:px-6 py-4 text-[10px] lg:text-xs font-bold uppercase tracking-widest text-muted-foreground">Address</th>
              <th className="px-4 lg:px-6 py-4 text-[10px] lg:text-xs font-bold uppercase tracking-widest text-muted-foreground text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {nodes?.map((node: any) => (
              <motion.tr 
                key={node.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="hover:bg-muted/30 transition-colors group text-sm"
              >
                <td className="px-4 lg:px-6 py-4">
                  <div className="flex items-center space-x-2">
                    <div className={`h-2 w-2 rounded-full flex-shrink-0 ${node.status === 'online' ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' : 'bg-red-500'}`} />
                    <span className="text-[10px] lg:text-xs font-bold uppercase">{node.status}</span>
                  </div>
                </td>
                <td className="px-4 lg:px-6 py-4 font-bold truncate max-w-[120px] lg:max-w-none">{node.name}</td>
                <td className="px-4 lg:px-6 py-4">
                  <span className="px-2 py-1 rounded-full bg-primary/10 text-primary text-[9px] lg:text-[10px] font-bold uppercase tracking-tighter border border-primary/20">
                    {node.provider_type}
                  </span>
                </td>
                <td className="px-4 lg:px-6 py-4 font-mono text-[10px] lg:text-xs text-muted-foreground truncate max-w-[150px] lg:max-w-none">{node.address}</td>
                <td className="px-4 lg:px-6 py-4 text-right">
                  <button className="p-2 hover:text-destructive transition-colors opacity-100 lg:opacity-0 group-hover:opacity-100">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

