import { motion } from 'framer-motion';
import { Handle, Position } from 'reactflow';
import { Server, Activity, Shield } from 'lucide-react';
import { clsx } from 'clsx';

export const NodeComponent = ({ data }: any) => {
  const isOnline = data.status === 'online';
  
  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={clsx(
        "relative group p-4 rounded-2xl border transition-all duration-500 backdrop-blur-xl",
        isOnline 
          ? "bg-white/[0.03] border-white/10 shadow-[0_0_20px_rgba(255,255,255,0.02)]" 
          : "bg-white/[0.01] border-white/5 grayscale"
      )}
    >
      {/* Glow Effect for Online Nodes */}
      {isOnline && (
        <div className="absolute inset-0 bg-white/5 blur-xl rounded-full -z-10 animate-pulse" />
      )}

      <Handle type="target" position={Position.Top} className="!bg-white/20 !border-none !w-2 !h-2" />
      
      <div className="flex items-center space-x-4">
        <div className={clsx(
          "w-10 h-10 rounded-xl flex items-center justify-center transition-colors duration-500",
          isOnline ? "bg-white text-black glow-white" : "bg-white/10 text-white/20"
        )}>
          {data.role === 'exit' ? <Globe className="w-5 h-5" /> : <Server className="w-5 h-5" />}
        </div>
        
        <div className="space-y-0.5">
          <div className="text-[10px] font-bold uppercase tracking-luxury italic text-white/80">
            {data.label}
          </div>
          <div className="flex items-center space-x-2">
             <div className={clsx(
               "w-1.5 h-1.5 rounded-full",
               isOnline ? "bg-white shadow-[0_0_8px_#fff]" : "bg-white/10"
             )} />
             <span className="text-[8px] font-bold uppercase tracking-widest text-white/30">{data.status}</span>
          </div>
        </div>
      </div>

      {/* Hover Info */}
      <div className="mt-3 overflow-hidden h-0 group-hover:h-8 transition-all duration-500 flex items-center space-x-4 opacity-0 group-hover:opacity-100">
        <div className="flex items-center space-x-1">
          <Activity className="w-3 h-3 text-white/20" />
          <span className="text-[9px] font-bold text-white/40">{data.stats?.cpu || 0}%</span>
        </div>
        <div className="flex items-center space-x-1">
          <Shield className="w-3 h-3 text-white/20" />
          <span className="text-[9px] font-bold text-white/40">{data.provider_type}</span>
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-white/20 !border-none !w-2 !h-2" />
    </motion.div>
  );
};

// Helper components for the icons used in NodeComponent
const Globe = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
  </svg>
);
