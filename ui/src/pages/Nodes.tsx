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
    <div className="flex h-[50vh] items-center justify-center">
       <div className="text-[10px] font-bold uppercase tracking-luxury animate-pulse text-white/20 italic">Scanning Perimeter...</div>
    </div>
  );

  return (
    <div className="space-y-12 pb-10">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl lg:text-4xl font-bold tracking-luxury uppercase italic">Nodes</h1>
          <p className="text-[10px] font-bold text-white/20 uppercase tracking-widest">Global Fleet Inventory & Real-time Telemetry</p>
        </div>
        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <button 
            onClick={() => refetch()}
            className="flex-1 sm:flex-none flex items-center justify-center space-x-2 px-6 py-3 rounded-2xl bg-white/[0.03] border border-white/10 hover:bg-white/5 transition-all group"
          >
            <RefreshCw className="h-3.5 w-3.5 text-white/40 group-hover:rotate-180 transition-transform duration-700" />
            <span className="text-[9px] font-bold uppercase tracking-widest text-white/60">Sync Fleet</span>
          </button>
          <button className="flex-1 sm:flex-none flex items-center justify-center space-x-2 px-6 py-3 rounded-2xl bg-white text-black hover:bg-white/90 transition-all shadow-[0_0_20px_rgba(255,255,255,0.1)]">
            <Plus className="h-3.5 w-3.5" />
            <span className="text-[9px] font-black uppercase tracking-widest">Deploy Node</span>
          </button>
        </div>
      </div>

      <div className="overflow-x-auto glass rounded-3xl">
        <table className="w-full text-left border-collapse min-w-[700px]">
          <thead>
            <tr className="border-b border-white/5 bg-white/[0.01]">
              <th className="px-8 py-5 text-[9px] font-bold uppercase tracking-[0.2em] text-white/20 italic">Status</th>
              <th className="px-8 py-5 text-[9px] font-bold uppercase tracking-[0.2em] text-white/20 italic">Identifier</th>
              <th className="px-8 py-5 text-[9px] font-bold uppercase tracking-[0.2em] text-white/20 italic">Architecture</th>
              <th className="px-8 py-5 text-[9px] font-bold uppercase tracking-[0.2em] text-white/20 italic">Network Address</th>
              <th className="px-8 py-5 text-[9px] font-bold uppercase tracking-[0.2em] text-white/20 italic text-right">Operations</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {nodes?.map((node: any, i: number) => (
              <motion.tr 
                key={node.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="hover:bg-white/[0.02] transition-colors group"
              >
                <td className="px-8 py-6">
                  <div className="flex items-center space-x-3">
                    <div className={`h-1.5 w-1.5 rounded-full ${node.status === 'online' ? 'bg-white shadow-[0_0_8px_#fff]' : 'bg-white/10'}`} />
                    <span className={`text-[9px] font-bold uppercase tracking-widest ${node.status === 'online' ? 'text-white/80' : 'text-white/20'}`}>
                      {node.status}
                    </span>
                  </div>
                </td>
                <td className="px-8 py-6 font-bold text-[11px] tracking-tight text-white/80 italic">{node.name}</td>
                <td className="px-8 py-6">
                  <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/40 text-[8px] font-black uppercase tracking-widest">
                    {node.provider_type}
                  </span>
                </td>
                <td className="px-8 py-6 font-mono text-[10px] text-white/30 truncate max-w-[200px]">{node.address}</td>
                <td className="px-8 py-6 text-right">
                  <div className="flex items-center justify-end space-x-2">
                    <button className="p-2.5 rounded-xl bg-white/0 hover:bg-white/5 text-white/20 hover:text-white transition-all">
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </button>
                    <button className="p-2.5 rounded-xl bg-white/0 hover:bg-destructive/10 text-white/20 hover:text-destructive transition-all">
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
