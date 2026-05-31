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
       <div className="text-[11px] font-black uppercase tracking-luxury animate-pulse opacity-10 italic">Scanning Perimeter...</div>
    </div>
  );

  return (
    <div className="space-y-8 pb-12">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="space-y-1">
          <h1 className="text-4xl lg:text-6xl font-black tracking-tighter uppercase italic opacity-95 text-foreground">Nodes</h1>
          <p className="text-[10px] lg:text-[11px] font-bold opacity-30 uppercase tracking-[0.3em]">Global Fleet Inventory & Telemetry</p>
        </div>
        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <button 
            onClick={() => refetch()}
            className="flex-1 sm:flex-none flex items-center justify-center space-x-2 px-6 py-3 rounded-xl bg-foreground/[0.03] border border-border hover:bg-foreground/[0.06] transition-all group"
          >
            <RefreshCw className="h-3.5 w-3.5 opacity-30 group-hover:rotate-180 transition-transform duration-700" />
            <span className="text-[10px] font-black uppercase tracking-widest opacity-50 text-foreground">Sync</span>
          </button>
          <button className="flex-1 sm:flex-none flex items-center justify-center space-x-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground hover:opacity-90 transition-all shadow-xl">
            <Plus className="h-3.5 w-3.5" />
            <span className="text-[10px] font-black uppercase tracking-widest">Deploy</span>
          </button>
        </div>
      </div>

      <div className="overflow-x-auto glass rounded-[32px] shadow-2xl border-border">
        <table className="w-full text-left border-collapse min-w-[700px]">
          <thead>
            <tr className="border-b border-border bg-foreground/[0.01]">
              <th className="px-6 py-5 text-[10px] font-black uppercase tracking-[0.2em] opacity-20 italic text-foreground">Status</th>
              <th className="px-6 py-5 text-[10px] font-black uppercase tracking-[0.2em] opacity-20 italic text-foreground">Identifier</th>
              <th className="px-6 py-5 text-[10px] font-black uppercase tracking-[0.2em] opacity-20 italic text-foreground">Architecture</th>
              <th className="px-6 py-5 text-[10px] font-black uppercase tracking-[0.2em] opacity-20 italic text-foreground">Address</th>
              <th className="px-6 py-5 text-[10px] font-black uppercase tracking-[0.2em] opacity-20 italic text-right text-foreground">Ops</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {nodes?.map((node: any, i: number) => (
              <motion.tr 
                key={node.id}
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
                className="hover:bg-foreground/[0.015] transition-colors group"
              >
                <td className="px-6 py-5">
                  <div className="flex items-center space-x-3">
                    <div className={`h-1.5 w-1.5 rounded-full ${node.status === 'online' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]' : 'bg-red-500/30'}`} />
                    <span className={`text-[9px] font-black uppercase tracking-widest ${node.status === 'online' ? 'opacity-80' : 'opacity-20'}`}>
                      {node.status}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-5 font-black text-[13px] tracking-tight opacity-90 italic text-foreground">{node.name}</td>
                <td className="px-6 py-5">
                  <span className="px-3 py-1 rounded-lg bg-foreground/[0.03] border border-border opacity-50 text-[9px] font-black uppercase tracking-widest text-foreground">
                    {node.provider_type}
                  </span>
                </td>
                <td className="px-6 py-5 font-mono text-[11px] opacity-30 truncate max-w-[200px] text-foreground">{node.address}</td>
                <td className="px-6 py-5 text-right">
                  <div className="flex items-center justify-end space-x-2">
                    <button className="p-2 rounded-lg bg-transparent hover:bg-foreground/[0.04] opacity-20 hover:opacity-100 transition-all text-foreground">
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </button>
                    <button className="p-2 rounded-lg bg-transparent hover:bg-red-500/5 opacity-10 hover:text-red-500 hover:opacity-100 transition-all">
                      <Trash2 className="h-3.5 w-3.5" />
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
