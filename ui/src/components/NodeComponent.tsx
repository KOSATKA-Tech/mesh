import { motion } from 'framer-motion';
import { Handle, Position } from 'reactflow';
import { clsx } from 'clsx';

// ROLE-SPECIFIC DISTRIBUTED GRAPH VISUALS
const MasterSVG = () => (
  <svg width="60" height="60" viewBox="0 0 100 100">
    <g className="filter drop-shadow-[0_0_10px_rgba(255,255,255,0.4)]">
      <motion.circle 
        animate={{ r: [2, 4, 2], opacity: [0.6, 1, 0.6] }}
        transition={{ duration: 2, repeat: Infinity }}
        cx="50" cy="50" r="3" fill="white" 
      />
      {[...Array(8)].map((_, i) => {
        const angle = (i * 45) * (Math.PI / 180);
        const x2 = 50 + 35 * Math.cos(angle);
        const y2 = 50 + 35 * Math.sin(angle);
        return (
          <g key={i}>
            <line x1="50" y1="50" x2={x2} y2={y2} stroke="white" strokeWidth="1" opacity="0.3" />
            <circle cx={x2} cy={y2} r="2" fill="white" opacity="0.6" />
          </g>
        );
      })}
    </g>
  </svg>
);

const RelaySVG = () => (
  <svg width="60" height="60" viewBox="0 0 100 100">
    <g className="opacity-70">
      <circle cx="50" cy="50" r="2" fill="white" />
      {/* Symmetrical horizontal branches */}
      <line x1="20" y1="50" x2="80" y2="50" stroke="white" strokeWidth="1.5" opacity="0.4" />
      <circle cx="20" cy="50" r="3" fill="white" opacity="0.6" />
      <circle cx="80" cy="50" r="3" fill="white" opacity="0.6" />
      {[30, 150, 210, 330].map((angleDeg, i) => {
        const angle = angleDeg * (Math.PI / 180);
        const x2 = 50 + 25 * Math.cos(angle);
        const y2 = 50 + 25 * Math.sin(angle);
        return (
          <g key={i}>
            <line x1="50" y1="50" x2={x2} y2={y2} stroke="white" strokeWidth="0.8" opacity="0.3" />
            <circle cx={x2} cy={y2} r="1.5" fill="white" opacity="0.4" />
          </g>
        );
      })}
    </g>
  </svg>
);

const ExitSVG = () => (
  <svg width="60" height="60" viewBox="0 0 100 100">
    <g className="filter drop-shadow-[0_0_8px_rgba(255,255,255,0.2)]">
      <circle cx="50" cy="70" r="2" fill="white" opacity="0.8" />
      {/* Blooming upwards */}
      {[210, 240, 270, 300, 330].map((angleDeg, i) => {
        const angle = angleDeg * (Math.PI / 180);
        const x2 = 50 + 40 * Math.cos(angle);
        const y2 = 70 + 40 * Math.sin(angle);
        return (
          <g key={i}>
            <motion.line 
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              x1="50" y1="70" x2={x2} y2={y2} stroke="white" strokeWidth="1" opacity="0.4" 
            />
            <motion.circle 
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 3, delay: i * 0.2, repeat: Infinity }}
              cx={x2} cy={y2} r="2.5" fill="white" 
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
      whileHover={{ scale: 1.05 }}
      className={clsx(
        "relative flex flex-col items-center group transition-all duration-700",
        !isOnline && "grayscale opacity-40"
      )}
    >
      <div className="relative mb-2">
        {getVisual()}
        {isOnline && (
           <div className="absolute inset-0 bg-white/5 blur-2xl rounded-full -z-10 animate-pulse scale-150" />
        )}
      </div>

      <div className="text-center space-y-1">
        <div className="text-[10px] font-black uppercase tracking-[0.2em] italic text-white/80 group-hover:text-white transition-colors">
          {data.label}
        </div>
        <div className="flex items-center justify-center space-x-2">
           <div className={clsx(
             "w-1 h-1 rounded-full",
             isOnline ? "bg-white shadow-[0_0_5px_#fff]" : "bg-white/10"
           )} />
           <span className="text-[7px] font-bold uppercase tracking-widest text-white/20 group-hover:text-white/40 transition-colors">
             {data.status}
           </span>
        </div>
      </div>

      <Handle type="target" position={Position.Top} className="!opacity-0" />
      <Handle type="source" position={Position.Bottom} className="!opacity-0" />
    </motion.div>
  );
};
