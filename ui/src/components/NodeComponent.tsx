import { motion } from 'framer-motion';
import { Handle, Position } from 'reactflow';
import { clsx } from 'clsx';

// ROLE-SPECIFIC DISTRIBUTED GRAPH VISUALS
const MasterSVG = () => (
  <svg width="60" height="60" viewBox="0 0 100 100">
    <g className="filter drop-shadow-[0_0_15px_rgba(255,255,255,0.5)]">
      <motion.circle 
        animate={{ r: [2, 5, 2], opacity: [0.6, 1, 0.6] }}
        transition={{ duration: 2, repeat: Infinity }}
        cx="50" cy="50" r="4" fill="currentColor" 
      />
      {[...Array(8)].map((_, i) => {
        const angle = (i * 45) * (Math.PI / 180);
        const x2 = 50 + 35 * Math.cos(angle);
        const y2 = 50 + 35 * Math.sin(angle);
        return (
          <g key={i}>
            <line x1="50" y1="50" x2={x2} y2={y2} stroke="currentColor" strokeWidth="1.5" opacity="0.3" />
            <circle cx={x2} cy={y2} r="3" fill="currentColor" opacity="0.6" />
          </g>
        );
      })}
    </g>
  </svg>
);

const RelaySVG = () => (
  <svg width="60" height="60" viewBox="0 0 100 100">
    <g className="opacity-70">
      <circle cx="50" cy="50" r="3" fill="currentColor" />
      <line x1="15" y1="50" x2="85" y2="50" stroke="currentColor" strokeWidth="2" opacity="0.4" />
      <circle cx="15" cy="50" r="4" fill="currentColor" opacity="0.6" />
      <circle cx="85" cy="50" r="4" fill="currentColor" opacity="0.6" />
      {[45, 135, 225, 315].map((angleDeg, i) => {
        const angle = angleDeg * (Math.PI / 180);
        const x2 = 50 + 30 * Math.cos(angle);
        const y2 = 50 + 30 * Math.sin(angle);
        return (
          <g key={i}>
            <line x1="50" y1="50" x2={x2} y2={y2} stroke="currentColor" strokeWidth="1" opacity="0.3" />
            <circle cx={x2} cy={y2} r="2" fill="currentColor" opacity="0.4" />
          </g>
        );
      })}
    </g>
  </svg>
);

const ExitSVG = () => (
  <svg width="60" height="60" viewBox="0 0 100 100">
    <g>
      <circle cx="50" cy="75" r="3" fill="currentColor" opacity="0.8" />
      {[210, 240, 270, 300, 330].map((angleDeg, i) => {
        const angle = angleDeg * (Math.PI / 180);
        const x2 = 50 + 45 * Math.cos(angle);
        const y2 = 75 + 45 * Math.sin(angle);
        return (
          <g key={i}>
            <motion.line 
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              x1="50" y1="75" x2={x2} y2={y2} stroke="currentColor" strokeWidth="1.5" opacity="0.4" 
            />
            <motion.circle 
              animate={{ opacity: [0.3, 1, 0.3], r: [2, 4, 2] }}
              transition={{ duration: 3, delay: i * 0.2, repeat: Infinity }}
              cx={x2} cy={y2} r="3" fill="currentColor" 
            />
          </g>
        );
      })}
    </g>
  </svg>
);

export const NodeComponent = ({ data }: any) => {
  const isOnline = data.status === 'online';
  
  const getVisual = () => {
    if (data.role === 'master' || data.name.toLowerCase().includes('master')) return <MasterSVG />;
    if (data.role === 'proxy' || data.role === 'relay') return <RelaySVG />;
    return <ExitSVG />;
  };

  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      whileHover={{ scale: 1.1 }}
      className={clsx(
        "relative flex flex-col items-center group transition-all duration-500",
        !isOnline && "grayscale opacity-40"
      )}
    >
      <div className={clsx(
        "relative mb-4 text-foreground transition-colors duration-500",
        isOnline ? "text-primary drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]" : "text-muted-foreground"
      )}>
        {getVisual()}
        {isOnline && (
           <div className="absolute inset-0 bg-primary/5 blur-3xl rounded-full -z-10 animate-pulse scale-[2]" />
        )}
      </div>

      <div className="text-center space-y-1.5">
        <div className="text-[12px] font-black uppercase tracking-[0.2em] italic opacity-80 group-hover:opacity-100 transition-opacity">
          {data.label}
        </div>
        <div className="flex items-center justify-center space-x-2">
           <div className={clsx(
             "w-1.5 h-1.5 rounded-full",
             isOnline ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" : "bg-red-500/30"
           )} />
           <span className="text-[9px] font-black uppercase tracking-widest opacity-40 group-hover:opacity-60 transition-opacity">
             {data.status}
           </span>
        </div>
      </div>

      <Handle type="target" position={Position.Top} className="!opacity-0" />
      <Handle type="source" position={Position.Bottom} className="!opacity-0" />
    </motion.div>
  );
};
