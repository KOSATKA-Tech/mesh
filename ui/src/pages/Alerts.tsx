import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Alerts() {
  const { data: alerts, isLoading } = useQuery({
    queryKey: ['system-alerts-ui'],
    queryFn: async () => {
      const resp = await axios.get('/api/v1/nodes/alerts'); // We need to add this endpoint or just use a generic one
      return resp.data;
    }
  });

  const getIcon = (level: string) => {
    switch (level.toLowerCase()) {
      case 'critical': return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'warning': return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      default: return <Info className="h-5 w-5 text-blue-500" />;
    }
  };

  if (isLoading) return <div>Interpreting distress signals...</div>;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold tracking-tighter">ALERTS</h1>
        <p className="text-muted-foreground italic">Central Intelligence & Node Notifications</p>
      </div>

      <div className="grid gap-4">
        {alerts?.length === 0 && (
          <div className="text-center py-20 bg-card/20 rounded-3xl border border-border italic text-muted-foreground">
            Clear skies. No system anomalies detected.
          </div>
        )}
        
        {alerts?.map((alert: any) => (
          <motion.div 
            key={alert.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-start space-x-4 bg-card/40 backdrop-blur-md border border-border p-5 rounded-2xl group hover:border-primary/30 transition-all"
          >
            <div className="mt-1">{getIcon(alert.level)}</div>
            <div className="flex-1 space-y-1">
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold uppercase tracking-widest text-primary/80">{alert.source}</span>
                <span className="text-[10px] text-muted-foreground">{new Date(alert.created_at).toLocaleString()}</span>
              </div>
              <p className="text-sm font-medium leading-relaxed group-hover:text-foreground transition-colors">
                {alert.message}
              </p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
