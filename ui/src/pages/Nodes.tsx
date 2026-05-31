import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Trash2, RefreshCw, Plus, ArrowUpRight } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Nodes() {
  const { data: nodes, isLoading, refetch } = useQuery({
    queryKey: ['nodes'],
    queryFn: async () => {
      const resp = await axios.get('/api/v1/nodes/');
      return resp.data;
    }
  });

  if (isLoading) return (
    <div className="flex h-[60vh] items-center justify-center">
       <div className="text-[12px] font-black uppercase tracking-luxury animate-pulse opacity-20 italic">Scanning Perimeter...</div>
    </div>
  );

  return (
    <div className="space-y-12 pb-16">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
        <div className="space-y-2">
          <h1 className="text-5xl lg:text-7xl font-black tracking-tighter uppercase italic opacity-95">Nodes</h1>
          <p className="text-[12px] lg:text-[14px] font-bold opacity-40 uppercase tracking-[0.4em]">Global Fleet Inventory & Real-time Telemetry</p>
        </div>
        <div className="flex items-center space-x-4 w-full sm:w-auto">
          <button 
            onClick={() => refetch()}
            className="flex-1 sm:flex-none flex items-center justify-center space-x-3 px-8 py-4 rounded-2xl bg-foreground/[0.03] border border-border hover:bg-foreground/[0.06] transition-all group"
          >
            <RefreshCw className="h-4 w-4 opacity-40 group-hover:rotate-180 transition-transform duration-700" />
            <span className="text-[11px] font-black uppercase tracking-widest opacity-60">Sync Fleet</span>
          </button>
          <button className="flex-1 sm:flex-none flex items-center justify-center space-x-3 px-8 py-4 rounded-2xl bg-primary text-primary-foreground hover:opacity-90 transition-all shadow-2xl">
            <Plus className="h-4 w-4" />
            <span className="text-[11px] font-black uppercase tracking-widest">Deploy Node</span>
          </button>
        </div>
      </div>

      <div className="overflow-x-auto glass rounded-[40px] shadow-2xl border-border">
        <table className="w-full text-left border-collapse min-w-[800px]">
          <thead>
            <tr className="border-b border-border bg-foreground/[0.02]">
              <th className="px-8 py-7 text-[11px] font-black uppercase tracking-[0.3em] opacity-30 italic">Status</th>
              <th className="px-8 py-7 text-[11px] font-black uppercase tracking-[0.3em] opacity-30 italic">Identifier</th>
              <th className="px-8 py-7 text-[11px] font-black uppercase tracking-[0.3em] opacity-30 italic">Architecture</th>
              <th className="px-8 py-7 text-[11px] font-black uppercase tracking-[0.3em] opacity-30 italic">Network Address</th>
              <th className="px-8 py-7 text-[11px] font-black uppercase tracking-[0.3em] opacity-30 italic text-right">Operations</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {nodes?.map((node: any, i: number) => (
              <motion.tr 
                key={node.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="hover:bg-foreground/[0.02] transition-colors group"
              >
                <td className="px-8 py-8">
                  <div className="flex items-center space-x-3">
                    <div className={`h-2 w-2 rounded-full ${node.status === 'online' ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]' : 'bg-red-500/40'}`} />
                    <span className={`text-[10px] font-black uppercase tracking-widest ${node.status === 'online' ? 'opacity-90' : 'opacity-30'}`}>
                      {node.status}
                    </span>
                  </div>
                </td>
                <td className="px-8 py-8 font-black text-[16px] tracking-tight opacity-90 italic">{node.name}</td>
                <td className="px-8 py-8">
                  <span className="px-5 py-2 rounded-full bg-foreground/[0.05] border border-border opacity-60 text-[10px] font-black uppercase tracking-widest">
                    {node.provider_type}
                  </span>
                </td>
                <td className="px-8 py-8 font-mono text-[14px] opacity-40 truncate max-w-[250px]">{node.address}</td>
                <td className="px-8 py-8 text-right">
                  <div className="flex items-center justify-end space-x-3">
                    <button className="p-3 rounded-2xl bg-transparent hover:bg-foreground/[0.05] opacity-20 hover:opacity-100 transition-all">
                      <ArrowUpRight className="h-4 w-4" />
                    </button>
                    <button className="p-3 rounded-2xl bg-transparent hover:bg-red-500/10 opacity-20 hover:text-red-500 hover:opacity-100 transition-all">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
